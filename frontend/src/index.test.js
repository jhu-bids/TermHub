/*
TODO: Refactor & add more test cases:
  [Frontend functional / unit tests #701](https://github.com/jhu-bids/TermHub/issues/701)

### Definitions
- **Test targets**: Specific functionality we're testing, e.g. a single function.
- **Test cases**: Ambiguous. Could be (a) the csets for "test inputs", or (b) a single executable unit test / test case
w/in the given framework (combo of "test input" x "test target").
 */
import {test, expect} from '@jest/globals';
import {GraphContainer, makeGraph} from "./state/GraphState";


// const singleSmallFromConceptGraphEndpoint = {
// 	"edges":[[4174977,380096],[4034964,4029423],[4311708,376112],[4102176,35625722],[442793,443767],[442793,4034964],[376112,4044392],[380096,4210128],[4210128,4161671],[4044391,4311708],[4129519,43531010],[4029423,4016047],[443767,4102176],[443767,4174977],[443767,4224419],[35625722,35625724]],
// 	"concept_ids":[4174977,43531010,4161671,4327944,4221962,4237068,4034962,4034964,4311708,4294429,4102176,45766050,4224419,442793,4016047,376112,35626038,35626039,4162239,36674752,380096,43022019,4252356,4210128,44833365,3172958,4270049,4044391,4044392,4129519,4029423,4129524,4129525,443767,35625722,35625724],
// 	"filled_gaps":[380096,4210128,376112,443767,35625722,4311708,4029423],
// 	"missing_from_graph":[4252356,44833365],
// 	"hidden_by_vocab":{},
// 	"nonstandard_concepts_hidden":[]
// };
import singleSmallGraphContainerGraphData from './jest-data/singleSmallGraphContainerGraphData.json';
import manySmallGraphContainerGraphData from './jest-data/manySmallGraphContainerGraphData.json';
import asthmaGraphData from './jest-data/asthmaExampleGraphData.json';
import _diagramCase from './jest-data/diagramCase.json';


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

// VARS
// diagramCase: last copied from test_graph.py test_get_missing_in_between_nodes(): 2024/02/11
let diagramCase = convertToArrayOfStrings(_diagramCase);

;

// TESTS
// TODO: What are some good assertions, given various inputs?
// - makeGraph()
test('test makeGraph() - diagram case', () => {
  const uniqueConcepts = [...new Set(diagramCase.flat())];
  const uniqueConceptObjs = uniqueConcepts.map(d => ({concept_id: d}));
  const [graph, nodes] = makeGraph(diagramCase, uniqueConceptObjs);
  
  // noinspection JSUnresolvedReference idkWhyUnresolved
  expect(graph.directedSize).toBe(32);
  expect(graph.nodes()).toStrictEqual(uniqueConcepts);
});

// TODO:
// test('test makeGraph() - 1 cset "single small"', () => {
// });
//
// // TODO:
// test('test makeGraph() - 2+ csets', () => {
// });

// - roots, leaves
// todo?
// test('test roots, leaves - diagram case', () => {});

test('test roots, leaves - 1 cset "single small"', () => {
  const gc = new GraphContainer(singleSmallGraphContainerGraphData);
  expect(gc.roots).toStrictEqual(["442793", "4044391", "4129519", "unlinked"]);
  expect(gc.leaves).toStrictEqual(["3172958", "4016047", "4034962", "4044392", "4129524", "4129525", "4161671", "4162239", "4221962", "4224419", "4237068", "4252356", "4270049", "4294429", "4327944", "35625724", "35626038", "35626039", "36674752", "43022019", "43531010", "44833365", "45766050"]);
});

test('test roots, leaves - 2+ csets', () => {
  const gc = new GraphContainer(manySmallGraphContainerGraphData);
  expect(gc.roots).toStrictEqual(["76685", "81893", "441269", "442793", "4044391", "4129519", "4209139", "unlinked"]);
  expect(gc.leaves).toStrictEqual(["78799", "81400", "436956", "3172958", "4016047", "4029372", "4031048", "4034962", "4043730", "4044392", "4045731", "4046356", "4048782", "4086978", "4129524", "4129525", "4135454", "4146936", "4161671", "4162239", "4187900", "4204694", "4215003", "4215784", "4221962", "4224419", "4237068", "4252356", "4269919", "4270049", "4271197", "4294429", "4301738", "4327944", "35625724", "35626038", "35626039", "36674478", "36674752", "36713763", "37116298", "37116300", "37116301", "37117740", "40481367", "43022019", "43531010", "43531560", "43531561", "44783784", "44833365", "45766050", "46269838", "46269840", "46269841", "46269848", "46269850", "46269851"]);
});

test('tests with asthma example', () => {
  // console.log(asthmaGraphData);
  const gc = new GraphContainer(asthmaGraphData);
  expect(gc.roots).toStrictEqual(["76685", "81893", "441269", "442793", "4044391", "4129519", "4209139", "unlinked"]);
  expect(gc.leaves).toStrictEqual(["78799", "81400", "436956", "3172958", "4016047", "4029372", "4031048", "4034962", "4043730", "4044392", "4045731", "4046356", "4048782", "4086978", "4129524", "4129525", "4135454", "4146936", "4161671", "4162239", "4187900", "4204694", "4215003", "4215784", "4221962", "4224419", "4237068", "4252356", "4269919", "4270049", "4271197", "4294429", "4301738", "4327944", "35625724", "35626038", "35626039", "36674478", "36674752", "36713763", "37116298", "37116300", "37116301", "37117740", "40481367", "43022019", "43531010", "43531560", "43531561", "44783784", "44833365", "45766050", "46269838", "46269840", "46269841", "46269848", "46269850", "46269851"]);
});
