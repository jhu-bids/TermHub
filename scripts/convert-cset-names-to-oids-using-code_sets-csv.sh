#!/bin/bash

# head -1 input/enclave_3_csv_files/code_sets.csv
echo oid
while read p; do
        echo fgrep \'$p\' input/enclave_3_csv_files/code_sets.csv
done < input/dup_cset_ids.txt | bash | awk -F, '{print $20}' | awk -F\; '{print $2}' | sed 's/[^0123456789\.]*//' | grep -v '^$'
