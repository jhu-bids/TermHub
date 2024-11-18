"""Tests

How to run:
    python -m unittest discover

TODO: _save_output() broken now. Need to match updated concept_graph() outputs:
 Tuple[DiGraph, Set[int], Set[int], Dict[str, Set[int]], Set[int]], from:
 return sg, concept_ids, hidden_by_voc, nonstandard_concepts_hidden

TODO: for big JSON, save without indent
todo: Siggie already wrote some code that gets the commit hash, because we show that in TermHub's UI. i can probably
 re-use that here for DRYness.
"""
import asyncio
import csv
import json
import os
import subprocess
import sys
import unittest
from io import StringIO
from pathlib import Path
from typing import Dict, List, Set, Tuple

from networkx import DiGraph

THIS_DIR = Path(os.path.dirname(__file__))
PROJECT_ROOT = THIS_DIR.parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# todo: https://github.com/jhu-bids/TermHub/issues/784 . Failing as of https://github.com/jhu-bids/TermHub/pull/883 ,
#  but examining the diff, it's not obvious why. Pickle didn't change. Loading of pickle essentially unchanged. 
import builtins
builtins.DONT_LOAD_GRAPH = True
from backend.routes.graph import concept_graph
# noinspection PyUnresolvedReferences rel_graph_exists_just_not_if_name_eq_main
REL_GRAPH = DiGraph()


THIS_STATIC_DIR = THIS_DIR / 'static'
STATIC_DIR_concept_graph = THIS_STATIC_DIR / 'concept_graph'
# remove last two codeset_ids from many-small because not like the others (include rxnorm)
# many small,many-small,"1000002363, 1000002657, 1000007602, 1000013397, 1000010688, 1000015307, 1000031299",45

# cardiomyopathies, expect cid 619077 to be missing
TEST_CASES_FAST = """
testType,testName,codeset_ids,timeoutSeconds,hide_vocabs
small,cardiomyopathies,35275316,45,Nebraska Lexicon
single 2000,autoimmune 1,101398605,180
many small,many-small,"1000002363, 1000002657, 1000007602, 1000013397, 1000010688",45,Nebraska Lexicon
mixed 6000 to 21000,Sulfonylureas,"417730759, 423850600, 966671711, 577774492",120
mixed 30 to 3000,autoimmune 2,"101398605, 947369784, 287650725, 283328624, 115052941",240
single 30000,antibiotics 1,909552172,180
single small,single-small,1000002363,30
single small,single-small-second-time,1000002363,30
"""
TEST_CASES_HOLD = """
testType,testName,codeset_ids,timeoutSeconds
"""
TEST_CASES = TEST_CASES_FAST
EXTRA_CONCEPT_IDS = []
HIDE_VOCABS = ['RxNorm Extension']


class AsyncTests(unittest.TestCase):
    def run(self, result=None):
        """Override normal test run() func for async."""
        loop = asyncio.get_event_loop()
        if loop.is_closed():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        loop.run_until_complete(self._async_run(result))

    async def _async_run(self, result):
        """Run async tests."""
        test_method = getattr(self, self._testMethodName)
        if asyncio.iscoroutinefunction(test_method):
            await test_method()
        else:
            super().run(result)


