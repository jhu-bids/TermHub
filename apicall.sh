#!/bin/bash
source ./env/.env

#!/bin/bash

curl \
      -H "Content-type: application/json" \
      -H "Authorization: Bearer $TOKEN" \
      "https://$HOSTNAME/api/v1/ontologies/$ONTOLOGY_RID/$1"
