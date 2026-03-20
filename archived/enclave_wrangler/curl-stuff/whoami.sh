#!/bin/sh
source $( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )/../../env/.env

curl  -H "Content-type: application/json" -H "Authorization: Bearer $TOKEN" https://unite.nih.gov/multipass/api/me | jq
