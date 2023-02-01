#!/bin/sh
source /Users/sigfried/git-repos/TermHub/env/.env

curl -H "Content-type: application/json" -H "Authorization: Bearer $PALANTIR_ENCLAVE_AUTHENTICATION_BEARER_TOKEN" \
        https://unite.nih.gov/api/v1/ontologies/$ONTOLOGY_RID/objects/OMOPConcept/258780/links/omopConceptAncestorRelationship |jq
