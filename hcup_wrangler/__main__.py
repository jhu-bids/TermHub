"""Take an HCUP data set and convert to enclave data set"""
import os
from argparse import ArgumentParser
from datetime import datetime, timezone
from typing import Dict
from uuid import uuid4

import pandas as pd


PKG_ROOT = os.path.dirname(os.path.realpath(__file__))
PROJECT_ROOT = os.path.join(PKG_ROOT, '..')
OUTPUT_DIR = os.path.join(PROJECT_ROOT, 'output', 'hcup')
CONCEPT_CSV_NAME = 'Dx_Concepts_Codes_for_Enclave.csv'
CONCEPT_METADATA_CSV_NAME = 'CCSR_Prov_Intent_Limit.csv'
PALANTIR_ENCLAVE_USER_ID_1 = 'a39723f3-dc9c-48ce-90ff-06891c29114f'
HCUP_CODESYSTEM = 'ICD10CM'
HCUP_LABEL_PREFIX = '[HCUP] '


def _save_csv(df: pd.DataFrame, filename, field_delimiter=','):
    """Side effects: Save CSV"""
    outdir = os.path.join(OUTPUT_DIR)
    if not os.path.exists(outdir):
        os.mkdir(outdir)
    outdir2 = os.path.join(outdir, datetime.now().strftime('%Y.%m.%d'))
    if not os.path.exists(outdir2):
        os.mkdir(outdir2)

    output_format = 'csv' if field_delimiter == ',' else 'tsv' if field_delimiter == '\t' else 'txt'
    outpath = os.path.join(outdir2, f'{filename}.{output_format}')

    df.to_csv(outpath, sep=field_delimiter, index=False)


def _datetime_palantir_format() -> str:
    """Returns datetime str in format used by palantir data enclave
    e.g. 2021-03-03T13:24:48.000Z (milliseconds allowed, but not common in observed table)"""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")[:-4] + 'Z'


def _icd10cm_code_fixer(code):
    """Fixes ICD10CM codes"""
    new_code = code[0:3]
    if len(code) > 3:
        new_code += '.' + code[3:]
    return new_code


def cli():
    """Command line interface"""
    package_description = 'Tool for converting HCUP value sets into enclave uploadable value sets.'
    parser = ArgumentParser(description=package_description)
    parser.add_argument(
        '-p', '--input-dir-path', required=False,
        help='Path to input directory. This should be a folder with 2 files: "CSSR_Prov_Intent_Limit.csv" and '
             '"Dx_Concepts_Codes_for_Enclave.csv".')
    kwargs = parser.parse_args()
    kwargs_dict: Dict = vars(kwargs)
    run(**kwargs_dict)


def load_cup_data(input_dir_path: str) -> pd.DataFrame:
    """Load HCUP data and format as necessary"""
    # Read data
    concept_csv_name_path = os.path.join(input_dir_path, CONCEPT_CSV_NAME)
    concept_metadata_csv_name_path = os.path.join(input_dir_path, CONCEPT_METADATA_CSV_NAME)
    concept_csv_name_df = pd.read_csv(concept_csv_name_path).fillna('')
    concept_metadata_csv_name_df = pd.read_csv(concept_metadata_csv_name_path).fillna('')

    # Filter by x mark, which means we should include it
    concept_csv_name_df = concept_csv_name_df[
        (concept_csv_name_df['x_mark'] == 'X') | (concept_csv_name_df['x_mark'] == 'x')]

    # JOIN
    df: pd.DataFrame = pd.merge(
        concept_csv_name_df, concept_metadata_csv_name_df, how='left',
        left_on=['ccsr_code'], right_on=['CCSR'])

    # Fix codes
    df['icd10cm_code'] = df['icd10cm_code'].apply(_icd10cm_code_fixer)

    return df


