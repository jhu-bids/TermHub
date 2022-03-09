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


def strip(s: str) -> str:
    s = re.sub(r'^[·\s]+', '', s)
    s = re.sub(r'[·\s]+$', '', s)
    s = re.sub(r'  +', ' ', s)
    return s

def addPrefix(df: pd.DataFrame) -> pd.DataFrame:
    df['prefix'] = df.cset_id.str.replace('\].*', ']', regex=True)
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

    counts = pd.read_csv('data/Lisa3forMarch9Bonanza/code_counts_back_from_enclave.csv', keep_default_na=False)
    counts['concept_set_name'] = list(counts['cset_id'])  # counts already has cset_id, copy it to concept_set_name

    vsac_dfs = load3file(VSAC_PATH)
    hcup_dfs = load3file(HCUP_PATH)
    versions, csets, items = [pd.concat([vsac_dfs[i], hcup_dfs[i]]) for i in range(3)]

    # for the rest, make a corrected name column called cset_id
    for df in versions, v_versions, h_versions, csets, h_csets, v_csets:
        df['cset_id'] = df.concept_set_name.apply(strip)

    for df in versions, v_versions, h_versions, csets, h_csets, v_csets:

    # some of this code was written just to figure out what was going on with all this messed up data and how to fix it
    # part of what stumped me for a long time. A bunch of the enclave concept_set_names have an ASCII 183 at the end
    # which looks like this:  ·  , a period in the middle of the line. don't ask me why

    # another: the enclave unhelpfully "fixed" our double spaces so  '[VSAC] Bells Palsy,  codes for AE reporting'
    # in the CSV ended up '[VSAC] Bells Palsy, codes for AE reporting' on the enclave

    counts['prefix'] = counts.cset_id.str.replace('\].*', ']', regex=True)
    v_versions['prefix'] = v_versions.concept_set_name.str.replace('\].*', ']', regex=True)
    h_versions['prefix'] = h_versions.concept_set_name.str.replace('\].*', ']', regex=True)
    versions['prefix'] = versions.concept_set_name.str.replace('\].*', ']', regex=True)

    counts['cset_id'] = counts.concept_set_name.apply(strip)
    counts['whitespace'] = counts.concept_set_name == counts.cset_id

    versions['cset_id'] = versions.concept_set_name.apply(strip)
    csets['cset_id'] = csets.concept_set_name.apply(strip)

    counts = counts[counts.prefix != '[VSAC Bulk-Import test]']
    counts = counts[counts.cset_id.str.endswith(' Requests') != True]
    counts = counts[counts.cset_id.str.startswith('[')]

    missing_from_enclave = set(versions.cset_id) - set(counts.cset_id)
    extra_on_enclave = set(counts.cset_id) - set(versions.cset_id)

    if len(missing_from_enclave) > 0:
        raise Exception("CSV csets exist that didn't get to enclave: " + ''.join([f'\n   {n}' for n in missing_from_enclave]))

    if len(extra_on_enclave) > 0:
        print("CSV csets exist on enclave but not CSVs: ")
        pp.pprint(extra_on_enclave)


    codesetid2name = dict(zip(versions.codeset_id, versions.concept_set_name))

    items['cset_id'] = [codesetid2name[id] for id in items.codeset_id]
    items['cd'] = items.codeSystem + ':' + items.code

    counts['cd'] = counts.codesyscode.apply(lambda s: s[2:-2].split(', ')).apply(lambda x: set(x))

    len(list(list(counts[counts.cset_id == '[VSAC] Diabetes'].cd)[0]))

    itemgrps = items.groupby('cset_id')['cd'].agg(codesyscode=lambda x: set(x), len=lambda x: len(x))

    count_pairs = pd.DataFrame(items.groupby('cset_id')['cd'].nunique().reset_index()
                                ).merge(counts[['cset_id', 'code_count']], on='cset_id', how='left')

    count_pairs['cd'] = count_pairs.cd.astype('Int64')
    count_pairs['code_count'] = count_pairs.code_count.astype('Int64')

    discrepant_csets = count_pairs[abs(count_pairs.code_count - count_pairs.cd) > 0]

    cc = counts[['cset_id', 'cd']].merge(discrepant_csets, on='cset_id')

    [r.codesyscode - r.cd_x for n, r in cc.iterrows()]
    [r.cd_x - r.codesyscode for n, r in cc.iterrows()]

    cc = cc.merge(itemgrps, on='cset_id')
    print(discrepant_csets)

    return discrepant_csets


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

                                               cset_id    cd  code_count
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