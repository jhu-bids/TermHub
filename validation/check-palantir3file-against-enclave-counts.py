import pandas as pd
import os

THREE_FILES = ('code_sets.csv', 'concept_set_container_edited.csv', 'concept_set_version_item_rv_edited.csv')
VSAC_PATH = 'data/palantir-three-file/Lisa3/2022.03.02/output'
HCUP_PATH = 'data/palantir-three-file/hcup/2022.03.02/output'

def load3file(dirpath):
    return (pd.read_csv(os.path.join(dirpath, file)) for file in THREE_FILES)

def quick_and_dirty():
    v_versions, v_csets, v_items = load3file(VSAC_PATH)
    vsac_dfs = [v_versions, v_csets, v_items]
    h_versions, h_csets, h_items = load3file(HCUP_PATH)
    hcup_dfs = [h_versions, h_csets, h_items]

    versions, csets, items = [pd.concat([vsac_dfs[i], hcup_dfs[i]]) for i in range(3)]

    counts = pd.read_csv('data/Lisa3forMarch9Bonanza/code_counts_back_from_enclave.csv', keep_default_na=False)
    counts['prefix'] = counts.concept_set_name.str.replace('\].*', ']', regex=True)

    ann_pre = {x[0]: x[1].groupby('annotation') for x in counts.groupby('annotation')}

    for pre, g in counts.groupby('prefix'):
        print(f'{pre}   {len(g)}')
        for ann, gg in g.groupby('annotation'):
            print(f'    {ann}   {len(gg)}')

    try:
        print(f"vsac enclave sets: {len(set(counts[counts.prefix == '[VSAC]'].concept_set_name))}")
        print(f"vsac csv sets: {len(set(v_versions.concept_set_name))}")
        print(f"hcup enclave sets: {len(set(counts[counts.prefix == '[HCUP]'].concept_set_name))}")
        print(f"hcup csv sets: {len(set(h_versions.concept_set_name))}")
        assert len(set(counts[counts.prefix == '[VSAC]'].concept_set_name) - set(v_versions.concept_set_name))
        assert len(set(v_versions.concept_set_name) - set(counts[counts.prefix == '[VSAC]'].concept_set_name))
        assert len(set(counts[counts.prefix == '[HCUP]'].concept_set_name) - set(h_versions.concept_set_name))
        assert len(set(h_versions.concept_set_name) - set(counts[counts.prefix == '[HCUP]'].concept_set_name))
    except AssertionError as ae:
        print(ae)



    cv = pd.merge(counts,versions, on='concept_set_name', how='left')
    by_annotation = cv.groupby('annotation').count()

    print(by_annotation)

    set(counts[counts.annotation == 'Curated HCUP CCSR value set.'].concept_set_name)


if __name__ == '__main__':
    quick_and_dirty()