"""OAK routes"""
import os, warnings
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
from backend.db.queries import get_vocab_of_concepts, get_vocabs_of_concepts

router = APIRouter(
    # prefix="/oak",
    # tags=["oak", "ontology-access-kit],
    # dependencies=[Depends(get_token_header)],  # from FastAPI example
    responses={404: {"description": "Not found"}},
)

# logging.basicConfig(level=logging.INFO)
# logger = logging.getLogger(__name__)
# APIRouter.logger = logger
# oi_pkg.logger = logger

PROJECT_DIR = Path(os.path.dirname(__file__)).parent.parent
VOCABS_PATH = os.path.join(PROJECT_DIR, 'termhub-vocab')

vocab_paths = {
    'SNOMED': os.path.join(VOCABS_PATH, 'n3c-SNOMED.db'),
    'RxNorm': os.path.join(VOCABS_PATH, 'n3c-RxNorm.db'),
}

def get_oi(vocab):
    return get_adapter(vocab_paths[vocab])


def omop_id_to_curie(id: int, vocab: str):
    if vocab == 'RxNorm':
        return f'<https://athena.ohdsi.org/search-terms/terms/{id}>'
    if vocab == 'SNOMED':
        return f'SNOMED:{id}'
    return f'OMOP:{id}'



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
@router.get("/subgraph-oak/")
def subgraph_oak(id: List[int] = Query(...)):
    # def subgraph(cid: List[str] = Query(...), add_prefix=True):
    """ Get a subgraph / minimal subsumption tree between and including 2 nodes.
    https://github.com/INCATools/
    ontology-access-kit/blob/4f215f71d4f814e1bd910710f68030b2976d845b/src/oaklib/interfaces/obograph_interface.py#L315
    """
    cids_by_vocab = get_vocabs_of_concepts(id)
    if cids_by_vocab.get('RxNorm'):
        vocab = 'RxNorm' # dropping RxNorm Extension and ATC that appear in some med csets
    elif len(cids_by_vocab.keys()) == 1:
        vocab = cids_by_vocab.keys()[0]
    elif cids_by_vocab.get('SNOMED'):
        vocab = 'SNOMED'
        warnings.warn(f"Including SNOMED concepts. Can't handle the ones from [{', '.join(set(cids_by_vocab.keys()) - set(['SNOMED']))}]")
    else:
        raise RuntimeError(f"Don't know what to do with concept_ids from [{', '.join(cids_by_vocab.keys())}]")
    seeds = [omop_id_to_curie(_id, vocab) for _id in cids_by_vocab[vocab]]
    traversal = oi_pkg.TraversalConfiguration(up_distance=oi_pkg.Distance.TRANSITIVE,
                                              down_distance=oi_pkg.Distance.DIRECT)
    oi = get_oi(vocab)
    edges = oi.gap_fill_relationships(seed_curies=seeds, predicates=[IS_A])
    # print(next(edges))
    return list(edges)
    # g = OI.subgraph_from_traversal(['N3C:201826', 'N3C:201254'], predicates=[IS_A])
    sg = oi.subgraph_from_traversal(seeds, predicates=[IS_A, PART_OF], traversal=traversal).edges
    return sg
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
    q = """
      SELECT *
      FROM concept_relationship_plus
      WHERE concept_name_1 = (:term)
        AND relationship_id = 'Subsumes'
    """
    with get_db_connection() as con:
        timer('done')
        timer = get_timer('Postgres speed test')
        timer(f'  parents of {term}')
        print()
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

    oi = get_oi('RxNorm')




    sg = subgraph(
        [40128015,1748921,1748921,1748921,40059337,1738170,1738170,1738170,40059335,995126,1592433,1592434,1592435,1592436,1592437,1592438,1738170,1738171,1738202,1738203,1738204,1748921,1748953,1748954,1748955,1748956,1748957,1748959,1748960,1748982,1748984,1748985,1748986,1748987,1748988,1748989,2031629,2031630,2031631,2050589,2050590,19016698,19038784,19038785,19048071,19048073,19048075,19048077,19082373,19088562,19122186,19125242,21023720,21023721,21023722,21033493,21040051,21043414,21043415,21051386,21053213,21053214,21053215,21061185,21061186,21063034,21063035,21063036,21069578,21069606,21072939,21072940,21079385,21080806,21082601,21092413,21110299,21112108,21121798,21131573,21131574,21138148,21139717,21141522,21149567,21161276,35408398,35410429,35410525,35410716,35412557,35412773,35412885,35414412,35414451,35742186,35748013,35752148,35764671,35770020,35789094,35860451,35860452,35860453,35860454,35860455,35860456,35860457,35860458,35860779,35860780,35860781,35860782,35860783,35860784,35860785,35860786,35860787,35860788,35860789,35860836,35860837,35860838,35860839,35860840,36061896,36061897,36061898,36061899,36061900,36061901,36061902,36061903,36061904,36061905,36061906,36061907,36061908,36061909,36219735,36219736,36219737,36222583,36222584,36222585,36229804,36229805,36229806,36233142,36233143,36233144,36248168,36248169,36248898,36248899,36262103,36269549,36271562,36272735,36275334,36277107,36277450,36404012,36406313,36407130,36409400,36412245,36412246,36412247,36412248,36504619,36509777,36778999,36779000,36779001,36783255,36784561,36784562,36897515,36897543,36897682,36897763,36898056,36898068,40059335,40059337,40080334,40080336,40080337,40080338,40128015,40160001,40160002,40160004,40171778,40171779,40171780,40171781,40220769,40220792,40220793,40220794,40220795,40220796,40220797,40221116,40709680,40709681,40709688,40709689,40712269,40712270,40712271,40724589,40724590,40724591,40724592,40724593,40724594,40724595,40724596,40724597,40724598,40724599,40724600,40724601,40724602,40724604,40834350,40852101,40852102,40853055,40865477,40883372,40883373,40883374,40883375,40883376,40885252,40896672,40914288,40916124,40916125,40916126,40945664,40945665,40945666,40945667,40945668,40945669,40947545,40947546,40960083,40996625,40996626,41007936,41007937,41013502,41027628,41039028,41040935,41040936,41058809,41058810,41070325,41072178,41083974,41101768,41101769,41103646,41103647,41116314,41133091,41133092,41133093,41135083,41135084,41135085,41135086,41166314,41177701,41184181,41195800,41195801,41209226,41226850,41226851,41226852,41234056,41246494,41249680,41257682,41257683,41277370,41288745,41288746,41290665,41302143,41311816,41320140,41402640,41404281,41404313,41404323,41404332,41404340,41404350,41404433,41404462,42731574,42731594,42731595,42731648,42731691,42875915,42876172,42918908,42918909,42963128,42963129,42963130,43032545,43032546,43035797,43042972,43138732,43138758,43138759,43142737,43149644,43149674,43149675,43153842,43153881,43153882,43160866,43160867,43160868,43160869,43160870,43160871,43160894,43171780,43171800,43171801,43171802,43175881,43175926,43182762,43182790,43182791,43182792,43186772,43193748,43193749,43193750,43193751,43197819,43204708,43204732,43204733,43208695,43208697,43215610,43215611,43215612,43215643,43219711,43257505,43262883,43268384,43268385,43272621,43276253,43283430,43290082,43297865,43298018,43298279,43298296,43298357,43298482,43298529,43522495,43522777,43522783,43522786,43522791,43522795,43522809,43522840,43522868,43534798,43642381,43660518,43678527,43696348,43714174,43732231,43768138,43786180,43786181,43786182,43804159,43840342,43840343,43858446,44033885,44036307,44037034,44045833,44049837,44051010,44062430,44067904,44096044,44096910,44101047,44112432,44120603,44127029,44159847,44166954,44170968,44174454,44174865,44180502,44183594,44185672,44186126,45892214,45892556,45892557,45893034,46275632,46275633,46275634]
    )
    print(sg)
    return sg


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
