#!/bin/bash

source .env

if ! find "tgt.txt" -mmin +480 ; then
  [:]
  # echo "ticket still fresh"
else
  # echo "fetching new ticket"
  # curl -w '\n' --data "username=$VSAC_API_USER&password=$VSAC_API_PWD"  https://vsac.nlm.nih.gov/vsac/ws/Ticket > tgt.txt
  curl -w '\n' --data "apikey=$UMLS_API_KEY"  https://vsac.nlm.nih.gov/vsac/ws/Ticket >| tgt.txt
fi
TGT=`cat tgt.txt`
echo $TGT
