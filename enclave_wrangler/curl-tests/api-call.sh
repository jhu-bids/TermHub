#!/bin/bash
source ../../env/.env
echo curl \"$1\" -H \"authorization: Bearer $PALANTIR_ENCLAVE_AUTHENTICATION_BEARER_TOKEN\"
curl $1 -H "authorization: Bearer $PALANTIR_ENCLAVE_AUTHENTICATION_BEARER_TOKEN" | json_pp

