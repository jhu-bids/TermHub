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

from enclave_wrangler.utils import EnclaveWranglerErr

class ObjWithMetadata:
    def __init__():
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

    # This is useful because they come as camel case from following locations: (i) xxxx, (ii) xxxx
    field_names_camel_case = [
        'conceptSetName',
        'parentVersionCodesetId',
        'currentMaxVersion',
        provenance,
        limitations,
        annotation
    ]
    param_spelling_variations = [

    ]



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
