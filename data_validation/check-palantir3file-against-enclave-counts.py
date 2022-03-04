import pandas as pd

def quick_and_dirty():
    versions = pd.read_csv('data/palantir-three-file/Lisa3/2022.03.02/output/code_sets.csv')
    csets = pd.read_csv('data/palantir-three-file/Lisa3/2022.03.02/output/concept_set_container_edited.csv')
    items = pd.read_csv('data/palantir-three-file/Lisa3/2022.03.02/output/concept_set_version_item_rv_edited.csv')
    counts = pd.read_csv('data/Lisa3forMarch9Bonanza/code_counts_back_from_enclave.csv', keep_default_na=False)
    counts['prefix'] = counts.concept_set_name.str.replace('\].*', ']', regex=True)

    cv = pd.merge(counts,versions, on='concept_set_name', how='left')
    by_annotation = cv.groupby('annotation').count()

    print(by_annotation)




if __name__ == '__main__':
    quick_and_dirty()