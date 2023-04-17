#!/bin/sh
source ../../env/.env
curl  -H "Content-type: application/json" \
            -H "Authorization: Bearer $TOKEN" \
            https://unite.nih.gov/api/v1/ontologies/ri.ontology.main.ontology.00000000-0000-0000-0000-000000000000/objectTypes | jq
