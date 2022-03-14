import pandas as pd
import os
import re
import json
import pprint
pp = pprint.PrettyPrinter(compact=True)

THREE_FILES = ('code_sets.csv', 'concept_set_container_edited.csv', 'concept_set_version_item_rv_edited.csv')
VSAC_PATH = 'data/palantir-three-file/Lisa3/2022.03.02/output'
HCUP_PATH = 'data/palantir-three-file/hcup/2022.03.02/output'

def load3file(dirpath):
    return (pd.read_csv(os.path.join(dirpath, file)) for file in THREE_FILES)


def strip(s: str) -> str:   # concept_set_name fixes
    '''
    part of what stumped me for a while: a bunch of the enclave concept_set_names have an ASCII 183 at the end
    which looks like this:  ·  , a period in the middle of the line. don't ask me why

    another: the enclave unhelpfully "fixed" our double spaces so  '[VSAC] Bells Palsy,  codes for AE reporting'
    in the CSV ended up '[VSAC] Bells Palsy, codes for AE reporting' on the enclave
    '''
    s = re.sub(r'[·\s]+$', '', s)   # fix ASCII 183 and any whitespace at end of lines (like trim, but more)
    s = re.sub(r'^[·\s]+', '', s)   # do same at beginning for good measure, currently has no effect
    s = re.sub(r'  +', ' ', s)      # within lines convert multiple space to single space to match enclave
    return s


def addPrefix(df: pd.DataFrame) -> pd.DataFrame:
    df['prefix'] = df.cset_id.str.replace('\].*', ']', regex=True) # prefix = [VSAC] or [HCUP]
    return df


def delete_rows(df: pd.DataFrame) -> pd.DataFrame:
    # delete unneeded rows (doing this on enclave now? well doesn't hurt)
    df = df[df.prefix != '[VSAC Bulk-Import test]']
    df = df[df.cset_id.str.endswith(' Requests') != True]
    df = df[df.cset_id.str.startswith('[')]
    return df


