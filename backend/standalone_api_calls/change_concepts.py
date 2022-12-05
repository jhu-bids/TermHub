# TODO: make this a test case
import pandas as pd
from pathlib import Path
import os
from backend.app import route_upload_new_container_with_concepts, route_upload_new_cset_version_with_concepts
from backend.pandas_data_munging import Bunch

PROJECT_DIR = Path(os.path.dirname(__file__)).parent.parent
CSV_DIR = os.path.join(PROJECT_DIR, 'termhub-csets/n3c-upload-jobs')

def run():
  # fname = os.path.join(CSV_DIR, 'Other Diabetes.csv')
  fname = os.path.join(CSV_DIR, 'diabetes-recommended-csets-modifications', 'type-2-diabetes-mellitus.csv')
  df = pd.read_csv(fname).fillna('')
  omop_concepts = df[[
      'concept_id',
      'includeDescendants',
      'isExcluded',
      'includeMapped',
      'annotation']].to_dict(orient='records')
  new_version = {
    "omop_concepts": omop_concepts,
    "provenance": "Created through TermHub.",
    "concept_set_name": "[DM]Type2 Diabetes Mellitus",
    "limitations": "",
    "intention": "",
    "on_behalf_of": '5c560c3e-8e55-485c-9a66-f96285f273a0'
  }
  new_version = Bunch(new_version)
  res = route_upload_new_cset_version_with_concepts(new_version)
  print(df)

# includedescendants isexcluded includemapped

if __name__ == '__main__':
  run()
