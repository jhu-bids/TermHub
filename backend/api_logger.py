import datetime
import os
import re
import httpx
import time
from _socket import gethostname
from typing import Dict, List, Optional

import pytz
from starlette.requests import Request

from backend.config import get_schema_name
from backend.db.utils import get_db_connection, insert_from_dict, run_sql, sql_query
from backend.utils import dump


class Api_logger:
    def __init__(self):
        pass

    async def start_rpt(self, request: Request, params: Dict):
        self.start_time = time.time()
        rpt = {}
        url = request.url
        api_call = url.components[2][1:] # string leading /
        rpt['api_call'] = api_call

        eastern = pytz.timezone('US/Eastern')
        rpt['timestamp'] = datetime.datetime.now(eastern).isoformat()

        rpt['host'] = os.getenv('HOSTENV', gethostname())

        rpt['client'] = await client_location(request)

        rpt['schema'] = get_schema_name()

        rpt['api_call_group_id'] = int(request.query_params.get('api_call_group_id', -1))

        rpt_params = {}
        for k,v in params.items():
            if type(v) == list:
                if len(v) > 20:
                    # change any params with len > 20 to just log the len
                    rpt_params[k + '_len'] = len(v)
                elif k in ['codeset_ids', 'id', ]:
                    # put codeset_ids in a separate column (is this going to be helpful?)
                    codeset_ids = v

                    if len(v) == 1 and type(codeset_ids[0]) == str:
                        codeset_ids = codeset_ids[0].split('|')

                    codeset_ids = [int(x) for x in codeset_ids]
                    rpt['codeset_ids'] = codeset_ids
                else:
                    rpt_params[k] = v
            else:
                raise(Exception(f"don't know how to log {k}: {dump(v)}"))

        # everything but codeset_ids just gets dumped into the rpt
        params_list = []
        for k,v in rpt_params.items():
            params_list.append(f'{k}: {v}')

        rpt['params'] = '; '.join(params_list)
        self.rpt = rpt
        with get_db_connection() as con:
            insert_from_dict(con, 'public.api_runs', rpt, skip_if_already_exists=False)


    async def finish(self, rows: List = []):
        if rows:
            self.rpt['result'] = f'{rows} rows'
        else:
            self.rpt['result'] = 'Success'

        await self.complete_log_record()


    async def complete_log_record(self):
        end_time = time.time()
        process_seconds = end_time - self.start_time
        self.rpt['process_seconds'] = process_seconds

        with get_db_connection() as con:
            run_sql(con, """
                        UPDATE public.api_runs
                        SET process_seconds = :process_seconds, result = :result
                        WHERE timestamp = :timestamp""", self.rpt)
            # using timestamp as a primary key. not the best practice, I know, but with microsecond granularity
            #   (e.g., 2023-10-31T13:32:23.934211), it seems like it should be safe


    async def log_error(self, e):
        self.rpt['result'] = f'Error: {e}'
        await self.complete_log_record()

async def client_location(request: Request) -> str:
    # rpt['client'] = request.client.host -- this gives a local (169.154) IP on azure
    #   chatgpt recommends:
    forwarded_for: Optional[str] = request.headers.get('X-Forwarded-For')
    if forwarded_for:
        # The header can contain multiple IP addresses, so take the first one
        ip = forwarded_for.split(',')[0]
    else:
        ip = request.client.host

    ip = re.sub(':.*', '', ip)

    with get_db_connection() as con:
        ip_info = sql_query(con, 'SELECT * FROM public.ip_info WHERE ip = :ip', {'ip': ip})
        if ip_info:
            city = ip_info.get('city', 'no city')
            region = ip_info.get('region', 'no region')
            location = f"{ip}: {city}, {region}"
            return location

    # for now we're going to just return the ip, free subscription ran out and need to update key
    # return ip

    ipstack_key = os.getenv('API_STACK_KEY', None)

    if ip != '127.0.0.1' and ipstack_key:
        """
        http://api.ipstack.com/134.201.250.155?access_key=<key>&format=1
        {
            "ip": "134.201.250.155",
            "type": "ipv4",
            "continent_code": "NA",
            "continent_name": "North America",
            "country_code": "US",
            "country_name": "United States",
            "region_code": "CA",
            "region_name": "California",
            "city": "San Fernando",
            "zip": "91344",
            "latitude": 34.293949127197266,
            "longitude": -118.50763702392578,
            "location": {
                "geoname_id": 5391945,
                "capital": "Washington D.C.",
                "languages": [
                    {
                        "code": "en",
                        "name": "English",
                        "native": "English"
                    }
                ],
                "country_flag": "https://assets.ipstack.com/flags/us.svg",
                "country_flag_emoji": "🇺🇸",
                "country_flag_emoji_unicode": "U+1F1FA U+1F1F8",
                "calling_code": "1",
                "is_eu": false
            }
        }
        """

        loc_url = f"http://api.ipstack.com/{ip}?access_key={ipstack_key}"

        async with httpx.AsyncClient() as client:
            response = await client.get(loc_url)
            if response and response.json:
                loc = response.json()
                if 'error' in loc:
                    return f'{ip} (no loc, err {loc.get("error", {}).get("code", "")})'
                city = loc.get('city', 'no city')
                region = loc.get('region', 'no region')
                location = f"{ip}: {city}, {region}"

                with get_db_connection() as con:
                    insert_from_dict(con, 'public.ip_info', loc)

                return location

    return ip