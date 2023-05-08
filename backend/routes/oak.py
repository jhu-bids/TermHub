"""OAK routes"""
import os
from functools import cache
from pathlib import Path
from typing import List
from oaklib import BasicOntologyInterface, get_adapter
import oaklib.interfaces.obograph_interface as oi_pkg
import oaklib.interfaces.subsetter_interface as ss
from oaklib.datamodels.vocabulary import IS_A, PART_OF
from fastapi import APIRouter, Query
from backend.utils import get_timer
from backend.db.utils import sql_query, get_db_connection
from backend.db.queries import get_vocab_of_concepts

router = APIRouter(
    # prefix="/oak",
    # tags=["oak", "ontology-access-kit],
    # dependencies=[Depends(get_token_header)],  # from FastAPI example
    responses={404: {"description": "Not found"}},
)

PROJECT_DIR = Path(os.path.dirname(__file__)).parent.parent
VOCABS_PATH = os.path.join(PROJECT_DIR, 'termhub-vocab')

# logging.basicConfig(level=logging.INFO)
# logger = logging.getLogger(__name__)
# APIRouter.logger = logger
# oi_pkg.logger = logger

snomed_path = os.path.join(VOCABS_PATH, 'n3c-SNOMED.db')
rxnorm_path = os.path.join(VOCABS_PATH, 'n3c-RxNorm.db')

OIs = {
    'SNOMED': get_adapter(snomed_path),
    'RxNorm': get_adapter(rxnorm_path),
}

def get_oi(vocab):
    return OIs[vocab]


@cache
def get_curie(label, list_ok=False):
    """Get term's CURIE by its label"""
    # noinspection PyUnresolvedReferences doesnt_expect_basic_search_but_I_think_its_wrong
    curies = list(OI.basic_search(label))
    if list_ok:
        return curies
    return curies[0]


# Routes ---------------------------------------------------------------------------------------------------------------
# @cache
@router.get("/subgraph/")
def subgraph(id: List[int] = Query(...)):
    # def subgraph(cid: List[str] = Query(...), add_prefix=True):
    """ Get a subgraph / minimal subsumption tree between and including 2 nodes.
    https://github.com/INCATools/
    ontology-access-kit/blob/4f215f71d4f814e1bd910710f68030b2976d845b/src/oaklib/interfaces/obograph_interface.py#L315
    """
    vocabulary_id = get_vocab_of_concepts(id)
    seeds = ['N3C:' + str(_id) for _id in id]
    traversal = oi_pkg.TraversalConfiguration(up_distance=oi_pkg.Distance.TRANSITIVE,
                                              down_distance=oi_pkg.Distance.DIRECT)
    # edges = OI.gap_fill_relationships(seed_curies=seeds, predicates=[IS_A])
    # print(next(edges))
    # return edges
    # g = OI.subgraph_from_traversal(['N3C:201826', 'N3C:201254'], predicates=[IS_A])
    return get_oi(vocabulary_id).subgraph_from_traversal(seeds, predicates=[IS_A, PART_OF], traversal=traversal).edges
    # edges = subsetter.gap_fill_relationships(seed_curies=seeds, predicates=[IS_A])
    return graph.edges


# Utility functions, ad hoc testing, and analysis ----------------------------------------------------------------------
def oak_test(term, predicates):  # from Chris Mungall
    """Testing if OAK works as expected"""
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
    """Testing if SNOMED works as expected"""
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
        # noinspection PyArgumentList doesnt_expect_predicate_but_I_think_its_wrong
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
        results = sql_query(con, q, {'term': term})
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
        results = sql_query(con, q, {'term': term})
        for row in results:
            print(f"  * {row['relationship_id']} {row['concept_id_2']} ! {row['concept_name_2']}")
        print()
    print()
    timer('done')


# def show_info(term: str, oi: BasicOntologyInterface = OI):
#     """Show term's info"""
#     term_id = get_curie(term)
#     # from https://incatools.github.io/ontology-access-kit/intro/tutorial02.html#extending-the-example
#     print(f"ID: {term_id}")
#     print(f"Name: {oi.label(term_id)}")
#     print(f"Definition: {oi.definition(term_id)}")
#     for rel, parent in oi.outgoing_relationships(term_id):
#         print(f'  {rel} ({oi.label(rel)}) {parent} ({oi.label(parent)})')


def ad_hoc_test_1():
    """Misc test"""
    search_term = 'Renal failure'
    terms = ['Renal failure', 'Cyst of kidney']
    curies = []
    for term in terms:
        curies.extend(get_curie(term, list_ok=True))
    subgraph(curies)
    # sys.exit()
    show_info(search_term)
    # sys.exit()
    snomed_test(term=search_term, predicates=[IS_A])
    oak_test(term=search_term, predicates=[IS_A])
    print('\n\n\nDOING IT A SECOND TIME\n\n\n')
    oak_test(term=search_term, predicates=[IS_A])
    # icdtest()
    # snomed_test()


if __name__ == '__main__':
    ad_hoc_test_1()
