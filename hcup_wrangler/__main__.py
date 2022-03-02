"""Take an HCUP data set and convert to enclave data set
Resources
- https://docs.google.com/spreadsheets/d/1cbHB9AZLpirOz4_N7SrsnDLomg1I6VgbPFp8rzGnpzc/edit#gid=510825150
"""
import os
from argparse import ArgumentParser
from datetime import datetime, timezone
from typing import Dict
from uuid import uuid4

import pandas as pd


PKG_ROOT = os.path.dirname(os.path.realpath(__file__))
PROJECT_ROOT = os.path.join(PKG_ROOT, '..')
DATA_DIR = os.path.join(PROJECT_ROOT, 'data')
CONCEPT_CSV_NAME = 'Dx_Concepts_Codes_for_Enclave.csv'
CONCEPT_METADATA_CSV_NAME = 'CCSR_Prov_Intent_Limit.csv'
PROJECT_NAME = 'RP-4A9E27'
PALANTIR_ENCLAVE_USER_ID_1 = 'a39723f3-dc9c-48ce-90ff-06891c29114f'
HCUP_CODESYSTEM = 'ICD10CM'
HCUP_LABEL_PREFIX = '[HCUP] '


# to-do: Shared lib for this stuff?
# noinspection DuplicatedCode
def _save_csv(df: pd.DataFrame, output_name, source_name, filename, field_delimiter=','):
    """Side effects: Save CSV"""
    date_str = datetime.now().strftime('%Y.%m.%d')
    out_dir = os.path.join(DATA_DIR, output_name, source_name, date_str, 'output')
    os.makedirs(out_dir, exist_ok=True)
    output_format = 'csv' if field_delimiter == ',' else 'tsv' if field_delimiter == '\t' else 'txt'
    outpath = os.path.join(out_dir, f'{filename}.{output_format}')
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
        help='Path to input directory. This should be a folder with 2 files: "CCSR_Prov_Intent_Limit.csv" and '
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
        concept_metadata_csv_name_df, concept_csv_name_df, how='left',
        left_on=['CCSR'], right_on=['ccsr_code'])

    # Fix codes
    df['icd10cm_code'] = df['icd10cm_code'].apply(_icd10cm_code_fixer)

    return df


def get_palantir_csv_from_hcup(
    hcup_value_set_items: pd.DataFrame, field_delimiter=',', output_name='palantir-three-file', source_name='hcup',
    filename1='concept_set_version_item_rv_edited', filename2='code_sets', filename3='concept_set_container_edited'
) -> Dict[str, pd.DataFrame]:
    """Convert VSAC hiearchical XML to CSV compliant w/ Palantir's OMOP-inspired concept set editor data model"""
    # I. Create IDs that will be shared between files
    ccsr__enclave_code_set_id__map_csv_path = os.path.join(PROJECT_ROOT, 'data', 'cset.csv')
    ccsr__enclave_code_set_id__df = pd.read_csv(ccsr__enclave_code_set_id__map_csv_path)
    ccsr__codeset_id__map = dict(zip(
        ccsr__enclave_code_set_id__df['ccsr_code'],
        ccsr__enclave_code_set_id__df['internal_id']))
    ccsr_codes = list(hcup_value_set_items['CCSR'].unique())

    # II. Create & save exports
    _all = {}
    # 1. Palantir enclave table: concept_set_version_item_rv_edited
    rows1 = []
    codeset_id__code__map = {}
    for i, this_value_set_items in hcup_value_set_items.iterrows():
        codeset_id = ccsr__codeset_id__map[this_value_set_items['ccsr_code']]
        code = this_value_set_items['icd10cm_code']

        # This will help us avoid duplicate codes in single concept set
        if codeset_id not in codeset_id__code__map:
            codeset_id__code__map[codeset_id] = []
        if code not in codeset_id__code__map[codeset_id]:
            codeset_id__code__map[codeset_id].append(code)
        else:
            continue

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
            'includeDescendants': False,
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
    _save_csv(df_code_set_members, output_name, source_name, filename1, field_delimiter)

    # 2. Palantir enclave table: code_sets
    rows2 = []
    for ccsr_code in ccsr_codes:
        this_value_set_items = hcup_value_set_items[hcup_value_set_items['CCSR'] == ccsr_code]
        codeset_id = ccsr__codeset_id__map[ccsr_code]
        # to-do: The source dataset comes in format like f'{ccsr_code} {description}'.
        # ...Maybe we should do: .replace(codeset_id, '').
        concept_set_name = HCUP_LABEL_PREFIX + list(this_value_set_items['ccsr_description'])[0].replace(ccsr_code + ' ', '')
        row = {
            'codeset_id': codeset_id,
            'concept_set_name': concept_set_name,
            'concept_set_version_title': concept_set_name + ' (v1)',
            'project': PROJECT_NAME,  # always use this project id for bulk import
            'source_application': 'EXTERNAL VSAC',
            'source_application_version': '',  # nullable
            'created_at': _datetime_palantir_format(),
            'atlas_json': '',  # nullable
            'is_most_recent_version': True,
            'version': 1,
            'comments': 'Exported from VSAC and bulk imported to N3C.',
            'intention': list(this_value_set_items['INTENTION'])[0],  # nullable
            'limitations': list(this_value_set_items['LIMITATION'])[0],  # nullable
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
            'provenance': list(this_value_set_items['PROVENANCE'])[0] + '; CCSR Code: ' + ccsr_code,
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
    _save_csv(df_code_sets, output_name, source_name, filename2, field_delimiter)

    # 3. Palantir enclave table: concept_set_container_edited
    rows3 = []
    for ccsr_code in ccsr_codes:
        this_value_set_items = hcup_value_set_items[hcup_value_set_items['CCSR'] == ccsr_code]
        codeset_id = ccsr__codeset_id__map[ccsr_code]
        concept_set_name = HCUP_LABEL_PREFIX + list(this_value_set_items['ccsr_description'])[0].replace(ccsr_code + ' ', '')
        row = {
            'concept_set_id': codeset_id,
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
            'intention': list(this_value_set_items['INTENTION'])[0],  # nullable
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
    _save_csv(df_code_sets__container_variation, output_name, source_name, filename3, field_delimiter)

    return _all


def run(input_dir_path: str):
    """Does the transform"""
    # Read data
    codes_df: pd.DataFrame = load_cup_data(input_dir_path)
    # Write CSVs
    get_palantir_csv_from_hcup(codes_df)


# Runtime
cli()
