import {GraphContainer} from './state/GraphState';
import { graphOptionsInitialState, graphOptionsReducer } from './state/AppState';
import singleSmallTestData from './jest-data/singleSmallGraph.json';
import { safeTest, resetTestSuite } from './testUtils';

const singleSmallTestData = require('./jest-data/singleSmallGraph.json');
const manySmallGraphContainerGraphData = require('./jest-data/manySmallGraphContainerGraphData.json');
const asthmaGraphData = require('./jest-data/asthmaExampleGraphData.json');

const graphDataCases = [singleSmallTestData, manySmallGraphContainerGraphData, asthmaGraphData];

describe.each(graphDataCases)('Graph algorithm tests for $test_name', (dataCase) => {
  let gc;
  let graphOptions;

  beforeEach(() => {
    resetTestSuite(); // Reset the suite at the start
    gc = new GraphContainer(dataCase.graphData);
    graphOptions = { ...graphOptionsInitialState };
    gc.getDisplayedRows(graphOptions);
  });


  safeTest('1. Initial state is correct', () => {
    expect(testState).toEqual(/* expected initial state */);
  });

  safeTest('2. Expanding works correctly', () => {
    expandSomething(testState);
    expect(testState).toEqual(/* expected expanded state */);
  });
  test('Initial displayed rows should match roots', () => {
    const displayedConceptIds = gc.displayedRows.map(row => row.concept_id);
    expect(displayedConceptIds.map(String).sort()).toEqual(dataCase.roots.map(String).sort());
  });

  test('Expanding first row should display its children, collapsing should hide', () => {

    // get first displayed row. its childIds should match the test case first row childIds
    gc.getDisplayedRows(graphOptions);

    const firstRowConceptId = dataCase.roots[0];

    let firstRow = gc.displayedRows.find(row => row.concept_id == firstRowConceptId);
    expect(firstRow.childIds).toBeDefined();
    expect(firstRow.childIds.length).toBeGreaterThan(0);

    expect(firstRow.childIds.map(String).sort()).toEqual(dataCase.firstRow.childIds.map(String).sort());

    // Expand the first row
    const expandAction = {
      type: 'TOGGLE_NODE_EXPANDED',
      nodeId: firstRowConceptId,
      direction: 'expand'
    };
    graphOptions = graphOptionsReducer(graphOptions, expandAction);



    // Now, collapse the row
    let collapseAction = {
      type: 'TOGGLE_NODE_EXPANDED',
      nodeId: firstRowConceptId,
      direction: 'collapse'
    };
    graphOptions = graphOptionsReducer(graphOptions, collapseAction);
    gc.getDisplayedRows(graphOptions);

    firstRow = gc.displayedRows.find(row => row.concept_id === firstRowConceptId);
    expect(firstRow.childIds).toBeUndefined();

    const displayedConceptIds = gc.displayedRows.map(row => row.concept_id);
    expect(displayedConceptIds).toEqual(dataCase.roots);
  });
});