def get_palantir_csv_from_hcup(
    hcup_value_sets: pd.DataFrame, field_delimiter=',', filename1='concept_set_version_item_rv_edited',
    filename2='code_sets', filename3='concept_set_container_edited'
) -> Dict[str, pd.DataFrame]:
    """Convert VSAC hiearchical XML to CSV compliant w/ Palantir's OMOP-inspired concept set editor data model"""
    # I. Create IDs that will be shared between files
    cssr__enclave_code_set_id__map_csv_path = os.path.join(PROJECT_ROOT, 'data', 'cset.csv')
    cssr__enclave_code_set_id__df = pd.read_csv(cssr__enclave_code_set_id__map_csv_path)
    cssr__codeset_id__map = dict(zip(
        cssr__enclave_code_set_id__df['ccsr_code'],
        cssr__enclave_code_set_id__df['internal_id']))

    # II. Create & save exports
    _all = {}
    # 1. Palantir enclave table: concept_set_version_item_rv_edited
    rows1 = []
    for i, value_set in hcup_value_sets.iterrows():
        codeset_id = cssr__codeset_id__map[value_set['ccsr_code']]
        code = value_set['icd10cm_code']
        code_system = HCUP_CODESYSTEM
        # The 3 fields isExcluded, includeDescendants, and includeMapped, are from OMOP but also in VSAC. If it has
        # ...these 3 options, it is intensional. And when you execute these 3, it is now extensional / expansion.
        row = {
            'codeset_id': codeset_id,
            'concept_id': '',  # leave blank for now
            # <non-palantir fields>
            'code': code,
            'codeSystem': code_system,
            # </non-palantir fields>
            'isExcluded': False,
            'includeDescendants': True,
            'includeMapped': False,
            'item_id': str(uuid4()),  # will let palantir verify ID is indeed unique
            'annotation': 'Curated HCUP CCSR value set.',
            # 'created_by': 'DI&H Bulk Import',
            'created_by': PALANTIR_ENCLAVE_USER_ID_1,
            'created_at': _datetime_palantir_format()
        }
        row2 = {}
        for k, v in row.items():
            row2[k] = v.replace('\n', ' - ') if type(v) == str else v
        row = row2
        rows1.append(row)
    df_code_set_members = pd.DataFrame(rows1)
    _all[filename1] = df_code_set_members
    _save_csv(df_code_set_members, filename=filename1, field_delimiter=field_delimiter)

    # 2. Palantir enclave table: code_sets
    rows2 = []
    for i, value_set in hcup_value_sets.iterrows():
        codeset_id = cssr__codeset_id__map[value_set['ccsr_code']]
        # to-do: The source dataset comes in format like f'{ccsr_code} {description}'.
        # ...Maybe we should do: .replace(codeset_id, '').
        concept_set_name = HCUP_LABEL_PREFIX + value_set['ccsr_description']
        row = {
            'codeset_id': codeset_id,
            'concept_set_name': concept_set_name,
            'concept_set_version_title': concept_set_name + ' (v1)',
            'project': 'RP-4A9E',  # always use this project id for bulk import
            'source_application': 'EXTERNAL VSAC',
            'source_application_version': '',  # nullable
            'created_at': _datetime_palantir_format(),
            'atlas_json': '',  # nullable
            'is_most_recent_version': True,
            'version': 1,
            'comments': 'Exported from VSAC and bulk imported to N3C.',
            'intention': value_set['INTENTION'],  # nullable
            'limitations': value_set['LIMITATION'],  # nullable
            'issues': '',  # nullable
            'update_message': 'Initial version.',  # nullable (maybe?)
            # status field stats as appears in the code_set table 2022/01/12:
            # 'status': [
            #     '',  # null
            #     'Finished',
            #     'In Progress',
            #     'Awaiting Review',
            #     'In progress',
            # ][2],
            # status field doesn't show this in stats in code_set table, but UI uses this value by default:
            'status': 'Under Construction',
            'has_review': '',  # boolean (nullable)
            'reviewed_by': '',  # nullable
            'created_by': PALANTIR_ENCLAVE_USER_ID_1,
            'provenance': value_set['PROVENANCE'],
            'atlas_json_resource_url': '',  # nullable
            # null, initial version will not have the parent version so this field would be always null:
            'parent_version_id': '',  # nullable
            # True ( after the import view it from the concept set editor to review the concept set and click done.
            # We can add the comments like we imported from VSAC and reviewed it from the concept set editor. )
            # 1. import 2. manual check 3 click done to finish the definition. - if we want to manually review them
            # first and click Done:
            'is_draft': True,
        }
        rows2.append(row)
    df_code_sets = pd.DataFrame(rows2)
    _all[filename2] = df_code_sets
    _save_csv(df_code_sets, filename=filename2, field_delimiter=field_delimiter)

    # 3. Palantir enclave table: concept_set_container_edited
    rows3 = []
    for i, value_set in hcup_value_sets.iterrows():
        concept_set_name = HCUP_LABEL_PREFIX + value_set['ccsr_description']
        row = {
            'concept_set_id': concept_set_name,
            'concept_set_name': concept_set_name,
            'project_id': '',  # nullable
            'assigned_informatician': PALANTIR_ENCLAVE_USER_ID_1,  # nullable
            'assigned_sme': PALANTIR_ENCLAVE_USER_ID_1,  # nullable
            'status': ['Finished', 'Under Construction', 'N3C Validation Complete'][1],
            'stage': [
                'Finished',
                'Awaiting Editing',
                'Candidate for N3C Review',
                'Awaiting N3C Committee Review',
                'Awaiting SME Review',
                'Under N3C Committee Review',
                'Under SME Review',
                'N3C Validation Complete',
                'Awaiting Informatician Review',
                'Under Informatician Review',
            ][1],
            'intention': value_set['INTENTION'],  # nullable
            'n3c_reviewer': '',  # nullable
            'alias': None,
            'archived': False,
            # 'created_by': 'DI&H Bulk Import',
            'created_by': PALANTIR_ENCLAVE_USER_ID_1,
            'created_at': _datetime_palantir_format()
        }

        row2 = {}
        for k, v in row.items():
            row2[k] = v.replace('\n', ' - ') if type(v) == str else v
        row = row2

        rows3.append(row)
    df_code_sets__container_variation = pd.DataFrame(rows3)
    _all[filename3] = df_code_sets__container_variation
    _save_csv(df_code_sets__container_variation, filename=filename3, field_delimiter=field_delimiter)

    return _all


def run(input_dir_path: str):
    """Does the transform"""
    # Read data
    df: pd.DataFrame = load_cup_data(input_dir_path)
    # Write CSVs
    get_palantir_csv_from_hcup(df)


# Runtime
cli()
