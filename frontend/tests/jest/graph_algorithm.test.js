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
  let displayedRows;
  let allRows;
  let allRowsById;

  beforeEach(() => {
    /* this should run once, not before each test, right? */
    try {
      gc = new GraphContainer(dataCase.graphData);
      const x = gc.setupAllRows(gc.roots);
      allRows = x.allRows;
      allRowsById = x.allRowsById;
      graphOptions = { ...graphOptionsInitialState };
      displayedRows = gc.getDisplayedRows(graphOptions, allRows, allRowsById);
    } catch(e) {
      console.log(e);
      throw new Error(e);
    }
  });

  safeTest('1. Initial displayed rows should match roots', () => {
    const displayedConceptIds = displayedRows.map(row => row.concept_id + '');
    expect(displayedConceptIds.sort()).toEqual(dataCase.roots.map(String).sort());
  });

  safeTest('2. Initial displayed first row should match dataCase.first row', () => {
    // firstDisplayedRow = displayedRows.find(row => row.concept_id == firstRowConceptId);
    firstDisplayedRow = displayedRows[0];
    expect(firstDisplayedRow.concept_id == dataCase.firstRow.concept_id).toBeTruthy();
    expect(firstDisplayedRow.childIds.length).toEqual(dataCase.firstRow.childCount);  // expect number of kids
    // the childIds are already part of the firstDisplayedRow object, but are not displayed yet
    expect(firstDisplayedRow.childIds.map(String).sort()).toEqual(dataCase.firstRow.childIds.map(String).sort());
  });

  safeTest('3. Expanding first row should display its children', () => {
    const expandAction = { // Expand the first row
      type: 'TOGGLE_NODE_EXPANDED',
      rowPath: '/' + dataCase.firstRow.concept_id,
      direction: 'expand'
    };
    graphOptions = graphOptionsReducer(graphOptions, expandAction);
    displayedRows = gc.getDisplayedRows(graphOptions, allRows, allRowsById);
    const displayedChildObjects = displayedRows.slice(1, 1 + dataCase.firstRow.childIds.length);
    const displayedChildIds = displayedChildObjects.map(row => row.concept_id + '');
    // Test in correct order
    expect(displayedChildIds.map(String).sort()).toEqual(dataCase.firstRow.childIds.map(String).sort());
    // Test total rows = roots + n children expanded
    expect(displayedRows.length).toEqual(dataCase.roots.length + dataCase.firstRow.childIds.length);
  });

  safeTest('4. Collapsing first row should hide expanded children', () => {
    let collapseAction = {
      type: 'TOGGLE_NODE_EXPANDED',
      rowPath: '/' + dataCase.firstRow.concept_id,
      direction: 'collapse'
    };
    displayedRows = gc.getDisplayedRows(graphOptions, allRows, allRowsById);
    const displayedConceptIds = displayedRows.map(row => row.concept_id + '');
    expect(displayedConceptIds.sort()).toEqual(dataCase.roots.map(String).sort());
  });
});