def quick_and_dirty():
    '''
    counts is from /UNITE/[RP-4A9E27] DI&H - Data Quality/Users/Harold/workbook-output/Non-Archived Concept Sets (2021-05-21 at 08:59:45.15 AM)/Expr Items By Cset
            url: https://unite.nih.gov/workspace/data-integration/dataset/preview/ri.foundry.main.dataset.4b3df5ac-9389-4d83-8599-4dea3479ad3f/master
      which comes from code_system_concept_set_version_expression_item_schema_edited with
      concept_set_name added from /N3C Export Area/Concept Set Ontology/Concept Set Ontology/hubble_base/code_sets

      the query for it is:  SELECT  annotation,
                                    cset_id,
                                    count(distinct code, codeSystem) AS code_count,
                                    collect_set(codeSystem || ':' || code) AS codesyscode
                            FROM expr_items_plus_cset_name
                            WHERE annotation IS NOT NULL
                              AND cset_id LIKE '[VSAC]%' or cset_id LIKE '[HCUP]%'
                            GROUP BY 1,2
    '''

    now = re.sub(r':\d\d\.\d+', '', str(pd.to_datetime('today')))
    print(f"\nOutput from {os.path.basename(__file__)} on {now}\n")

    counts = pd.read_csv('data/Lisa3forMarch9Bonanza/code_counts_back_from_enclave.csv', keep_default_na=False)
    counts['concept_set_name'] = list(counts['cset_id'])  # copy cset_id to concept_set_name (same thing, but see below)

    vsac_dfs = list(load3file(VSAC_PATH))
    hcup_dfs = list(load3file(HCUP_PATH))

    # combine into single dfs for easier comparison
    versions, csets, items = [pd.concat([vsac_dfs[i], hcup_dfs[i]]) for i in range(3)]

    # make a corrected name column using strip function (above) called cset_id
    for df in versions, csets, counts:
        df['cset_id'] = df.concept_set_name.apply(strip)
        df = addPrefix(df)

    counts = delete_rows(counts)

    # find cset_ids only in counts or only in cvs
    # missing_from_enclave = set(versions.cset_id) - set(counts.cset_id)
    missing_from_enclave = set(versions.cset_id) - set(counts[counts.archived == False].cset_id)
    extra_on_enclave = set(counts.cset_id) - set(versions.cset_id)

    if len(missing_from_enclave) > 0:   # currently not a problem. fail if it starts happening
        missing_because_archived_on_enclave = set(versions.cset_id).intersection(set(counts[counts.archived == True].cset_id))
        print(f"{len(missing_because_archived_on_enclave)} CVS csets exist on enclave but are archived: " +
              ''.join([f'\n    {name}' for name in missing_because_archived_on_enclave]) + '\n\n')
        if missing_from_enclave > missing_because_archived_on_enclave:
            raise Exception("CSV csets exist that didn't get to enclave at all: " + ''.join([f'\n   {n}' for n in missing_from_enclave]))


    if len(extra_on_enclave) > 0:       # csets on enclave that we didn't expect,
                                        # print these out and figure out where they came from
        print(f"{len(extra_on_enclave)} csets exist on enclave but not CSVs: " +
                ''.join([f'\n    {name}' for name in extra_on_enclave]) + '\n\n')

        # get rid of enclave records missing from csv
        counts = counts[counts.cset_id.apply(lambda n: n not in extra_on_enclave)]

    # so far only compared based on name, now going to compare on included codes

    # lookup from codeset_id (our internal id) to concept set name (cset_id)
    codesetid2name = dict(zip(versions.codeset_id, versions.cset_id))

    items['cset_id'] = [codesetid2name[id] for id in items.codeset_id]
    items['csv_codes'] = items.codeSystem + ':' + items.code

    counts['enclave_codes'] = list(counts.codesyscode.apply(lambda s: s[2:-2].split(', ')).apply(lambda x: set(x)))

    # len(list(list(counts[counts.cset_id == '[VSAC] Diabetes'].enclave_codes)[0]))

    itemgrps = items.groupby('cset_id')['csv_codes'].agg(csv_codes=lambda x: set(x), csv_code_count=lambda x: len(x))

    versions['internal_id'] = versions['codeset_id']
    csvcodes = versions[['internal_id', 'cset_id']].merge(itemgrps, on='cset_id', how='outer')
    csvcodes['csv_code_count'] = csvcodes.csv_code_count.astype('Int64')

    enclavecodes = pd.DataFrame({'cset_id': list(counts.cset_id),
                                 'enclave_codes': list(counts.enclave_codes),
                                 'enclave_code_count': list(counts.code_count.astype('Int64'))})

    # enclavecodes = counts[['cset_id', 'enclave_codes', ]] # where's 'codeset_id', ?
    # enclavecodes['enclave_code_count'] = counts['code_count'].astype('Int64')

    merged = csvcodes.merge(enclavecodes, on='cset_id', how="outer")

    for i, r in merged.iterrows():
        try:
            codes_missing_from_enclave = r.csv_codes - r.enclave_codes
            codes_extra_in_enclave = r.enclave_codes - r.csv_codes
            if len(codes_missing_from_enclave):
                print(f'{r.cset_id} ({r.internal_id}) is missing {len(codes_missing_from_enclave)} codes on enclave: ' +
                        ','.join(codes_missing_from_enclave))
            if len(codes_extra_in_enclave):
                print(f'{r.cset_id} ({r.internal_id}) has {len(codes_extra_in_enclave)} extra codes on enclave: ' +
                        ','.join(codes_extra_in_enclave))
        except Exception as e:
            print("problem with pair:")
            print(r)

    return


'''     Here's what the output looks like:

CSV csets exist on enclave but not CSVs: 
{'[VSAC] Acute Respiratory Distress Syndrome 214',
 '[VSAC] Acute Respiratory Distress Syndrome 215',
 '[VSAC] Acute Respiratory Distress Syndrome 367', '[VSAC] Anemia 321',
 '[VSAC] Anemia 322', '[VSAC] Anemia 323', '[VSAC] Autoimmune Disease 309',
 '[VSAC] Autoimmune Disease 310',
 '[VSAC] Disseminated Intravascular Coagulation 223',
 '[VSAC] Disseminated Intravascular Coagulation 224',
 '[VSAC] Social Determinants of Health Conditions'}

                                               cset_id    csv  enclave
24                          [VSAC] Acute Heart Failure    10          21
25            [VSAC] Acute Myocardial Infarction (AMI)    63         100
26                          [VSAC] Acute Renal Failure    17          23
28                  [VSAC] Air and Thrombotic Embolism    76         106
31                                   [VSAC] Arrhythmia   111         113
40                                  [VSAC] Bradycardia     8          11
46                              [VSAC] Cardiac Surgery    82         100
50        [VSAC] Chronic Obstructive Pulmonary Disease     8          15
51                        [VSAC] Chronic Stable Angina    23          50
60                                     [VSAC] Diabetes   281         639
61                      [VSAC] Diastolic Heart Failure    11          19
63                                    [VSAC] Eclampsia     9          15
87                                  [VSAC] Hypotension    17          24
88                               [VSAC] Hypothyroidism    85          94
112  [VSAC] Mental Behavioral and Neurodevelopmenta...  2036        2804
115                       [VSAC] Myocardial Infarction    54         101
'''

if __name__ == '__main__':
    quick_and_dirty()