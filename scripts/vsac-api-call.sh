#!/bin/bash
source ./env/.env

cmd="curl -u :$VSAC_API_KEY https://cts.nlm.nih.gov/fhir/ValueSet/$1"

echo calling VSAC FHIR API with OID:
echo $cmd
echo
$cmd

