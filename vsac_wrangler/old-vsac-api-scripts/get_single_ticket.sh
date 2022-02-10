#!/bin/bash


TGT=`./get_tgt.sh`

curl -s -w '\n' --data "service=http://umlsks.nlm.nih.gov" https://vsac.nlm.nih.gov/vsac/ws/Ticket/$TGT
