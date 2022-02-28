#!/bin/bash

ticket=`./get_single_ticket.sh`
echo $ticket

curl -w '\n' -G "https://vsac.nlm.nih.gov/vsac/tagName/CMS eMeasure ID/tagValues?ticket=$ticket"