class TestGraph(AsyncTests):
    """Tests for graph.py"""
    test_cases: List[Dict] = []

    @staticmethod
    def _get_test_cases() -> List[Dict]:
        """Set up"""
        csv_file = StringIO(TEST_CASES_FAST.strip())
        cases: List[Dict] = list(csv.DictReader(csv_file, delimiter=',', quotechar='"'))
        for case in cases:
            for k, v in case.items():
                if k in ['codeset_ids', 'hide_vocabs']:
                    case[k] = v.split(',') if v else []
        return cases

    @staticmethod
    def _save_output(
        test_name: str, sg: DiGraph, nodes_in_graph: Set[int], preferred_concept_ids: Set[int],
        orphans_not_in_graph: Set[int], hidden: Dict[str, Set[int]], minify_threshold=1000, base_case=False
    ):
        """Save outputs
        :param minify_threshold: If the number of records in the JSON is greater than this, will save minified, else
        will use indent of 4.
        :param base_case: If True, this will be considered the new base case for testing against in the future, and
        outputs will be saved not to a hash subfolder, but to STATIC_DIR_concept_graph. For reference, the hash
         will be saved in _base_case_hash.txt."""
        # Find commit hash & determine how to use it
        hash_proc = subprocess.run(['git', 'rev-parse', 'HEAD'], stdout=subprocess.PIPE, text=True, check=True)
        git_hash = hash_proc.stdout.strip()[0:7]
        subdir = STATIC_DIR_concept_graph
        subdir = subdir / f'{git_hash}' if not base_case else subdir
        subdir.mkdir(parents=True, exist_ok=True)
        path = subdir / f'{test_name}.json'
        if base_case:
            with open(subdir / '_base_case_hash.txt', 'w') as f:
                f.write(git_hash)
        # Format & save output
        normalized_hidden = {k: sorted(list(v)) for k, v in hidden.items()}
        results = {
            'sg.edges': sorted(list(sg.edges)),
            'nodes_in_graph': sorted(list(nodes_in_graph)),
            'preferred_concept_ids': sorted(list(preferred_concept_ids)),
            'orphans_not_in_graph': sorted(list(orphans_not_in_graph)),
            'hidden': normalized_hidden,
        }
        n_records = sum([len(v) for k, v in results.items()])
        indent = None if n_records > minify_threshold else 4
        with open(path, 'w') as f:
            f.write(json.dumps(results, indent=indent))

    # todo: this is not currently used. It needs modification after changes to concept_graph()
    async def _create_inputs__concept_graph__needs_repair(self):
        """Creat inputs for concept_graph()"""
        for test_type, test_name, codeset_ids, timeout_secs, hide_vocabs in [x.values() for x in self._get_test_cases()]:
            # Creat output files
            sg, nodes_in_graph, preferred_concept_ids, orphans_not_in_graph, hidden = \
                await concept_graph(codeset_ids, EXTRA_CONCEPT_IDS, HIDE_VOCABS)
            self._save_output(
                test_name, sg, nodes_in_graph, preferred_concept_ids, orphans_not_in_graph, hidden, base_case=True)

    # TODO: AttributeError: 'DiGraph' object has no attribute 'wholegraph' (see below)
    # todo: will fail on testName 'cardiomyopathies' because hasn't been saved to JSON yet, so it's currently skipped
    #  via only_fast_cases
    @unittest.skip("https://github.com/jhu-bids/TermHub/issues/811")
    async def test_concept_graph(self, only_fast_cases=True, save_output=True):
        """Test concept_graph()"""
        # Get results
        expected_actual_by_test: Dict[str, Tuple[Dict, Dict]] = {}
        for test_type, test_name, codeset_ids, timeout_secs, hide_vocabs in [x.values() for x in self._get_test_cases()]:
            # Do just 1 fast test case, or all test cases?
            if only_fast_cases and test_name not in [ 'single-small', 'many-small']:
                continue
            # Expected
            input_path = STATIC_DIR_concept_graph / f'{test_name}.json'
            expected_raw = json.load(open(input_path, 'r'))
            expected = {}  # convert JSON serialization back to sets
            for k, v in expected_raw.items():
                if k == 'sg.edges':
                    expected[k] = {tuple(x) for x in v}
                elif k == 'hidden':
                    expected[k] = {k2: set(v2) for k2, v2 in v.items()}
                else:
                    expected[k] = set(v)
            # Actual
            nodes_in_graph, preferred_concept_ids, orphans_not_in_graph, hidden = \
                await concept_graph(codeset_ids, EXTRA_CONCEPT_IDS, HIDE_VOCABS)
            # TODO: AttributeError: 'DiGraph' object has no attribute 'wholegraph'
            sg = REL_GRAPH.wholegraph(nodes_in_graph)
            actual = {
                'sg.edges': set(sg.edges),
                'nodes_in_graph': sg.nodes,
                'preferred_concept_ids': preferred_concept_ids,
                'orphans_not_in_graph': orphans_not_in_graph,
                'hidden': hidden,
            }
            # Store results to test at end
            expected_actual_by_test[test_name] = (expected, actual)
            # Save output
            if save_output:
                self._save_output(test_name, sg, nodes_in_graph, preferred_concept_ids, orphans_not_in_graph, hidden)

        # Run tests
        # todo: consider looking at diffs between all files and error at end, rather than on first failure
        for test_name, (expected, actual) in expected_actual_by_test.items():
            for k, v in actual.items():
                self.assertEqual(v, expected[k], msg=f'Results differ for {k} for test {test_name}')

    # todo: docstring: write how this differs from test_concept_graph()
    # noinspection PyUnboundLocalVariable removeNoinspectWhenMoreTestsAndMoveAssertsIntoLoop
    @unittest.skip("https://github.com/jhu-bids/TermHub/issues/811")
    async def test_concept_graph2(self):
        """Test concept_graph()"""
        # Get results
        for test_type, test_name, codeset_ids, timeout_secs, hide_vocabs in [x.values() for x in self._get_test_cases()]:
            if test_name not in ['cardiomyopathies', 'single-small', 'many-small']:  # TODO: do we want 3 cases or just cardiomyopathies?
                continue
            hide_vocabs = hide_vocabs or []
            sg: DiGraph
            hidden_by_voc: Dict[str, Set[int]]
            nonstandard_concepts_hidden: Set[int]
            sg, concept_ids, hidden_by_voc, nonstandard_concepts_hidden = await concept_graph(
                codeset_ids, hide_vocabs=hide_vocabs, hide_nonstandard_concepts=True, verbose=False)
                # self.assertEqual(...)
            if test_name == 'single-small':  # TODO: make assertions. although these are actually passing. why?
                self.assertEquals(len(sg.nodes), 000)
                self.assertEquals(len(sg.edges), 000)
                self.assertEquals(len(nonstandard_concepts_hidden), 000)
                self.assertEquals(len(hidden_by_voc[hide_vocabs[0]]), 000)
            elif test_name == 'many-small':
                self.assertEquals(len(sg.nodes), 14)  # TODO: assertion failing. update
                self.assertEquals(len(sg.edges), 24)
                self.assertEquals(len(nonstandard_concepts_hidden), 19)
                self.assertEquals(len(hidden_by_voc[hide_vocabs[0]]), 92)

    # todo: Upgrade for multiple scenarios & fix in GH action: https://github.com/jhu-bids/TermHub/issues/784
    @unittest.skip("Not using tested function anymore.")
    async def test_get_missing_in_between_nodes(self, verbose=False):
        """Could change this to test for current behavior of getting all descendants"""
        """Test get_missing_in_between_nodes()"""
        # - Test: Gap filling
        #   Source: depth first of https://app.diagrams.net/#G1mIthDUn4T1y1G3BdupdYKPkZVyQZ5XYR
        # test code for the above:
        # subgraph edges (from definitions and expansions)
        # (2, 1), (2, 8), (4, 3), (4, 10), (10, 9), (10, 12), (11, 10), (11, 13), (15, 14), (15, 18), (20, 16), (20, 19),
        # outside_scope_edges
        # ('root', '2p1'), ('2p1', 2), ('root', '2p2'), ('2p2', 2), ('root', 'cloud'), ('cloud', 8), ('cloud', 6), (6, 5),
        # (6, 11), (6, 17), ('cloud', 15), ('cloud', 20),
        # missing in between edges
        # (8, 7), (7, 5), (5, 4), (18, 17), (17, 16),
        whole_graph_edges = [   # now, more or less, in diagram number order
            (2, 1),
            ('root', '2p1'), ('2p1', 2), ('root', '2p2'), ('2p2', 2), ('root', 'cloud'),
            (4, 3),
            (5, 4),
            (7, 5),
            (8, 7),
            ('cloud', 8),
            (2, 8),
            (6, 5),
            ('cloud', 6),
            (10, 9),
            (4, 10),
            (10, 12),
            (11, 10),
            (6, 11),
            (11, 13),
            (15, 14),
            ('cloud', 15),
            (16, 21),
            (17, 16),
            (6, 17),
            (18, 17),
            (15, 18),
            (20, 16),
            ('cloud', 20),
            (22, 23),
            (19, 22),
            (20, 19),
        ]
        # noinspection PyPep8Naming
        G = DiGraph(whole_graph_edges)

        graph_nodes = set(list(range(1, 23)))
        # graph_nodes.update(['root', '2p1', '2p2', 'cloud'])
        subgraph_nodes =  graph_nodes - {7, 5, 6, 17}
        """ comment out because get_missing_in_between_nodes no longer exists
        expected_missing_in_between_nodes = {5, 7, 17}

        missing_in_between_nodes = get_missing_in_between_nodes(G, subgraph_nodes)

        self.assertEquals(missing_in_between_nodes, expected_missing_in_between_nodes)
        if verbose:
            print(f"test_get_missing_in_between_nodes(): passed with case: {missing_in_between_nodes}")
        """

    # TODO: test is failing. fix
    #  - The cause of the err is that subgraph() is a different function now. it used to call connected_subgraph_from_nodes(), which no longer exists.
    #    Is this test still valid? Is there any func that takes a list of concept IDs and returns their parentage tuples?
    @unittest.skip("https://github.com/jhu-bids/TermHub/issues/807")
    def test_subgraph(self):
        """Tests subgraph()"""
        from backend.routes.graph import wholegraph  # a little slow, and only needed here
        # Basic unit test for a simple connected graph without a complex hierarchy
        edges1 = wholegraph([1738170, 1738171, 1738202, 1738203])
        """
        ┌────────────┬──────────────────────┬───────────┬───────────────┬────────────────────┬────┬──────────────┬─────┬────────────┬───────────────┬───────────┬─────────────────────┐
        │ concept_id │ concept_name         │ domain_id │ vocabulary_id │  concept_class_id  │ sc │ concept_code │ inv │ domain_cnt │    domain     │ total_cnt │ distinct_person_cnt │
        ├────────────┼──────────────────────┼───────────┼───────────────┼────────────────────┼────┼──────────────┼─────┼────────────┼───────────────┼───────────┼─────────────────────┤
        │    1738170 │ lopinavir            │ Drug      │ RxNorm        │ Ingredient         │ S  │ 195088       │ ∅   │          1 │ drug_exposure │      2188 │ 142                 │
        │    1738171 │ lopinavir 133 MG     │ Drug      │ RxNorm        │ Clinical Drug Comp │ S  │ 331536       │ ∅   │          0 │               │         0 │ 0                   │
        │    1738202 │ lopinavir 80 MG / ML │ Drug      │ RxNorm        │ Clinical Drug Comp │ S  │ 331538       │ ∅   │          0 │               │         0 │ 0                   │
        │    1738203 │ lopinavir 200 MG     │ Drug      │ RxNorm        │ Clinical Drug Comp │ S  │ 597727       │ ∅   │          0 │               │         0 │ 0                   │
        └────────────┴──────────────────────┴───────────┴───────────────┴────────────────────┴────┴──────────────┴─────┴────────────┴───────────────┴───────────┴─────────────────────┘
        prefer concepts that do have counts
        """
        self.assertEqual(edges1, [ ( "1738170", "1738171" ), ( "1738170", "1738202" ), ( "1738170", "1738203" ) ])

        """ x
        select * from concept_relationship_plus
        where concept_id_1 in (1738170, 1738171, 1738202, 1738203)
          and concept_id_2 in (1738170, 1738171, 1738202, 1738203)
          and concept_id_1 != concept_id_2
        order by 5;

        ┌─────────────────┬──────────────┬────────────────────┬──────────────┬─────────────────┬─────────────────┬──────────────┬────────────────────┐
        │ vocabulary_id_1 │ concept_id_1 │   concept_name_1   │ concept_code │ relationship_id │ vocabulary_id_2 │ concept_id_2 │   concept_name_2   │
        ├─────────────────┼──────────────┼────────────────────┼──────────────┼─────────────────┼─────────────────┼──────────────┼────────────────────┤
        │ RxNorm          │      1738171 │ lopinavir 133 MG   │ 331536       │ RxNorm has ing  │ RxNorm          │      1738170 │ lopinavir          │
        │ RxNorm          │      1738202 │ lopinavir 80 MG/ML │ 331538       │ RxNorm has ing  │ RxNorm          │      1738170 │ lopinavir          │
        │ RxNorm          │      1738203 │ lopinavir 200 MG   │ 597727       │ RxNorm has ing  │ RxNorm          │      1738170 │ lopinavir          │
        │ RxNorm          │      1738170 │ lopinavir          │ 195088       │ RxNorm ing of   │ RxNorm          │      1738202 │ lopinavir 80 MG/ML │
        │ RxNorm          │      1738170 │ lopinavir          │ 195088       │ RxNorm ing of   │ RxNorm          │      1738171 │ lopinavir 133 MG   │
        │ RxNorm          │      1738170 │ lopinavir          │ 195088       │ RxNorm ing of   │ RxNorm          │      1738203 │ lopinavir 200 MG   │
        └─────────────────┴──────────────┴────────────────────┴──────────────┴─────────────────┴─────────────────┴──────────────┴────────────────────┘
        relationship between sources and targets:
        ┌─────────────────┬────────────────────────┬─────────────────┬──────────────────┬─────────────────────────┬─────────────────────────┐
        │ relationship_id │   relationship_name    │ is_hierarchical │ defines_ancestry │ reverse_relationship_id │ relationship_concept_id │
        ├─────────────────┼────────────────────────┼─────────────────┼──────────────────┼─────────────────────────┼─────────────────────────┤
        │ RxNorm ing of   │ Ingredient of (RxNorm) │               1 │                1 │ RxNorm has ing          │                44818817 │
        └─────────────────┴────────────────────────┴─────────────────┴──────────────────┴─────────────────────────┴─────────────────────────┘
        (code: select * from concept_relationship_plus where concept_id_1 = 1738170 and concept_id_2 = 1738171;
               select * from relationship where relationship_id = 'RxNorm ing of';)
        """

        #Test for a concept set that fills in the gaps (i.e. between child and grandparent)
        edges2 = wholegraph([1738170, 19122186])
        self.assertEqual(edges2, [ ( "1738170", "1738203" ), ( "1738203", "19122186" ) ])
        """
        ┌────────────┬────────────────────────────────────────────────┬───────────┬───────────────┬────────────────────┬──────────────────┬──────────────┬────────────────┬────────────┬───────────────┬───────────┬─────────────────────┐
        │ concept_id │                  concept_name                  │ domain_id │ vocabulary_id │  concept_class_id  │ standard_concept │ concept_code │ invalid_reason │ domain_cnt │    domain     │ total_cnt │ distinct_person_cnt │
        ├────────────┼────────────────────────────────────────────────┼───────────┼───────────────┼────────────────────┼──────────────────┼──────────────┼────────────────┼────────────┼───────────────┼───────────┼─────────────────────┤
        │    1738170 │ lopinavir                                      │ Drug      │ RxNorm        │ Ingredient         │ S                │ 195088       │ ∅              │          1 │ drug_exposure │      2188 │ 142                 │
        │    1738203 │ lopinavir 200 MG                               │ Drug      │ RxNorm        │ Clinical Drug Comp │ S                │ 597727       │ ∅              │          0 │               │         0 │ 0                   │
        │   19122186 │ lopinavir 200 MG / ritonavir 50 MG Oral Tablet │ Drug      │ RxNorm        │ Clinical Drug      │ S                │ 597730       │ ∅              │          1 │ drug_exposure │      5789 │ 833                 │
        └────────────┴────────────────────────────────────────────────┴───────────┴───────────────┴────────────────────┴──────────────────┴──────────────┴────────────────┴────────────┴───────────────┴───────────┴─────────────────────┘

        No relationship appears for concept relationship table.
        """

        #Test for a more complex hierarchial relationship
        edges3 = wholegraph([321588, 4027255, 316139, 43530856,
                             45766164,
                             4024552,
                             # missing node 4027255,
                             43530961])
        """
        ┌────────────┬──────────────────────────────────────────────────┬───────────┬───────────────┬──────────────────┬──────────────────┬──────────────┬────────────────┬────────────┬────────────────────────────────────┬───────────┬─────────────────────┐
        │ concept_id │                   concept_name                   │ domain_id │ vocabulary_id │ concept_class_id │ standard_concept │ concept_code │ invalid_reason │ domain_cnt │               domain               │ total_cnt │ distinct_person_cnt │
        ├────────────┼──────────────────────────────────────────────────┼───────────┼───────────────┼──────────────────┼──────────────────┼──────────────┼────────────────┼────────────┼────────────────────────────────────┼───────────┼─────────────────────┤
        │     321588 │ Heart disease                                    │ Condition │ SNOMED        │ Clinical Finding │ S                │ 56265001     │ ∅              │          1 │ condition_occurrence               │   1067160 │ 290357              │
        │     316139 │ Heart failure                                    │ Condition │ SNOMED        │ Clinical Finding │ S                │ 84114007     │ ∅              │          2 │ drug_exposure,condition_occurrence │   4105468 │ 20,613310           │
        │   43530856 │ High risk of heart failure, stage B              │ Condition │ SNOMED        │ Clinical Finding │ S                │ 609389009    │ ∅              │          1 │ condition_occurrence               │        20 │ 20                  │
        │   45766164 │ Heart failure with reduced ejection fraction     │ Condition │ SNOMED        │ Clinical Finding │ S                │ 703272007    │ ∅              │          1 │ condition_occurrence               │     10913 │ 3386                │
        │    4024552 │ Disorder of cardiac function                     │ Condition │ SNOMED        │ Clinical Finding │ S                │ 105981003    │ ∅              │          1 │ condition_occurrence               │      1192 │ 421                 │
        │    4027255 │ Structural disorder of heart                     │ Condition │ SNOMED        │ Clinical Finding │ S                │ 128599005    │ ∅              │          1 │ condition_occurrence               │       613 │ 231                 │
        │   43530961 │ Induced termination of pregnancy complicated by …│ Condition │ SNOMED        │ Clinical Finding │ S                │ 609507007    │ ∅              │          1 │ condition_occurrence               │        20 │ 20                  │
        │            │…cardiac failure                                  │           │               │                  │                  │              │                │            │                                    │           │                     │
        └────────────┴──────────────────────────────────────────────────┴───────────┴───────────────┴──────────────────┴──────────────────┴──────────────┴────────────────┴────────────┴────────────────────────────────────┴───────────┴─────────────────────┘

        "vocabulary_id_1"|"concept_id_1"|"concept_name_1"                                               |"concept_code"|"relationship_id"|"vocabulary_id_2"|"concept_id_2"|"concept_name_2"
        SNOMED           |4024552       |Disorder of cardiac function                                   |105981003     |Is a             |SNOMED           |321588        |Heart disease
        SNOMED           |4027255       |Structural disorder of heart                                   |128599005     |Is a             |SNOMED           |321588        |Heart disease
        SNOMED           |43530961      |Induced termination of pregnancy complicated by cardiac failure|609507007     |Is a             |SNOMED           |316139        |Heart failure
        SNOMED           |45766164      |Heart failure with reduced ejection fraction                   |703272007     |Is a             |SNOMED           |316139        |Heart failure
        SNOMED           |316139        |Heart failure                                                  |84114007      |Is a             |SNOMED           |4024552       |Disorder of cardiac function
        SNOMED           |43530856      |High risk of heart failure, stage B                            |609389009     |Is a             |SNOMED           |4027255       |Structural disorder of heart
        SNOMED           |316139        |Heart failure                                                  |84114007      |Subsumes         |SNOMED           |45766164      |Heart failure with reduced ejection fraction
        SNOMED           |321588        |Heart disease                                                  |56265001      |Subsumes         |SNOMED           |4024552       |Disorder of cardiac function
        SNOMED           |4024552       |Disorder of cardiac function                                   |105981003     |Subsumes         |SNOMED           |316139        |Heart failure
        SNOMED           |321588        |Heart disease                                                  |56265001      |Subsumes         |SNOMED           |4027255       |Structural disorder of heart
        SNOMED           |4027255       |Structural disorder of heart                                   |128599005     |Subsumes         |SNOMED           |43530856      |High risk of heart failure, stage B
        SNOMED           |316139        |Heart failure                                                  |84114007      |Subsumes         |SNOMED           |43530961      |Induced termination of pregnancy complicated by cardiac failure
        """
        self.assertEqual(edges3, [ ( "4024552", "316139" ), ( "316139", "43530961" ), ( "316139", "45766164" ),
                             ( "321588", "4024552" ), ( "321588", "4027255" ), ( "4027255", "43530856" ) ] )

        #Testing a relationship where a common ancestor is needed to connect the graph
        edges3 = wholegraph([4027255, 43530856, 4024552, 316139, 45766164, 43530961])
        """
        ┌────────────┬──────────────────────────────────────────────────┬───────────┬───────────────┬──────────────────┬──────────────────┬──────────────┬────────────────┬────────────┬────────────────────────────────────┬───────────┬─────────────────────┐
        │ concept_id │                   concept_name                   │ domain_id │ vocabulary_id │ concept_class_id │ standard_concept │ concept_code │ invalid_reason │ domain_cnt │               domain               │ total_cnt │ distinct_person_cnt │
        ├────────────┼──────────────────────────────────────────────────┼───────────┼───────────────┼──────────────────┼──────────────────┼──────────────┼────────────────┼────────────┼────────────────────────────────────┼───────────┼─────────────────────┤
        │     316139 │ Heart failure                                    │ Condition │ SNOMED        │ Clinical Finding │ S                │ 84114007     │ ∅              │          2 │ drug_exposure,condition_occurrence │   4105468 │ 20,613310           │
        │     321588 │ Heart disease                                    │ Condition │ SNOMED        │ Clinical Finding │ S                │ 56265001     │ ∅              │          1 │ condition_occurrence               │   1067160 │ 290357              │
        │    4024552 │ Disorder of cardiac function                     │ Condition │ SNOMED        │ Clinical Finding │ S                │ 105981003    │ ∅              │          1 │ condition_occurrence               │      1192 │ 421                 │
        │    4027255 │ Structural disorder of heart                     │ Condition │ SNOMED        │ Clinical Finding │ S                │ 128599005    │ ∅              │          1 │ condition_occurrence               │       613 │ 231                 │
        │   43530856 │ High risk of heart failure, stage B              │ Condition │ SNOMED        │ Clinical Finding │ S                │ 609389009    │ ∅              │          1 │ condition_occurrence               │        20 │ 20                  │
        │   43530961 │ Induced termination of pregnancy complicated by …│ Condition │ SNOMED        │ Clinical Finding │ S                │ 609507007    │ ∅              │          1 │ condition_occurrence               │        20 │ 20                  │
        │            │…cardiac failure                                  │           │               │                  │                  │              │                │            │                                    │           │                     │
        │   45766164 │ Heart failure with reduced ejection fraction     │ Condition │ SNOMED        │ Clinical Finding │ S                │ 703272007    │ ∅              │          1 │ condition_occurrence               │     10913 │ 3386                │
        └────────────┴──────────────────────────────────────────────────┴───────────┴───────────────┴──────────────────┴──────────────────┴──────────────┴────────────────┴────────────┴────────────────────────────────────┴───────────┴─────────────────────┘

        "vocabulary_id_1"|"concept_id_1"|"concept_name_1"                                               |"concept_code"|"relationship_id"|"vocabulary_id_2"|"concept_id_2"|"concept_name_2"
        SNOMED           |316139        |Heart failure                                                  |84114007      |Is a             |SNOMED           |4024552       |Disorder of cardiac function
        SNOMED           |43530856      |High risk of heart failure, stage B                            |609389009     |Is a             |SNOMED           |4027255       |Structural disorder of heart
        SNOMED           |45766164      |Heart failure with reduced ejection fraction                   |703272007     |Is a             |SNOMED           |316139        |Heart failure
        SNOMED           |43530961      |Induced termination of pregnancy complicated by cardiac failure|609507007     |Is a             |SNOMED           |316139        |Heart failure
        SNOMED           |4027255       |Structural disorder of heart                                   |128599005     |Subsumes         |SNOMED           |43530856      |High risk of heart failure, stage B
        SNOMED           |316139        |Heart failure                                                  |84114007      |Subsumes         |SNOMED           |43530961      |Induced termination of pregnancy complicated by cardiac failure
        SNOMED           |316139        |Heart failure                                                  |84114007      |Subsumes         |SNOMED           |45766164      |Heart failure with reduced ejection fraction
        SNOMED           |4024552       |Disorder of cardiac function                                   |105981003     |Subsumes         |SNOMED           |316139        |Heart failure
        """
        self.assertEqual(edges3,
                         [ ( "4024552", "316139" ), ( "316139", "43530961" ), ( "316139", "45766164" ),
                           ( "321588", "4024552" ), ( "321588", "4027255" ), ( "4027255", "43530856" ) ] )


# Uncomment this and run this file and run directly to run all tests
if __name__ == '__main__':
    unittest.main()
    # asyncio.run(TestGraph().test_concept_graph())
    # asyncio.run(TestGraph().test_concept_graph())
