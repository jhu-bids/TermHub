/*
TODO: Refactor & add more test cases:
  [Frontend functional / unit tests #701](https://github.com/jhu-bids/TermHub/issues/701)

### Definitions
- **Test targets**: Specific functionality we're testing, e.g. a single function.
- **Test cases**: Ambiguous. Could be (a) the csets for "test inputs", or (b) a single executable unit test / test case
w/in the given framework (combo of "test input" x "test target").
 */
import React from 'react';
import {renderHook, act} from '@testing-library/react-hooks';
import { describe, test, expect, /*beforeAll, afterAll, beforeEach, afterEach */} from '@jest/globals';
import {
  GraphContainer,
  makeGraph,
  GraphOptionsProvider,
  useGraphOptions,
} from './state/GraphState';
import {graphOptionsInitialState,} from './state/AppState';

// siggie 2024-09-05 to @joeflack4: I just refactored the following out of
//  this file into json files, but now I see that these data already exist in
//  data files in ./test/test_backend/routes/static/concept_graph

// const singleSmallFromConceptGraphEndpoint = {
// 	"edges":[[4174977,380096],[4034964,4029423],[4311708,376112],[4102176,35625722],[442793,443767],[442793,4034964],[376112,4044392],[380096,4210128],[4210128,4161671],[4044391,4311708],[4129519,43531010],[4029423,4016047],[443767,4102176],[443767,4174977],[443767,4224419],[35625722,35625724]],
// 	"concept_ids":[4174977,43531010,4161671,4327944,4221962,4237068,4034962,4034964,4311708,4294429,4102176,45766050,4224419,442793,4016047,376112,35626038,35626039,4162239,36674752,380096,43022019,4252356,4210128,44833365,3172958,4270049,4044391,4044392,4129519,4029423,4129524,4129525,443767,35625722,35625724],
// 	"filled_gaps":[380096,4210128,376112,443767,35625722,4311708,4029423],
// 	"missing_from_graph":[4252356,44833365],
// 	"hidden_by_vocab":{},
// 	"nonstandard_concepts_hidden":[]
// };
import singleSmallTestData from './jest-data/singleSmallGraph.json';
import manySmallGraphContainerGraphData
  from './jest-data/manySmallGraphContainerGraphData.json';
import asthmaGraphData from './jest-data/asthmaExampleGraphData.json';
// diagramCase: last copied from test_graph.py test_get_missing_in_between_nodes(): 2024/02/11
// edges only. see https://github.com/jhu-bids/TermHub/blob/develop/docs/graph.md
import _diagramCase from './jest-data/diagramCase.json';

let diagramCase = convertToArrayOfStrings(_diagramCase);

// todo: add ./testing_get_missing_in_between_nodes.py

// TESTS
// TODO: What are some good assertions, given various inputs?
// siggie 2024-09-05: I'm not sure this test does much. I think
//  there's more real testing of this in ./test/test_backend/routes/test_graph.py
// - makeGraph()
test('makeGraph() - diagram case', () => {
  const uniqueConcepts = [...new Set(diagramCase.flat())];
  const uniqueConceptObjs = uniqueConcepts.map(d => ({concept_id: d}));
  const [graph, nodes] = makeGraph(diagramCase, uniqueConceptObjs);

  // noinspection JSUnresolvedReference idkWhyUnresolved
  expect(graph.directedSize).toBe(32);
  expect(graph.nodes()).toStrictEqual(uniqueConcepts);
  expect(nodes.map(n => n.concept_id)).toStrictEqual(uniqueConcepts);
});

// TODO:
// test('makeGraph() - 1 cset "single small"', () => {
// });
//
// // TODO:
// test('makeGraph() - 2+ csets', () => {
// });

// - roots, leaves
// todo?
// test('roots, leaves - diagram case', () => {});

describe(
    `Single small: ${singleSmallTestData.codeset_ids[0]} ${singleSmallTestData.concept_set_names[0]}`,
    () => {
      const {graphData, roots, leaves, firstRow, } = singleSmallTestData;
      const wrapper = ({children}) => (
          <GraphOptionsProvider>{children}</GraphOptionsProvider>
      );
      const {result} = renderHook(() => useGraphOptions(), {wrapper});
      const [graphOptions, graphOptionsDispatch] = result.current;
      // graphRender();
      const gc = new GraphContainer(graphData);
      let newGraphOptions = gc.setGraphDisplayConfig(graphOptions);
      gc.getDisplayedRows(newGraphOptions);
      newGraphOptions = gc.setGraphDisplayConfig(graphOptions);
      graphOptionsDispatch({type: 'REPLACE', graphOptions: newGraphOptions});

      test('roots', () => {
        expect(gc.roots).toStrictEqual(roots); // did include 4044391, but that's a grandchild of 442793
      });

      test('leaves', () => {
        expect(gc.leaves).toStrictEqual(leaves);
      });
      test('initial graphOptions', () => {
        expect(graphOptions).toEqual(graphOptionsInitialState);
      });
      test('initially displays root nodes', () => {
        expect(gc.displayedRows.map(r => r.concept_id)).toEqual(roots);
      });

      describe('First row expand/collapse', () => {
        const row = gc.displayedRows[0];

        test('has expected first row', () => {
          expect(row).toEqual(firstRow);
        });

        test('expands first row correctly', () => {
          act(() => { // toggle first row
            graphOptionsDispatch({
              gc,
              type: 'TOGGLE_NODE_EXPANDED',
              nodeId: row.concept_id,
              direction: 'expand',
            });
            graphRender();
          });

          // Check if state updated correctly
          // expect(result.current[0]).toEqual(/* your expected updated state */);
        });

        console.log(gc);
      });
});

