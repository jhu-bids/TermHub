import os
import sys
# import logging
from pathlib import Path
from typing import Dict, List
from oaklib import get_adapter, BasicOntologyInterface
from oaklib.datamodels.vocabulary import IS_A
from backend.utils import pdump, get_timer
from backend.db.utils import sql_query, get_db_connection
from backend.app import cache
import oaklib.interfaces.obograph_interface as OIpkg
from oaklib.datamodels.vocabulary import IS_A, PART_OF
from fastapi import APIRouter, Query

router = APIRouter(
    # prefix="/oak",
    # tags=["cset-crud"],
    # dependencies=[Depends(get_token_header)],  # from FastAPI example
    responses={404: {"description": "Not found"}},
)

PROJECT_DIR = Path(os.path.dirname(__file__)).parent.parent
VOCABS_PATH = os.path.join(PROJECT_DIR, 'termhub-vocab')

# logging.basicConfig(level=logging.INFO)
# logger = logging.getLogger(__name__)
# APIRouter.logger = logger

snomed_path = os.path.join(VOCABS_PATH, 'n3c-SNOMED.db')
OI = get_adapter(snomed_path)
# OIpkg.logger = logger


# @cache
@router.get("/subgraph/")
def subgraph(omop_ids: List[str] = Query(...), add_prefix = True):
  """
  from https://github.com/INCATools/ontology-access-kit/blob/4f215f71d4f814e1bd910710f68030b2976d845b/src/oaklib/interfaces/obograph_interface.py#L315
  """
  seeds = ['N3C:' + id for id in omop_ids]
  # from oaklib.interfaces.obograph_interface import TraversalConfiguration, Distance
  # use an adapter to talk to an endpoint (here, sqlite)
  # adapter = get_adapter("tests/input/go-nucleus.db")
  # get a subgraph centered around these nodes
  # seeds = ["GO:0005634", "GO:0005773"]  # nucleus, vacuole
  # walk up the graph to get ancestors, and also get direct children
  traversal = OIpkg.TraversalConfiguration(up_distance=OIpkg.Distance.TRANSITIVE, down_distance=OIpkg.Distance.DIRECT)
  graph = OI.subgraph_from_traversal(seeds, predicates=[IS_A, PART_OF], traversal=traversal)
  return graph.edges
  len(graph.nodes)
  len(graph.edges)


def oak_test(term, predicates): # from Chris Mungall
  # oi = get_adapter("/Users/cjm/repos/semantic-sql/local/snomed.db")

  timer = get_timer('Oak speed test')
  timer('basic search for term')
  curies = get_curie(term, list_ok=True)
  for curie in curies:
    timer(f"\n   {curie} predicates={','.join(predicates)}")
    label = OI.label(curie)
    timer(f'     {label} parents')
    for _s, _p, o in OI.relationships([curie], predicates=predicates):
      print(f' * OUTGOING: {o} {OI.label(o)}')
    timer(f'     {label} children')
    for s, _p, _o in OI.relationships(objects=[curie], predicates=predicates):
      print(f' * INCOMING: {s} {OI.label(s)}')
  timer('done')


def snomed_test(term, predicates):
  # ad = list(OI.basic_search('Atrial dilatation'))
  # pdump(list(OI.labels(list(OI.outgoing_relationship_map(ad[1]).items())[0][1])))

  timer = get_timer('Oak speed test')
  print()
  timer('  basic search for term')
  curies = get_curie(term, list_ok=True)
  # print(f'Definition: {OI.definition(curie)}')
  for curie in curies:
    timer(f'   {curie} predicates={",".join(predicates)}')
    label = OI.label(curie)
    timer(f'     {label} parents')
    print()
    for rel, fillers in OI.outgoing_relationship_map(curie, predicates=predicates).items():
      print(f'  {rel} ! {OI.label(rel)}')
      for filler in fillers:
        print(f'        * {filler} ! {OI.label(filler)}')
    print()
    timer(f'     {label} children')
    print()
    # incoming doesn't accept predicates
    for rel, fillers in OI.incoming_relationship_map(curie).items():
      print(f'  {rel} ! {OI.label(rel)}')
      for filler in fillers:
        print(f'        * {filler} ! {OI.label(filler)}')
    print()
  timer('done')

  print()
  # timer('  connect to db (query uses name so doesn\'t need term lookup)')
  timer = get_timer('connect to postgres')
  timer('connecting')
  with get_db_connection() as con:
    timer('done')
    timer = get_timer('Postgres speed test')
    timer(f'  parents of {term}')
    print()
    q = """
      SELECT *
      FROM concept_relationship_plus
      WHERE concept_name_1 = (:term)
        AND relationship_id = 'Subsumes'
    """
    results = sql_query(con, q, {'term':term})
    for row in results:
      print(f"  * {row['relationship_id']} {row['concept_id_1']} ! {row['concept_name_1']}")
    print()
    timer(f'  children of {term}')
    print()
    q = f"""
      SELECT *
      FROM concept_relationship_plus
      WHERE concept_name_1 = (:term)
        AND relationship_id = 'Subsumes'
    """
    results = sql_query(con, q, {'term':term})
    for row in results:
      print(f"  * {row['relationship_id']} {row['concept_id_2']} ! {row['concept_name_2']}")
    print()
  print()
  timer('done')


def show_info(BasicOntologyInterface, term: str):
  term_id = get_curie(term)
  # from https://incatools.github.io/ontology-access-kit/intro/tutorial02.html#extending-the-example
  print(f"ID: {term_id}")
  print(f"Name: {OI.label(term_id)}")
  print(f"Definition: {OI.definition(term_id)}")
  for rel, parent in OI.outgoing_relationships(term_id):
    print(f'  {rel} ({OI.label(rel)}) {parent} ({OI.label(parent)})')


@cache
def get_curie(label, list_ok=False):
  curies = list(OI.basic_search(label))
  if list_ok:
    return curies
  return curies[0]



SEARCH_TERM = 'Renal failure'

if __name__ == '__main__':
  terms = ['Renal failure', 'Cyst of kidney']
  curies = []
  for term in terms:
    curies.extend(get_curie(term, list_ok=True))
  subgraph(curies)
  sys.exit()
  show_info(SEARCH_TERM)
  sys.exit()
  snomed_test(term=SEARCH_TERM, predicates=[IS_A])
  oak_test(term=SEARCH_TERM, predicates=[IS_A])
  print('\n\n\nDOING IT A SECOND TIME\n\n\n')
  oak_test(term=SEARCH_TERM, predicates=[IS_A])
  # icdtest()
  # snomed_test()
