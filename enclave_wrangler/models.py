"""Models

TODO: OO
  - CsetContainer: 0+ versions. 1+ Researcher
  - CsetVersion: 0+ ExpressionItem. 0+ CsetMember. 1+ Researcher
  - ExpressionItem:
  - CsetMember / CsetExpansion(maybe):
  - Researcher:
"""
from typing import Dict, List

import pandas as pd
import csv, io, json
from functools import cache
from collections import defaultdict

from enclave_wrangler.utils import EnclaveWranglerErr, ActionValidateError, get_random_codeset_id, \
    make_objects_request, make_actions_request
from backend.utils import dump, pdump

class ObjWithMetadata:
    def __init__(self):
        pass

    csetVersionFields = {}
    # load this from table https://docs.google.com/spreadsheets/d/1fB-klbxOvxYiSzx3PnibMZPO_n-PSGb8vSx6GuDfuyE/edit#gid=0
    def populate_from_csv(self, df):
        for field in CsetVersion.csetVersionFields:
            first_row = {} # from df
            setattr(self, first_row[field['classPropName']],
                    first_row[field['csv_columns']])


class CsetVersion(ObjWithMetadata):
    """Cset version"""

    def create_new_draft_minimal(self, validate_first: bool = True, **kwargs) -> bool:
        #concept_set_name: str, codeset_id: int, on_behalf_of):
        params = {k.replace('_', '-'): v for k,v in kwargs.items()}
        if 'on-behalf-of' not in params:
            raise EnclaveWranglerErr("on_behalf_of required")
        versionId = get_random_codeset_id()
        params['versionId'] = versionId
        data = {"parameters": params}
        try:
            response = make_actions_request('create-new-draft-omop-concept-set-version',
                                        raise_validate_error=True,
                                        data=data, validate_first=validate_first)
        except ActionValidateError as err:
            print(dump(err.args[0]))
            return False

        # if valid response
        self.properties = make_objects_request(
            f'OMOPConceptSet/{versionId}', return_type='data',
            expect_single_item=True, retry_if_empty=True, retry_times=3)
        return True

    def create_from_csv(self, obj):
        self.container = CsetContainer(concept_set_name=obj['concept_set_name'])

        # does_container_exist(obj)

    # This is useful because they come as camel case from following locations: (i) xxxx, (ii) xxxx
    # field_names_camel_case = [
    #     'conceptSetName',
    #     'parentVersionCodesetId',
    #     'currentMaxVersion',
    #     provenance,
    #     limitations,
    #     annotation
    # ]
    # param_spelling_variations = [
    #
    # ]
    #


    # todo: are these fields actually used by a new version: domain_team, intention, authority
    def __init__(
        self, df: pd.DataFrame = None, concept_set_name: str = None, parent_version_codeset_id: int = None,
        current_max_version: float = None, provenance: str = "", limitations: str = "", annotation: str = "",
        domain_team: str = None, intention: str = "", authority: str = None, intended_research_project: str = None,
        on_behalf_of: str = None, codeset_id: int = None, omop_concepts: List[Dict] = None
    ):
        """
        @param created_by (UUID): This is also called `on_behalf_of` when we pass it to the API. This is also
        multiPassId.
        """
        if df:
            self.from_dataframe(df)
        else:
            self.concept_set_name = concept_set_name
            self.parent_version_codeset_id = parent_version_codeset_id
            self.current_max_version = current_max_version
            self.provenance = provenance
            self.limitations = limitations
            self.annotation = annotation
            self.domain_team = domain_team
            self.intention = intention
            self.authority = authority
            self.intended_research_project = intended_research_project
            self.on_behalf_of = on_behalf_of
            self.codeset_id = codeset_id
            self.omop_concepts = omop_concepts

    def from_dataframe(self, df):
        """From dataframe"""
        more_cset_cols = list(
            {'multipassId', 'current_max_version', 'domain_team', 'provenance', 'limitations', 'intention',
             'intended_research_project', 'authority'}.intersection(df.columns))
        concept_cols_required = ['concept_id', 'includeDescendants', 'isExcluded', 'includeMapped']
        concept_cols_optional = ['annotation']

        # TODO: From right about here, abstract this logic into new fun: cset_version_df_to_dict()
        new_version = {}
        first_row_all = df.to_dict(orient='records')[0]

        first_row = df[more_cset_cols].to_dict(orient='records')[0]
        cset_name = first_row_all['concept_set_name']
        new_version['concept_set_name'] = cset_name
        new_version['parent_version_codeset_id'] = int(first_row_all['parent_version_codeset_id'])

        for c in more_cset_cols:
            new_version[c] = first_row[c]

        new_version['on_behalf_of'] = new_version['multipassId']
        del new_version['multipassId']

        selectable_cols = concept_cols_required + [x for x in concept_cols_optional if x in list(df.columns)]
        try:
            new_version['omop_concepts'] = df[selectable_cols].to_dict(orient='records')
        except KeyError as e:
            raise EnclaveWranglerErr(str(e))
        for x in new_version['omop_concepts']:
                x['concept_id'] = int(x['concept_id'])
        print()