function graphRender(graphData, graphOptions) {
  let gc = new GraphContainer(graphData);
  let newGraphOptions = gc.setGraphDisplayConfig(graphOptions);
  gc.getDisplayedRows(newGraphOptions);
  newGraphOptions = gc.setGraphDisplayConfig(graphOptions);
  // graphOptionsDispatch({type: 'REPLACE', graphOptions: newGraphOptions});
}

test('roots, leaves - 2+ csets', () => {
  // codeset_ids: 1000002657, 241882304, 488007883, 1000087163
  const gc = new GraphContainer(manySmallGraphContainerGraphData);
  expect(gc.roots).
      toStrictEqual([
        '76685',
        '81893',
        '441269',
        '442793',
        '4044391',
        '4129519',
        '4209139',
        'unlinked']);
  expect(gc.leaves).
      toStrictEqual([
        '78799',
        '81400',
        '436956',
        '3172958',
        '4016047',
        '4029372',
        '4031048',
        '4034962',
        '4043730',
        '4044392',
        '4045731',
        '4046356',
        '4048782',
        '4086978',
        '4129524',
        '4129525',
        '4135454',
        '4146936',
        '4161671',
        '4162239',
        '4187900',
        '4204694',
        '4215003',
        '4215784',
        '4221962',
        '4224419',
        '4237068',
        '4252356',
        '4269919',
        '4270049',
        '4271197',
        '4294429',
        '4301738',
        '4327944',
        '35625724',
        '35626038',
        '35626039',
        '36674478',
        '36674752',
        '36713763',
        '37116298',
        '37116300',
        '37116301',
        '37117740',
        '40481367',
        '43022019',
        '43531010',
        '43531560',
        '43531561',
        '44783784',
        '44833365',
        '45766050',
        '46269838',
        '46269840',
        '46269841',
        '46269848',
        '46269850',
        '46269851']);

});

test('with asthma example', () => {
  // codeset_ids: 400614256, 419757429, 484619125
  // console.log(asthmaGraphData);
  const gc = new GraphContainer(asthmaGraphData);
  // these have nothing to do with asthma, i'm not sure why they were in the test
  // expect(gc.roots).toStrictEqual(["76685", "81893", "441269", "442793", "4044391", "4129519", "4209139", "unlinked"]);
  expect(gc.roots).
      toStrictEqual([
        '4152913',
        '4155469',
        '4191479',
        '40483397',
        '45769438',
        '45773005',
        'unlinked']);
  expect(gc.leaves).toStrictEqual([
    '252341',
    '259055',
    '3080832',
    '3105910',
    '3124228',
    '3124987',
    '3124988',
    '3124991',
    '3137829',
    '3137830',
    '3141621',
    '3141622',
    '3153572',
    '3162019',
    '3164757',
    '3201654',
    '3240140',
    '3427139',
    '3427698',
    '3429308',
    '3430639',
    '3432874',
    '3436486',
    '3439569',
    '3447664',
    '3451367',
    '3451853',
    '3452171',
    '3452456',
    '3456756',
    '3458794',
    '3459941',
    '3466361',
    '3468370',
    '3472300',
    '3472327',
    '3475208',
    '3476610',
    '3557638',
    '3661412',
    '4112669',
    '4112831',
    '4119299',
    '4119300',
    '4123253',
    '4125022',
    '4147509',
    '4211530',
    '4271333',
    '4283362',
    '4309833',
    '35609846',
    '36684335',
    '37310241',
    '40316544',
    '40345717',
    '40345719',
    '40389375',
    '40395876',
    '40395878',
    '40395891',
    '40481763',
    '40561687',
    '42536648',
    '42539549',
    '43530693',
    '44824287',
    '44824288',
    '44831278',
    '44832423',
    '45543269',
    '45543270',
    '45548116',
    '45548117',
    '45557624',
    '45557626',
    '45562457',
    '45567265',
    '45567266',
    '45572169',
    '45572170',
    '45572171',
    '45576951',
    '45576952',
    '45581860',
    '45586674',
    '45586675',
    '45601133',
    '45601134',
    '45766727',
    '45766728',
    '45768964',
    '45768965',
    '45769443',
    '45771045',
    '45909769',
    '45917166',
    '45938316',
    '45939036',
    '45939199',
    '45939829',
    '45940320',
    '45946655',
    '46269771',
    '46269785',
    '46269802',
    '46270082',
    '46273487',
    '46274124']);
});

test('initial state and dispatch function', () => {
});

// UTILS
/* Used to convert input to be same as graphology serialization (all strings). */
function convertToArrayOfStrings(matrix) {
  var stringMatrix = [];
  for (var i = 0; i < matrix.length; i++) {
    var stringRow = [];
    for (var j = 0; j < matrix[i].length; j++) {
      stringRow.push(matrix[i][j].toString());
    }
    stringMatrix.push(stringRow);
  }
  return stringMatrix;
}