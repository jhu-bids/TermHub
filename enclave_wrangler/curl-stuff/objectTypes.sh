#!/bin/sh
source /Users/sigfried/git-repos/TermHub/env/.env
curl  -H "Content-type: application/json" \
            -H "Authorization: Bearer $PALANTIR_ENCLAVE_AUTHENTICATION_BEARER_TOKEN" \
            https://unite.nih.gov/api/v1/ontologies/ri.ontology.main.ontology.00000000-0000-0000-0000-000000000000/objectTypes | jq