class CsetContainer:
    """Cset container"""

    # todo: add other properties
    def __init__(self, df=None, versions: List[CsetVersion] = None):
        if df:
            self.from_dataframe(df)
        else:
            self.versions = versions

    # TODO: this needs to iterate over something
    def from_dataframe(self, df):
        """From dataframe"""
        self.versions = CsetVersion(df)

"""
New way to do field mappings:
  After setting up the mapping between two rowtypes as below,
  you can get the field name you want. For instance, to copy fields
  from a concept records to an atlasjson records:
  
    ajrecs = convert_rows('concept', 'atlasjson', crecs)

  So far it only works with this one pair of rowtypes. As need arises 
  (like csv upload to make-new-omop-... api call), we'll add more mappings.
"""
FMAPS: List[Dict] = []
csv.register_dialect('trim', quotechar='"', skipinitialspace=True,
                     quoting=csv.QUOTE_NONE, lineterminator='\n', strict=True)


def add_mappings(csv_str: str):
    """Parse mappings from a CSV string and add to FMAPS."""
    reader = csv.DictReader(io.StringIO(csv_str), dialect='trim')
    maps: List[Dict] = list(reader)
    FMAPS.extend(maps)


PKEYS = {
    'concept': 'concept_id',
    'atlasjson': 'CONCEPT_ID',
    'OMOPConcept': 'conceptId',
    # version items, could be itemId or, preferably, codesetId + conceptId, but not sure how to handle that
    'OMOPConceptSet': 'codesetId',
    'code_sets': 'codeset_id',
    'OMOPConceptSetContainer': 'conceptSetId',
    'concept_set_container': 'concept_set_id',
}
def pkey(obj):
    """Get primary key for given object or  table."""
    return PKEYS.get(obj, None)

# OMOPConcept (concept): dataset <-> atlasjson
add_mappings(
    """concept,          atlasjson
       concept_id,       CONCEPT_ID
       concept_class_id, CONCEPT_CLASS_ID
       concept_code,     CONCEPT_CODE
       concept_name,     CONCEPT_NAME
       domain_id,        DOMAIN_ID
       invalid_reason,   INVALID_REASON
       standard_concept, STANDARD_CONCEPT
       vocabulary_id,    VOCABULARY_ID
       valid_start_date, VALID_START_DATE
       valid_end_date,   VALID_END_DATE""")

# OMOPConcept (concept): object <-> dataset
#  Unmapped fields:
#   OMOPConcept, concept
#   n/a,           standard_concept
#   b.a,           invalid_reason
add_mappings(
    """OMOPConcept, concept
    conceptId,         concept_id
    conceptClassId,    concept_class_id
    conceptCode,       concept_code
    conceptName,       concept_name
    domainId,          domain_id
    validEndDate,      valid_end_date
    validStartDate,    valid_start_date
    vocabularyId,      vocabulary_id""")

