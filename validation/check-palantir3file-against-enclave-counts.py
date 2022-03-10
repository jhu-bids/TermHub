import pandas as pd
import os
import re
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


def quick_and_dirty():
    v_versions, v_csets, v_items = load3file(VSAC_PATH)
    vsac_dfs = [v_versions, v_csets, v_items]
    h_versions, h_csets, h_items = load3file(HCUP_PATH)
    hcup_dfs = [h_versions, h_csets, h_items]
    versions, csets, items = [pd.concat([vsac_dfs[i], hcup_dfs[i]]) for i in range(3)]

    counts = pd.read_csv('data/Lisa3forMarch9Bonanza/code_counts_back_from_enclave.csv', keep_default_na=False)

    # some of this code was written just to figure out what was going on with all this messed up data and how to fix it
    # part of what stumped me for a long time. A bunch of the enclave concept_set_names have an ASCII 183 at the end
    # which looks like this:  ·  , a period in the middle of the line. don't ask me why

    # another: the enclave unhelpfully "fixed" our double spaces so  '[VSAC] Bells Palsy,  codes for AE reporting'
    # in the CSV ended up '[VSAC] Bells Palsy, codes for AE reporting' on the enclave

    counts['prefix'] = counts.cset_id.str.replace('\].*', ']', regex=True)
    v_versions['prefix'] = v_versions.concept_set_name.str.replace('\].*', ']', regex=True)
    h_versions['prefix'] = h_versions.concept_set_name.str.replace('\].*', ']', regex=True)
    versions['prefix'] = versions.concept_set_name.str.replace('\].*', ']', regex=True)

    counts['concept_set_name'] = list(counts['cset_id'])
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

    count_pairs = pd.DataFrame(items.groupby('cset_id')['cd'].nunique().reset_index()
                                ).merge(counts[['cset_id', 'code_count']], on='cset_id', how='left')

    count_pairs['cd'] = count_pairs.cd.astype('Int64')
    count_pairs['code_count'] = count_pairs.code_count.astype('Int64')

    discrepant_csets = count_pairs[abs(count_pairs.code_count - count_pairs.cd) > 0]
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