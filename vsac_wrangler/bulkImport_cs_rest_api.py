from typing import Dict, List, OrderedDict
from bs4 import BeautifulSoup
import requests
import urllib3.util
import xmltodict as xd
# print(pd.__version__)

###createNewConceptSet
##"ri.actions.main.parameter.36a1670f-49ca-4491-bb42-c38707bbcbb2":
##cs1 = 	{		"type": "objectLocator",
##			"objectLocator": 	{
##		"objectTypeId": "omop-concept-set-container",
##		"primaryKey": {
##			"concept_set_id": {
##				"type": "string",
##				"string": "Stephanie's concept set"
##			}
##		}
##	}
## }

#def post_cs_container( cs_create_data ):
    # """create a concept set container """
    #
    # url = f'https://unite.nih.gov/actions/'
    # header= get_header()
    # response = requests.post( url, data=cs_create_data)
    #
    # r = response.json()
    # return r


###createNewDraftConceptSetVersion
###createCodeSystmeConceptVersionExpressionItems
