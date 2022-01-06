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
https://console.cloud.google.com/apis/credentials/oauthclient/299107039403-jm7n7m3s9u771dnec1kncsllgoiv8p5a.apps.googleusercontent.com?project=ohbehave

# Data sources
Sheet of interest:
- XLSX version: https://docs.google.com/spreadsheets/d/17hHiqc6GKWv9trcW-lRnv-MhZL8Swrx2/edit#gid=1335629675
- https://docs.google.com/spreadsheets/d/1jzGrVELQz5L4B_-DqPflPIcpBaTfJOUTrVJT5nS_j18/edit#gid=405597125
"""
import json
import os
from typing import List, Dict
from datetime import datetime, timedelta
from dateutil.parser import parse as parse_datetime_str

from google.auth.exceptions import RefreshError
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
import pandas as pd
from pandas import DataFrame

from value_set_vsac_json_to_n3c_json.config import ENV_DIR, CACHE_DIR

# If modifying these scopes, delete the file token.json.
SCOPES = ['https://www.googleapis.com/auth/spreadsheets.readonly']

# The ID and range of a sample spreadsheet.
SAMPLE_SPREADSHEET_ID = '1jzGrVELQz5L4B_-DqPflPIcpBaTfJOUTrVJT5nS_j18'
SAMPLE_RANGE_NAME = 'CDC reference table list!A1:AC'
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


def _get_sheets_live() -> Dict:
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
        range=SAMPLE_RANGE_NAME).execute()

    return result


def _get_sheets_cache(path=cache_file_path) -> Dict:
    """Get sheets from local cache"""
    try:
        with open(path) as f:
            result: Dict = json.load(f)
        return result
    except FileNotFoundError:
        return {}


# TODO: get oids from this
# https://docs.google.com/spreadsheets/d/17hHiqc6GKWv9trcW-lRnv-MhZL8Swrx2/edit#gid=1335629675
def get_sheets_data(
    cache_threshold_datetime: datetime = datetime.now() - timedelta(days=7)
) -> pd.DataFrame:
    """Shows basic usage of the Sheets API.
    Prints values from a sample spreadsheet.
    The default cache date is a week ago. So if the last reported data in the
    cached file is les than 7 days ago, cache is used. Else, it loads live data
    and overwrites cache.
    """
    result: Dict = {}
    if cache_threshold_datetime:
        cached: Dict = _get_sheets_cache()
        last_timestamp = parse_datetime_str(
            cached['values'][-1][0]) if cached else None
        if last_timestamp and last_timestamp > cache_threshold_datetime:
            result = cached
    if not result:
        result = _get_sheets_live()
        with open(cache_file_path, 'w') as fp:
            json.dump(result, fp)

    values: List[List[str]] = result.get('values', [])
    header = values[0]
    values = values[1:]

    df: DataFrame = pd.DataFrame(values, columns=header).fillna('')

    return df


if __name__ == '__main__':
    get_sheets_data()
