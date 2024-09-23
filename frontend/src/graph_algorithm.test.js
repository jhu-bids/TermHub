const { GraphContainer } = require('../src/state/GraphState');
const { graphOptionsInitialState, graphOptionsReducer } = require('../src/state/AppState');
const singleSmallTestData = require('../src/jest-data/singleSmallGraph.json');

describe('Graph Algorithm Tests', () => {
  let gc;
  let graphOptions;

  beforeEach(() => {
    gc = new GraphContainer(singleSmallTestData.graphData);
    graphOptions = { ...graphOptionsInitialState };
  });

  test('Initial displayed rows should match roots', () => {
    gc.getDisplayedRows(graphOptions);
    const displayedConceptIds = gc.displayedRows.map(row => row.concept_id);
    expect(displayedConceptIds).toEqual(singleSmallTestData.roots);
  });

  test('Expanding first row should display its children', () => {
    const firstRowConceptId = singleSmallTestData.roots[0];

    // Expand the first row
    const expandAction = {
      type: 'TOGGLE_NODE_EXPANDED',
      nodeId: firstRowConceptId,
      direction: 'expand'
    };
    graphOptions = graphOptionsReducer(graphOptions, expandAction);

    gc.getDisplayedRows(graphOptions);

    const firstRow = gc.displayedRows.find(row => row.concept_id === firstRowConceptId);
    expect(firstRow.childIds).toBeDefined();
    expect(firstRow.childIds.length).toBeGreaterThan(0);

    const displayedChildIds = firstRow.childIds.map(row => row.concept_id);
    expect(displayedChildIds).toEqual(expect.arrayContaining(singleSmallTestData.firstRow.childIds));
  });

  test('Collapsing expanded row should hide its children', () => {
    const firstRowConceptId = singleSmallTestData.roots[0];

    // First, expand the row
    let expandAction = {
      type: 'TOGGLE_NODE_EXPANDED',
      nodeId: firstRowConceptId,
      direction: 'expand'
    };
    graphOptions = graphOptionsReducer(graphOptions, expandAction);
    gc.getDisplayedRows(graphOptions);

    // Now, collapse the row
    let collapseAction = {
      type: 'TOGGLE_NODE_EXPANDED',
      nodeId: firstRowConceptId,
      direction: 'collapse'
    };
    graphOptions = graphOptionsReducer(graphOptions, collapseAction);
    gc.getDisplayedRows(graphOptions);

    const firstRow = gc.displayedRows.find(row => row.concept_id === firstRowConceptId);
    expect(firstRow.childIds).toBeUndefined();

    const displayedConceptIds = gc.displayedRows.map(row => row.concept_id);
    expect(displayedConceptIds).toEqual(singleSmallTestData.roots);
  });
});