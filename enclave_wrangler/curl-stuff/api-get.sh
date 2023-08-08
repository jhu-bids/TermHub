#!/bin/bash
source $( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )/../../env/.env

usage() { echo "$0 usage:" && grep " .)\ *#" $0; exit 0; }
no_args="true"
echo_only="false"
while getopts ":hcd:a:u:" option; do
  case ${option} in
    a | u)  # api (url), the part after the ontology RID, generally starting with "objects/..." or "actions/..."
            api=${OPTARG}
            ;;
    c)      # echo curl command, don't run it
            echo_only="true"
            ;;
    d)      # specify json data (for actions or queries) -- only works with -c
            data=\'${OPTARG}\'
            ;;
            # [[ "$echo_only" == "false" ]] && { echo "can't get data to work; use -c option and copy/paste command"; exit 1; }
    h | *)  # Display help
            ;;
  esac
  no_args="false"
done

[[ "$no_args" == "true" ]] && { usage; exit 1; }

shift $((OPTIND - 1))

read -r -d '' cmd <<EOF
curl  -s -H "Content-type: application/json" \\
      -H "Authorization: Bearer \$TOKEN"  \\
      https://unite.nih.gov/api/v1/ontologies/ri.ontology.main.ontology.00000000-0000-0000-0000-000000000000/$api | jq
EOF

if [[ ! -z "$data" ]] ; then
  read -r -d '' cmd <<EOF
  curl  -s -H "Content-type: application/json" \\
        -H "Authorization: Bearer \$TOKEN"  \\
        --data $data \\
        https://unite.nih.gov/api/v1/ontologies/ri.ontology.main.ontology.00000000-0000-0000-0000-000000000000/$api | jq
EOF
fi

if [ "$echo_only" = true ] ; then
  echo "$cmd"
  exit;
fi

if [[ -z "$data" ]] ; then
  curl -s -H "Content-type: application/json" \
      -H "Authorization: Bearer $TOKEN" \
      https://unite.nih.gov/api/v1/ontologies/ri.ontology.main.ontology.00000000-0000-0000-0000-000000000000/$api  | jq
else  # doesn't work, don't know why
  curl -s -H "Content-type: application/json" \
      -H "Authorization: Bearer $TOKEN" \
      -d $data \
      https://unite.nih.gov/api/v1/ontologies/ri.ontology.main.ontology.00000000-0000-0000-0000-000000000000/$api  | jq
fi
