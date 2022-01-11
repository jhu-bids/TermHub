# -*- coding: utf-8 -*-
"""
Created on Tue Jan 11 05:43:26 2022

@author: sgold15
"""

import requests as req

headers = {
    'Host': 'atlas.pm.jh.edu:8443',
    'Connection': 'keep-alive',
    'sec-ch-ua': '" Not A;Brand";v="99", "Chromium";v="96", "Google Chrome";v="96"',
    'Accept': 'application/json',
    'Authorization': '''
            NOT INCLUDING AUTH STRING, GET IT FROM
              https://atlas.pm.jh.edu/#/search/diabetes
            right click on results page --> inspect --> Network tab --> select fetch/XHR

              --> right click on diabetes on the left (if there's lots of stuff,
                  you can clear that pane from an icon on the upper left of the Network tab
                  and hit the search magnifying glass in the ATLAS window)
              --> from the right click context menu --> Copy --> Copy request headers
            Then copy the Authorization value in place of all this text
    ''',
    'sec-ch-ua-mobile': '?0',
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.110 Safari/537.36',
    'sec-ch-ua-platform': '"Windows"',
    'Origin': 'https://atlas.pm.jh.edu',
    'Sec-Fetch-Site': 'same-site',
    'Sec-Fetch-Mode': 'cors',
    'Sec-Fetch-Dest': 'empty',
    'Referer': 'https://atlas.pm.jh.edu/',
    'Accept-Encoding': 'gzip, deflate, br',
    'Accept-Language': 'en-US,en;q=0.9',
}

r = requests.get(
    url='https://atlas.pm.jh.edu:8443/WebAPI/vocabulary/CAMP_OMOP_Projection/search/diabetes',
    headers=headers)

print(json.dumps(r.json(), indent=4, sort_keys=True))


