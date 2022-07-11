#!/bin/bash
source ../../env/.env

ONTOLOGY_RID=`curl \
                  -H "Content-type: application/json" \
                  -H "Authorization: Bearer $TOKEN" \
                  "https://$HOSTNAME/api/v1/ontologies" | sed 's/^.*\"rid\":\"//' | sed 's/\".*//'
              `

curl \
        -H "Content-type: application/json" \
        -H "Authorization: Bearer $TOKEN" \
        "https://$HOSTNAME/api/v1/ontologies/$ONTOLOGY_RID/objects/OmopConceptSetVersionItem"
