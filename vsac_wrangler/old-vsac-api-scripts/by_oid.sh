#!/bin/bash

cd "$(dirname "$(realpath "$0")")"

#echo current dir: `pwd`

oid=$1
ticket=`./get_single_ticket.sh`

echo curl -s -G "https://vsac.nlm.nih.gov/vsac/svs/RetrieveValueSet?id=$oid&ticket=$ticket"
curl -s -G "https://vsac.nlm.nih.gov/vsac/svs/RetrieveValueSet?id=$oid&ticket=$ticket"

# example:
# sh ./by_oid.sh 2.16.840.1.113883.3.464.1003.109.12.1028



#url="https://vsac.nlm.nih.gov/vsac/svs/RetrieveValueSet?id=$oid&ticket=$ticket"
#echo $url
#curl -w '\n' -G $url


