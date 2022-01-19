"""Get data from google sheets

# Docs
Quickstart:
https://developers.google.com/sheets/api/quickstart/python
Project creation and mgmt:
https://developers.google.com/workspace/guides/create-project
Create creds:
https://developers.google.com/workspace/guides/create-credentials

# Setup
Google cloud project console:
# TODO: When changing project from 'ohbehave' to a new one, update this URL:
https://console.cloud.google.com/apis/credentials/oauthclient/299107039403-jm7n7m3s9u771dnec1kncsllgoiv8p5a.apps.googleusercontent.com?project=ohbehave

# Data sources
- Refer to config.py
"""
import json
import os
from typing import List, Dict
from datetime import datetime, timedelta

from google.auth.exceptions import RefreshError
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
import pandas as pd
from pandas import DataFrame

from vsac_wrangler.config import ENV_DIR, CACHE_DIR, SAMPLE_RANGE_NAME, SAMPLE_SPREADSHEET_ID

# If modifying these scopes, delete the file token.json.
SCOPES = ['https://www.googleapis.com/auth/spreadsheets.readonly']

# The ID and range of a sample spreadsheet.
TOKEN_PATH = os.path.join(ENV_DIR, 'token.json')
CREDS_PATH = os.path.join(ENV_DIR, 'credentials.json')
cache_file_path = os.path.join(CACHE_DIR, 'data.json')


def _get_and_use_new_token():
    """Get new api token"""
    flow = InstalledAppFlow.from_client_secrets_file(
        CREDS_PATH, SCOPES)
    # creds = flow.run_local_server(port=0)
    creds = flow.run_local_server(port=54553)
    # Save the credentials for the next run
    with open(TOKEN_PATH, 'w') as token:
        token.write(creds.to_json())


def _get_sheets_live(google_sheet_name) -> Dict:
    """Get sheets from online source"""
    creds = None
    # The file token.json stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    if os.path.exists(TOKEN_PATH):
        creds = Credentials.from_authorized_user_file(TOKEN_PATH, SCOPES)
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        try:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                _get_and_use_new_token()
        except RefreshError:
            _get_and_use_new_token()

    service = build('sheets', 'v4', credentials=creds)

    # Call the Sheets API
    sheet = service.spreadsheets()
    result: Dict = sheet.values().get(
        spreadsheetId=SAMPLE_SPREADSHEET_ID,
        range=SAMPLE_RANGE_NAME.format(google_sheet_name)).execute()

    return result


def _get_sheets_cache(path=cache_file_path) -> Dict:
    """Get sheets from local cache"""
    try:
        with open(path) as f:
            result: Dict = json.load(f)
        return result
    except FileNotFoundError:
        return {}


# TODO: Utilize these params?
def get_sheets_data(
    google_sheet_name
    # cache_threshold_datetime: datetime = datetime.now() - timedelta(days=7)
) -> pd.DataFrame:
    """Shows basic usage of the Sheets API.
    Prints values from a sample spreadsheet.
    The default cache date is a week ago. So if the last reported data in the
    cached file is les than 7 days ago, cache is used. Else, it loads live data
    and overwrites cache.
    """
    result: Dict = {}
    # TODO: caching broken because need to figure out how to tell when sheet last updated
    # https://stackoverflow.com/questions/43411138/get-google-sheets-last-edit-date-using-sheets-api-v4-java
    # ...apparently this is not available in google sheets api, only google drive file api
    # if cache_threshold_datetime:
    #     cached: Dict = _get_sheets_cache()
    # #... this is how it was done in other project:
    #     last_timestamp = parse_datetime_str(
    #         cached['values'][-1][0]) if cached else None
    #     if last_timestamp and last_timestamp > cache_threshold_datetime:
    #         result = cached
    if not result:
        result = _get_sheets_live(google_sheet_name)
        with open(cache_file_path, 'w') as fp:
            json.dump(result, fp)

    values: List[List[str]] = result.get('values', [])
    header = values[0]
    # values = values[1:]

    # df: DataFrame = pd.DataFrame(values, columns=header).fillna('')
    df: DataFrame = pd.DataFrame(values).fillna('')
    df.columns = header
    df = df.drop([0])

    return df


if __name__ == '__main__':
    get_sheets_data('CDC reference table list')
