from argparse import ArgumentParser
from enclave_wrangler.actions_api import make_actions_request
from enclave_wrangler.models import CsetVersion

# def cli():
#   """Command line interface for package.
#
#   Side Effects: Executes program."""
#   package_description = 'CLI for running Enclave API calls'
#   parser = ArgumentParser(description=package_description)
#
#   parser.add_argument(
#     '-d', '--data',
#     help="""Data for POST calls. Usually like: -d '{".
#         """)
#   parser.add_argument(
#     '-f', '--format',
#     choices=['palantir-three-file', 'moffit'],
#     default='palantir-three-file',
#     help='The format of the file(s) to be uploaded.\n'
#          '- palantir-three-file: Path to folder with 3 files that have specific columns that adhere to concept table data model. These '
#          'files must have the following names: i. `code_sets.csv`, ii. `concept_set_container_edited.csv`, iii. '
#          '`concept_set_version_item_rv_edited.csv`.\n'
#          '- moffit: Has columns concept_set_id, concept_set_name, concept_code, concept_name, code_system.')
#   # parser.add_argument(
#   #     '-c', '--use-cache',
#   #     action='store_true',
#   #     help='If present, will check the input file and look at the `enclave_codeset_id` column. If no empty values are'
#   #          ' present, this indicates that the `enclave_wrangler` has already been run and that the input file itself '
#   #          'can be used as cached data. The only thing that will happen is an update to the persistence layer, '
#   #          '(`data/cset.csv` as of 2022/03/18).'),
#   kwargs = parser.parse_args()
#   kwargs_dict: Dict = vars(kwargs)
#   upload_dataset(**kwargs_dict)


if __name__ == '__main__':
  data = {"parameters": {"conceptSet": "Siggie test"}}
  cset = CsetVersion()
  if cset.create_new_draft_minimal(
          conceptSet = 'Siggie test',
          intended_research_project = 'RP-4A9E27',
          on_behalf_of = '5c560c3e-8e55-485c-9a66-f96285f273a0',
          intention = 'testing',
          copyExpressionsFromBaseVersion = True,
          validate_first = True):
    print(cset.properties) # has a bunch of stuff now
  else:
    print("Failed")

  # cli()