# OmopConceptSetVersionItem: object <-> dataset
add_mappings(
    """OmopConceptSetVersionItem, concept_set_version_item
    itemId,                       item_id
    codesetId,                    codeset_id
    conceptId,                    concept_id
    includeDescendants,           includeDescendants
    includeMapped,                includeMapped
    isExcluded,                   isExcluded
    createdBy,                    created_by
    createdAt,                    created_at""")

# OMOPConceptSet (Version): object <-> dataset
add_mappings(
    """OMOPConceptSet,            code_sets
       codesetId,                 codeset_id
       createdAt,                 created_at
       conceptSetVersionTitle,    concept_set_version_title
       isMostRecentVersion,       is_most_recent_version
       version,                   version
       createdBy,                 created_by
       conceptSetNameOMOP,        concept_set_name
       intention,                 intention
       updateMessage,             update_message
       atlasJsonResourceUrl,      atlas_json_resource_url
       provenance,                provenance
       sourceApplicationVersion,  source_application_version
       isDraft,                   is_draft
       sourceApplication,         source_application
       limitations,               limitations""")

# OMOPConceptSetContainer: object <-> dataset
#  Unmapped fields:
#   OMOPConcept, concept_set_members
#   n/a,                  assigned_informatician
#   n/a,                  assigned_sme
#   n/a,                  n3c_reviewer
add_mappings(
    """OMOPConceptSetContainer, concept_set_container
    conceptSetId,     concept_set_id
    alias,            alias
    archived,         archived
    conceptSetName,   concept_set_name
    createdAt,        created_at
    createdBy,        created_by
    intention,        intention
    project,          project_id
    stage,            stage
    status,           status""")


@cache
def get_field_mapping_lookup() -> Dict[str, Dict]:
    """
        mappings are a list of rows that look like:
            {'concept': 'concept_id', 'atlasjson': 'CONCEPT_ID'}

        rather than searching through the list for the mapping i want,
        it would be nice to have a quick lookup, to be able to do like:

        target_field_name = lookup[source_rowtype][source_field_name][target_rowtype]

        this function makes that object

        :returns like:
        {
            'atlasjson': {  # source model
                'CONCEPT_CLASS_ID': {  # source model field name
                    'concept':  # target model
                    'concept_class_id'  # target model field name
                }
            }
        }
        What it returns goes both ways. So it won't just give us atlasjson -> concept, but also concept -> atlasjson
    """
    # for nested defaultdict: https://stackoverflow.com/questions/19189274/nested-defaultdict-of-defaultdict
    d = defaultdict(lambda: defaultdict(dict))

    for m in FMAPS:
        rowtypes = list(m.keys())
        fields = list(m.values())
        # the mapping can go either direction
        d[rowtypes[0]][fields[0]][rowtypes[1]] = fields[1]
        d[rowtypes[1]][fields[1]][rowtypes[0]] = fields[0]
    return d


@cache
def get_field_names(rowtype: str):
    """Get the field names for a given rowtype"""
    return list(get_field_mapping_lookup()[rowtype].keys())


@cache
def field_name_mapping(source: str, target: str, field: str) -> str:
    """Get the field name mapping from source to target for a given field"""
    return get_field_mapping_lookup()[source][field][target]


def convert_rows(source: str, target: str, rows: List[Dict]) -> List[Dict]:
    """Convert rows from source to target"""
    out = []
    for row in rows:
        out.append(convert_row(source, target, row))
    return out


def convert_row(source: str, target: str, row: Dict, skip_missing_fields=True) -> Dict:
    """Convert row from source to target"""
    out = {}
    for field in get_field_names(target):
        try:
            out[field] = row[field_name_mapping(target, source, field)]
        except KeyError as err:
            if skip_missing_fields:
                pass
            else:
                raise err
    return out


if __name__ == '__main__':
    # mappings = get_field_mappings()
    # pdump(m)
    # t = field_name_mapping('concept', 'concept_id', 'atlasjson')
    # print(t)
    # t = field_name_mapping('concept', 'domain_id', 'atlasjson')
    # print(t)
    print()
