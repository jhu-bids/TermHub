#!/bin/bash
source ./env/.env

cmd="curl $1 -H \"authorization: Bearer $PALANTIR_ENCLAVE_AUTHENTICATION_BEARER_TOKEN\"" | json_pp

echo calling enclave api with url:
echo $cmd
echo
$cmd
