import {GraphContainer} from '../../src/state/GraphState';
import { graphOptionsInitialState, graphOptionsReducer } from '../../src/state/AppState';
import { getSafeTestFunc, csetTestData} from '../testUtils';
let safeTest;

let graphDataCases = csetTestData.slice(0,1);

describe.each(graphDataCases)('Graph algorithm tests for $test_name', (dataCase) => {
  safeTest = getSafeTestFunc();
  let gc;
  let graphOptions;
  let firstDisplayedRow;

  beforeEach(() => {
    /* this should run once, not before each test, right? */
    try {
      gc = new GraphContainer(dataCase.graphData);
      graphOptions = { ...graphOptionsInitialState };
      gc.getDisplayedRows(graphOptions);
    } catch(e) {
      console.log(e);
      throw new Error(e);
    }
  });

  safeTest('1. Initial displayed rows should match roots', () => {
    const displayedConceptIds = gc.displayedRows.map(row => row.concept_id + '');
    expect(displayedConceptIds.sort()).toEqual(dataCase.roots.map(String).sort());
  });

  safeTest('2. Initial displayed first row should match dataCase.first row', () => {
    // firstDisplayedRow = gc.displayedRows.find(row => row.concept_id == firstRowConceptId);
    firstDisplayedRow = gc.displayedRows[0];
    expect(firstDisplayedRow.concept_id == dataCase.firstRow.concept_id).toBeTruthy();
    expect(firstDisplayedRow.childIds).toBeDefined();
    expect(firstDisplayedRow.childIds.length).toEqual(dataCase)
    // the childIds are already part of the firstDisplayedRow object, but are not displayed yet
    expect(firstDisplayedRow.childIds.map(String).sort()).toEqual(dataCase.firstRow.childIds.map(String).sort());
  });

  safeTest('3. Expanding first row should display its children', () => {
    const expandAction = { // Expand the first row
      type: 'TOGGLE_NODE_EXPANDED',
      nodeId: dataCase.firstRow.concept_id,
      direction: 'expand'
    };
    gc.getDisplayedRows(graphOptions);
    graphOptions = graphOptionsReducer(graphOptions, expandAction);
    const displayedChildIds = gc.displayedRows.slice(1, 1 + dataCase.firstRow.childIds.length);
    expect(displayedChildIds.map(String).sort()).toEqual(dataCase.firstRow.childIds.map(String).sort());
    expect(gc.displayedRows.length).toEqual(dataCase.roots.length + dataCase.firstRow.childIds.length);
  });

  safeTest('4. Collapsing first row should hide expanded children', () => {
    let collapseAction = {
      type: 'TOGGLE_NODE_EXPANDED',
      nodeId: dataCase.firstRow.concept_id,
      direction: 'collapse'
    };
    gc.getDisplayedRows(graphOptions);
    const displayedConceptIds = gc.displayedRows.map(row => row.concept_id + '');
    expect(displayedConceptIds.sort()).toEqual(dataCase.roots.map(String).sort());
  });
});
