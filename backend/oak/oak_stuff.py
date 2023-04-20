import os
from pathlib import Path
from typing import Dict, List
from oaklib import get_adapter
from oaklib.datamodels.vocabulary import IS_A
from backend.utils import pdump, get_timer
from backend.db.utils import sql_query, get_db_connection

PROJECT_DIR = Path(os.path.dirname(__file__)).parent.parent
VOCABS_PATH = os.path.join(PROJECT_DIR, 'termhub-vocab')

def icdtest():
  """Test OAK
  Docs: https://incatools.github.io/ontology-access-kit/"""
  # oi: @Siggie: 'oak implementation' this is an OAK naming convention but you can rename
  icd10cm_path = os.path.join(VOCABS_PATH, 'icd10cm.db')
  oi = get_adapter(icd10cm_path)
  example_terms = ['ICD10CM:A00-A09']
  labels_example: List[tuple] = list \
    (oi.labels(example_terms))  # [('ICD10CM:A00-A09', 'Intestinal infectious diseases (A00-A09)')]
  # relationships: gets parents, but not children because they're not declared on the class itself
  relat_example: List[tuple] = list \
    (oi.relationships(example_terms))  # [('ICD10CM:A00-A09', 'rdfs:subClassOf', 'ICD10CM:A00-B99')]
  # incoming_relationship_map: gets children
  kids_example: Dict[str, List] = oi.incoming_relationship_map(example_terms[0])  # {'rdfs:subClassOf: [...]}
  print()  # set breakpoint here


def oak_test(): # from Chris Mungall
  # oi = get_adapter("/Users/cjm/repos/semantic-sql/local/snomed.db")
  snomed_path = os.path.join(VOCABS_PATH, 'n3c-SNOMED.db')
  oi = get_adapter(snomed_path)

  timer = get_timer('Oak speed test')
  curie = list(oi.basic_search("Atrial dilatation"))[1]
  timer('  basic search for term')
  print(f'{curie} ! {oi.label(curie)}')
  timer('  parents')
  for _s, _p, o in oi.relationships([curie], predicates=[IS_A]):
    print(f' * OUTGOING: {o} {oi.label(o)}')
  timer('  children')
  for s, _p, _o in oi.relationships(objects=[curie], predicates=[IS_A]):
    print(f' * INCOMING: {o} {oi.label(o)}')
  timer('done')


def snomed_test():
  snomed_path = os.path.join(VOCABS_PATH, 'n3c-SNOMED.db')
  oi = get_adapter(snomed_path)

  # ad = list(oi.basic_search('Atrial dilatation'))
  # pdump(list(oi.labels(list(oi.outgoing_relationship_map(ad[1]).items())[0][1])))

  timer = get_timer('Oak speed test')
  print()
  timer('  basic search for term')
  print()
  curie = list(oi.basic_search("Atrial dilatation"))[1]
  print(f'\n{curie} ! {oi.label(curie)}')
  # print(f'Definition: {oi.definition(curie)}')
  timer('  parents')
  print()
  for rel, fillers in oi.outgoing_relationship_map(curie).items():
    print(f'  {rel} ! {oi.label(rel)}')
    for filler in fillers:
      print(f'     * {filler} ! {oi.label(filler)}')
  print()
  timer('  children')
  print()
  for rel, fillers in oi.incoming_relationship_map(curie).items():
    print(f'  {rel} ! {oi.label(rel)}')
    for filler in fillers:
      print(f'     * {filler} ! {oi.label(filler)}')
  print()
  timer('done')

  print()
  # timer('  connect to db (query uses name so doesn\'t need term lookup)')
  timer = get_timer('connect to postgres')
  timer('connecting')
  with get_db_connection() as con:
    timer('done')
    timer = get_timer('Postgres speed test')
    timer('  parents of 4221281 ! Atrial dilatation subsumes')
    print()
    q = """
      SELECT *
      FROM concept_relationship_plus
      WHERE concept_name_2 = 'Atrial dilatation'
        AND relationship_id = 'Subsumes'
    """
    results = sql_query(con, q)
    for row in results:
      print(f"  * {row['relationship_id']} {row['concept_id_1']} ! {row['concept_name_1']}")
    print()
    timer('  children of 4221281 ! Atrial dilatation subsumes')
    print()
    q = """
      SELECT *
      FROM concept_relationship_plus
      WHERE concept_name_1 = 'Atrial dilatation'
        AND relationship_id = 'Subsumes'
    """
    results = sql_query(con, q)
    for row in results:
      print(f"  * {row['relationship_id']} {row['concept_id_2']} ! {row['concept_name_2']}")
    print()
  print()
  timer('done')


if __name__ == '__main__':
  oak_test()
  # icdtest()
  # snomed_test()
  # print('\n\n\nDOING IT A SECOND TIME\n\n\n')
  # snomed_test()
