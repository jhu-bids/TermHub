#!/bin/bash

GIT_ROOT=$(git rev-parse --show-toplevel)
. "${GIT_ROOT}/env/.env"

if test `find "tgt.txt" -mmin -1` ; then
  >&2 echo "ticket still fresh"
else
  >&2 echo "fetching new ticket"
  # curl -w '\n' --data "username=$VSAC_API_USER&password=$VSAC_API_PWD"  https://vsac.nlm.nih.gov/vsac/ws/Ticket > tgt.txt
  curl -w '\n' --data "apikey=$VSAC_API_KEY"  https://vsac.nlm.nih.gov/vsac/ws/Ticket > tgt.txt
fi
TGT=`cat tgt.txt`
echo $TGT
