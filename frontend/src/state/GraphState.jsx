import {
  cloneDeep,
  flatten,
  get,
  intersection,
  set,
  sortBy,
  sum,
  uniq,
} from 'lodash';
import Graph from 'graphology';
// import {bidirectional} from 'graphology-shortest-path/unweighted';
import {dfsFromNode} from 'graphology-traversal/dfs';
import {setOp} from '../utils';

const EXPAND_ALL_DEFAULT_THRESHOLD = 2000;
export class ExpandState {
  static EXPAND = 'expand';
  static COLLAPSE = 'collapse';
  static EXPAND_ALL = 'expandAll';

  static isValid(value) {
    return [this.EXPAND, this.COLLAPSE, this.EXPAND_ALL].includes(value);
  }
}

class ConceptClassVisibility {
  static SHOWN = 'shown';
  static HIDDEN = 'hidden';

  static isValid(value) {
    return [this.SHOWN, this.HIDDEN].includes(value);
  }
}

class GraphOptionsActionType {
  static TOGGLE_NODE_EXPANDED = 'TOGGLE_NODE_EXPANDED';
  static TOGGLE_OPTION = 'TOGGLE_OPTION';
  static TOGGLE_EXPAND_ALL = 'TOGGLE_EXPAND_ALL';
  static RESET = 'reset';
}

export const graphOptionsInitialState = {
  specialConceptTreatment: {
    addedCids: ConceptClassVisibility.SHOWN,
    definitionConcepts: ConceptClassVisibility.SHOWN,
    nonDefinitionConcepts: ConceptClassVisibility.SHOWN,
    standard: ConceptClassVisibility.SHOWN,
    classification: ConceptClassVisibility.SHOWN,
    nonStandard: ConceptClassVisibility.SHOWN,
    zeroRecord: ConceptClassVisibility.SHOWN,
    rxNormExtension: ConceptClassVisibility.HIDDEN,
    allButFirstOccurrence: ConceptClassVisibility.HIDDEN,
  },
  nested: true,
  specificPaths: {}, // { '/123/456': ExpandState.EXPAND, '/234/567': ExpandState.COLLAPSE }
  // expandAll is intentionally undefined until rows are displayed
  // hideRxNormExtension: true,
};

export function graphOptionsReducer(state, action) {
  if (!action?.type) return state;

  let {type, rowPath, expandDescendants, specialConceptType} = action;
  let graphOptions = action.graphOptions || state;

  switch (type) {
    case GraphOptionsActionType.TOGGLE_NODE_EXPANDED: {
      const { direction } = action;
      // will delete all when expandAll flips
      // could have two sets of specificPaths, one for expandAll, one for not

      if (!ExpandState.isValid(direction)) {
        console.error(`Invalid direction for TOGGLE_NODE_EXPANDED: ${direction}`);
        return state;
      }

      const specificPaths = { ...graphOptions.specificPaths };
      const currentState = specificPaths[rowPath];

      if (typeof currentState === 'undefined') {
        specificPaths[rowPath] = direction;
      } else {
        if (!ExpandState.isValid(currentState) || currentState === direction) {
          console.error(
            `Invalid state transition: current=${currentState}, requested=${direction}`
          );
        }
        delete specificPaths[rowPath];
      }

      return { ...graphOptions, specificPaths };
    }
    case GraphOptionsActionType.TOGGLE_OPTION: {
      if (!specialConceptType) {
        console.error('Missing specialConceptType for TOGGLE_OPTION');
        return state;
      }

      const currentVisibility =
        graphOptions.specialConceptTreatment[specialConceptType];

      const newVisibility = currentVisibility === ConceptClassVisibility.HIDDEN
        ? ConceptClassVisibility.SHOWN
        : ConceptClassVisibility.HIDDEN;

      return {
        ...graphOptions,
        specialConceptTreatment: {
          ...graphOptions.specialConceptTreatment,
          [specialConceptType]: newVisibility
        }
      };
    }
    case GraphOptionsActionType.TOGGLE_EXPAND_ALL:
      return {
        ...graphOptions,
        expandAll: !graphOptions.expandAll,
        specificPaths: {} // Reset paths when toggling expandAll
        // could have two sets of specificPaths, one for expandAll, one for not
      };
    case 'toggle-nested': {
      return {...state, nested: !state.nested}
    }
    case 'reset': {
      return action.resetValue;
    }
  }
  throw new Error("shouldn't get here");
  return {...state, ...graphOptions};
}

// window.graphFuncs = {bidirectional, dfsFromNode};

// versions of Set and Map that force keys to be strings
class StringSet extends Set {
  add(value) { super.add(value.toString()); }
  has(value) { return super.has(value.toString()); }
  delete(value) { return super.delete(value.toString()); }
}
class StringKeyMap extends Map {
  set(key, value) { super.set(key.toString(), value); }
  get(key) { return super.get(key.toString()); }
  has(key) { return super.has(key.toString()); }
  delete(key) { return super.delete(key.toString()); }
}

export const makeGraph = (edges, concepts) => {
  const graph = new Graph({allowSelfLoops: false, multi: false, type: 'directed'});
  let nodes = {};
  // add each concept as a node in the graph, the concept properties become the node attributes
  for (let c of concepts) {
    let nodeId = c.concept_id;
    graph.addNode(nodeId);
    nodes[nodeId] = {...c};
  }
  for (let edge of edges) {
    graph.addDirectedEdge(edge[0], edge[1]);
  }
  return [graph, nodes];
};

export class GraphContainer {
  constructor(graphData, /*, cloneThis */) {
    window.graphW = this; // for debugging
    this.gd = graphData;  // concepts, specialConcepts, csmi, edges, concept_ids,
                          // missing_from_graph, hidden_by_vocab, nonstandard_concepts_hidden
    set(this, 'gd.specialConcepts.allButFirstOccurrence', []);

    [this.graph, this.nodes] = makeGraph(this.gd.edges, this.gd.concepts);

    this.roots = this.graph.nodes().filter(n => !this.graph.inDegree(n));
    this.leaves = this.graph.nodes().filter(n => !this.graph.outDegree(n));

    // for concepts not linked to anything, move them under an artificial
    //  'unlinked' concept, and remove them from this.roots
    this.unlinkedConcepts = intersection(this.roots, this.leaves);

    let unlinkedConceptsParent = {
      concept_id: 'unlinked',
      concept_name: 'Concepts included but not linked to other concepts',
      not_a_concept: true,
      vocabulary_id: '--',
      standard_concept: '',
      total_cnt: 0,
      distinct_person_cnt: '0',
      status: "",
      // hasChildren: true,
      // levelsBelow: 1,
      childIds: this.unlinkedConcepts,
      // childCount: this.unlinkedConcepts.length,
      // descendantCount: this.unlinkedConcepts.length,
      // drc: sum(this.unlinkedConcepts.map(d => this.nodes[d].total_cnt || 0)), // Compute descendant counts
      // descendants: uniq(descendants), // Remove duplicates
    };
    this.graph.addNode('unlinked');
    this.nodes['unlinked'] = unlinkedConceptsParent;
    for (let c of this.unlinkedConcepts) {
      this.graph.addDirectedEdge('unlinked', c);
    }

    // delete unlinked concepts from this.roots
    this.roots = this.graph.nodes().filter(n => !this.graph.inDegree(n));

    this.#computeAttributes();
  }
  
  getDisplayedRows(graphOptions, allRows, allRowsById) {
    /*
    See new description of show/filter issue: https://github.com/jhu-bids/TermHub/issues/547
    Getting rid of showThoughCollapsed. But not sure how to handle hidden rows.

    if row collapsed, show summary in column of what's beneath it
    if row expanded but some children are hidden HTE, then show...?

    STC: showThoughCollapsed
    HTE: hideThoughExpanded
    SNC: specificPathsCollapsed (N=Nodes/Paths)
    SNE: specificPathsExpanded (N=Nodes/Paths)
    
    Special classes         Action              Default Label
    concepts                expandAll           false   Concepts
    TODO: make the expandAll default depend on number of concepts rather than being always false
    standard                nothing                     Standard concepts
    classification          nothing                     Classification concepts
  
    expandStateByPath (expanded/collapsed)              n/a
  
    addedCids               showThoughCollapsed true    Individually added concept_ids
    definitionConcepts      showThoughCollapsed false   Definition concepts
    added                   showThoughCollapsed false   n/a
    removed                 showThoughCollapsed false   n/a
  
    allButFirstOccurrence   hideThoughExpanded  true    All but first occurrence
    expansionConcepts       hideThoughExpanded  false   Expansion concepts
    nonStandard             hideThoughExpanded  false   Non-standard
    zeroRecord              hideThoughExpanded  false   Zero records / patients

    Algorithm
    For each row:
      showReasons: (todo)
        - showThoughCollapsed (definitions, added cids, comparison added/removed)
        - hidden parent/ancestor of showThoughCollapsed
        - child of specificPathsExpanded
      hideReasons:
        - non-root
        - hideThoughExpanded (expansion only, non-standard, zero pt, all but first)
        - child of specificPathsCollapsed
        - duplicate occurrence

    TODO:
      [ ] Column shows how many rows hidden below each displayed row
        With tooltip giving reasons
        Too complicated to have expand control in that field
      [ ] If expandAll, default icon is (-), otherwise (+)
        What happens to SNC/SNE when expandAll changes?
        Clear them? Have two sets of SNC/SNE and swap?
        Clear for now, then implement swap maybe
    TODO: decide how to handle showThoughCollapsed
      1.  Like before -- show path below nearest displayed ancestor
      2.  Actually expand down to STC row and have some way to indicate
          that siblings of the in-between nodes are not being displayed
      3.  Give users a way to see these separately and then expand
          manually to find the row of interest.
      *   - Example: Parent > [2 hidden levels] > Current Node

    Cases to think about (test?)
      Shown (definition) concept is descendant of hidden (nonStandard, zeroRecord) concept
        (-) Hidden concept    {hideReasons: [HTE(zero)],  showReasons: [parentOfSTC], result: show}
          (-) Def concept     {hideReasons: [childOfHTE], showReasons: [STC(def)],    result: show}
            (-) Another       {hideReasons: [],           showReasons: [childOfSTC],  result: show}
          (+) Def concept     {hideReasons: [childOfHTE], showReasons: [STC(def)],    result: show}
            (-) Another       {hideReasons: [childOfSNC], showReasons: [],            result: hide}

      Shown (definition) concept is descendant of hidden specificPathsCollapsed concept
        Ideally might depend on order of events, but too hard to code?
          If you collapse a parent of a STC node, expect the STC node to get hidden?
          If you turn show def concepts on while some are hidden undeer SNC, expect them to appear?
          Ok, keep hidden, but implement idea
        (+) Concept           {hideReasons: [],           showReasons: [root],        result: show}
          (-) Def concept     {hideReasons: [childOfSNC], showReasons: [STC(def)],    result: hide}
            (-) Another       {hideReasons: [descOfSNC],  showReasons: [childOfSTC],  result: hide}

      Shown (definition) concept is also hidden (zeroRecord) concept
        (-) Def zero concept  {hideReasons: [HTE(zero)],  showReasons: [STC(def)],    result: show}
        STC takes precedence over HTE

      Hidden (zeroRecord) concept is root
        Hide anyway

      specificNodeCollapsed while expandAll is on
        Hide descendants

      1. [ ] Generate allRows: list of all rows, in order, with duplicates
      2. [ ] If allButFirstOccurrence hidden, hide allButFirstOccurrence
          (and their descendants? descendants will be duplicate occurrences
          and hidden anyway)
          crap: what if STC/HTE settings affect which occurrence comes first?
            could that happen?
            having a hard time constructing the case (below). maybe just don't
              worry about it for now?
    
          (-) Concept 1         {hideReasons: [HTE(zero)],  showReasons: [parentOfSTC], result: show}
            (-) Concept 2       {hideReasons: [childOfHTE], showReasons: [STC(def)],    result: show}
            (-) Concept 3       {hideReasons: [childOfHTE], showReasons: [STC(def)],    result: show}
          ...
          (-) Concept 4         {hideReasons: [],           showReasons: [childOfSNE],  result: show}
            (-) Concept 2       {hideReasons: [childOfHTE], showReasons: [STC(def)],    result: show}
            (-) Concept 3       {hideReasons: [childOfHTE], showReasons: [STC(def)],    result: show}
    
      3. If expandAll, hide all HTE
      4. If not expandAll, hide everything that's
          a. not a root -- hides everything depth > 0;
      5. Unhide
          a. STC (showThoughCollapsed) That includes ancestors up to
             nearest not collapsed
          b. Child of SNE (specificPathsExpanded)
      6. Hide remaining HTE (hideThoughExpanded)
    */
    // Generate allRows
    // let {allRows, allRowsById} = this.setupAllRows(this.roots);

    if (graphOptions.expandAll) {
      // ....  no need to expand STC, because nothing collapsed except SNC
    } else {
      // Hide non-root rows (depth > 0)
      for (let row of allRows) {
        if (row.depth > 0) {
          row.display.hideReasons.nonRoot = true;
          row.display.result = 'hide';
        }
      }
    }

    // expandStateByPath: Expand and collapse children based on user having clicked +/- on row
    allRows.forEach((row, rowIdx) => {
      if (row.display.result === 'hide') return;
      let expandState = graphOptions.expandStateByPath[row.rowPath];
      if (expandState) {
        this.rowDisplay(rowIdx, expandState, 'specific', allRows);
      }
    });

    // hide all HTE (non-standard, zero pt, expansion only)
    for (let type in graphOptions.specialConceptTreatment) {
      if (type === 'allButFirstOccurrence') continue; // handle this differently
      if (graphOptions.specialConceptTreatment[type] === 'hidden') {
        // gather all the hideThoughExpanded ids
        (this.gd.specialConcepts[type] || []).forEach(id => {
          const rowsToHide = allRowsById.get(id) || [];
          for (const rowToHide of rowsToHide) {
            const rowToHideIdx = rowToHide.allRowsIdx;
            this.rowDisplay(rowToHideIdx, graphOptions.expandStateByPath[rowToHide.rowPath], type, allRows)
          }
        })
      }
    }
    // end hide all HTE

    let displayedRows = allRows.filter(r => r.display.result !== 'hide');

    // 2. Get list of allButFirstOccurrence; hide if option on
    let rowsPerId = {};
    displayedRows.forEach(row => {
      if (rowsPerId[row.concept_id]) {
        this.gd.specialConcepts.allButFirstOccurrence.push(row.rowPath);
        if (graphOptions.specialConceptTreatment.allButFirstOccurrence === 'hidden') {
          row.display.hideReasons.duplicate = true;
          row.display.result = 'hide';
        }
      } else {
        rowsPerId[row.concept_id] = 0;
      }
      row.nodeOccurrence = rowsPerId[row.concept_id]++;
    });
    //  this could filter allRows, shouldn't matter
    displayedRows = displayedRows.filter(r => r.display.result !== 'hide');

    // return this.displayedRows.filter(r => r.depth < 3);
    return displayedRows;
    // return this.getDisplayedRowsOLD(graphOptions);
  }
  
  rowDisplay(rowIdx, showHide, reason, allRows) {
    // this.rowDisplay(row, graphOptions.expandStateByPath[row.rowPath], 'specific')
    // this.rowDisplay(rowToHide, graphOptions.expandStateByPath[rowToHide.rowPath], type)
    // TODO: don't hide if it has children that should be shown
    if (reason === 'specific') {
      if (showHide === ExpandState.EXPAND) {
        for (let childRow of this.getDescendantRows(rowIdx, allRows, 1)) {
          childRow.display.showReasons.childOfExpanded = true;
          childRow.display.result = 'show';
        }
      } else if (showHide === ExpandState.EXPAND_ALL) {
        for (let childRow of this.getDescendantRows(rowIdx, allRows, Infinity)) {
          childRow.display.showReasons.childOfExpandAll = true;
          childRow.display.result = 'show';
        }
      } else if (showHide === ExpandState.COLLAPSE) {
        for (let childRow of this.getDescendantRows(rowIdx, allRows, Infinity)) {
          childRow.display.hideReasons.descendantOfCollapsed = rowIdx;
          childRow.display.result = 'hide';
        }
      } else {
        throw new Error(`Invalid showHide: ${showHide}`);
      }
    } else {
      const rowToHide = allRows[rowIdx];
      rowToHide.display.hideReasons[reason] = true;
      rowToHide.display.result = 'hide';
      for (let childRow of this.getDescendantRows(rowIdx, allRows)) {
        childRow.display.hideReasons[`descendantOf_${reason}`] = rowIdx;
        childRow.display.result = 'hide';
      }
    }
  }
  
  getDescendantRows(parentRowIdx, allRows, howDeep=Infinity) {
    // sort of a fragile way to do it, but will get all rows deeper
    //  than current row until the next row of the same depth
    // if howDeep is passed, will not return rows that much deeper than current row
    //  so, howDeep = 1 will get direct children, howDeep = 2, children and grandchildren
    // let idx = allRows.indexOf(parentRow) + 1;
    const parentRow = allRows[parentRowIdx];
    let idx = parentRowIdx + 1;
    let rows = [];
    while (idx < allRows.length && allRows[idx].depth > parentRow.depth) {
      if (allRows[idx].depth <= parentRow.depth + howDeep) {
        rows.push(allRows[idx]);
      }
      idx++;
    }
    return rows;
  }
  
  /* setupAllRows
  * Nomenclature: Rows, nodes, &concepts are all the same thing; just using term that fits purpose at the moment. */
  setupAllRows(rootNodes) {
    let allRows = [];
    let allRowsById = new StringKeyMap(); // start by getting lists of rowIdx by concept_id
    const addRows = (nodeIds, parentPath = '', depth = 0) => {
      let nodes = nodeIds.map(id => this.nodes[id]);
      nodes = sortBy(nodes, this.sortFunc);
      for (let node of nodes) {
        // Create `row`: `node` props, plus `depth`, `rowPath`, `display`, index
        let row = {...node, depth, rowPath: `${parentPath}/${node.concept_id}` };
        row.display = {
          hideReasons: {},
          showReasons: {},
          result: '',
        }
        row.allRowsIdx = allRows.length;
        
        // Add row
        // - to rows array
        allRows.push(row);
        // - too lookup
        if (allRowsById.has(row.concept_id)) {
          allRowsById.get(row.concept_id).push(row);
        } else {
          allRowsById.set(row.concept_id, [row]);
        }
        
        // If children/descendants, add rows for them, too
        if (node.childIds && node.childIds.length) {
          addRows(node.childIds, row.rowPath, depth + 1);
        }
      }
    };
    addRows(rootNodes);
    return {allRows, allRowsById};
  }

  sortFunc = (d => {
    // used to sort each level of the comparison table.
    // todo: allow this to be changed by user
    let n = typeof(d) === 'object' ? d : this.nodes[d];
    return n.not_a_concept  // not_a_concept should just be unlinked and should go to bottom
        ? Infinity
        : - n.drc;
    // let statusRank = n.isItem && 3 + n.added && 2 + n.removed && 1 || 0;
    // return - (n.drc || n.descendantCount || n.levelsBelow || n.status ? 1 : 0);
    // return - (n.levelsBelow || n.descendantCount || n.status ? 1 : 0);
  })

  #computeAttributes() {
    // compute children, descendants, child/descendant counts -- counts
    //  of concepts and also of records using this term's children/descendants
    const graph = this.graph;
    let nodes = this.nodes;
    function computeAttributesFunc(nodeId, level) { // recursive function, called on each node's children
      let node = nodes[nodeId];
      // Check if the attributes have already been computed to avoid recomputation
      if (node.descendantCount !== undefined) {
        return node;
      }
      node.levelsBelow = 0;
      node.descendantCount = 0;
      node.childCount = 0;
      node.drc = node.total_cnt || 0;

      const childIds = graph.outNeighbors(node.concept_id); // Get outgoing neighbors (children)
      if (childIds.length == 0) { // If there are no children, this node is a leaf node
        return node;
      }
      node.childIds = childIds;
      let descendants = childIds;

      childIds.forEach(childId => {
        let child = computeAttributesFunc(childId, level + 1);

        node.levelsBelow = Math.max(node.levelsBelow, 1 + child.levelsBelow); // Update max depth if this path is deeper
        if (child.descendants) {
          descendants = descendants.concat(child.descendants);
        }
      });

      // nodes[nodeId] = node = {...node, descendantCount: descendants.length, levelsBelow, drc};
      // nodes[nodeId] = node = {...node};   // why?
      // TODO: node.level = level; not sure why level isn't always correct;
      //  to see problem, try `gc.displayedRows.filter(d => d.depth != d.level)` from comparison renderer

      // if (levelsBelow > 0) { // todo: WHY IS THIS COMMENTED OUT?
        // node.expanded = false;  // TODO: deal with expanded differently for shown and hidden
        node.hasChildren = true;
        node.descendants = uniq(descendants); // Remove duplicates
        node.descendantCount = node.descendants.length;
        node.drc += sum(node.descendants.map(d => nodes[d].total_cnt || 0)); // Compute descendant counts
        node.childIds = childIds;
        node.childCount = childIds.length;
      // }

      return node;
    }

    // Iterate over all nodes to compute and store attributes
    // this.graph.nodes().forEach(node => {})
    for (let root of this.roots) {
      computeAttributesFunc(root, 0);
    };
    return nodes;
  }
  graphCopy() {
    return this.graph.copy();
  }
  
  /* `setGraphDisplayConfig()`:  These are all options that appear in Show Stats/Options
  *
  *  Returns:
  *   graphOptions: Object
  *
  *  Side effects:
  *   Sets: this.graphDisplayConfig (Object)
  *   Sets: this.graphDisplayConfigList (Array)
  *   Sets: graphOptions.specialConceptTreatment[type]
  *
  *  displayOptions logic
  *  See code for hidden-rows column in CsetComparisonPage StatsAndOptions table.
  *
  *  If specialTreatmentRule is 'show though collapsed', then what we care
  *  about are how many currently hidden rows will be shown if option is
  *  turned on and how many currently shown rows will be hidden if option
  *  is turned off.
  *
  *  If specialTreatmentRule is 'hide though expanded', then what we care
  *  about are how many currently visible rows will be hidden if option is
  *  turned on and how many currently hidden rows will be unhidden if option
  *  is turned off.
  *
  * */
  setGraphDisplayConfig(graphOptions, allRows, displayedRows) {
    // these are all options that appear in Show Stats/Options

    const displayedConceptIds = uniq(displayedRows.map(r => r.concept_id));
    let displayOrder = 0;
    if (typeof(graphOptions.expandAll) === 'undefined') {
      graphOptions.expandAll = allRows.length <= EXPAND_ALL_DEFAULT_THRESHOLD;
    }
    let displayOptions = {
      concepts: {
        name: "All", displayOrder: displayOrder++,
        total: this.gd.concept_ids.length,
        hiddenConceptCnt: setOp('difference', this.gd.concept_ids, displayedConceptIds).length,
        displayedConceptCnt: setOp('intersection', this.gd.concept_ids, displayedConceptIds).length,
      },
      addedCids: {
        name: "Individually added concept_ids", displayOrder: displayOrder++,
        total: this.gd.specialConcepts.addedCids.length,
        hiddenConceptCnt: setOp('difference', this.gd.specialConcepts.addedCids, displayedConceptIds).length,
        displayedConceptCnt: setOp('intersection', this.gd.specialConcepts.addedCids, displayedConceptIds).length,
      },
      definitionConcepts: {
        name: "Definition concepts", displayOrder: displayOrder++,
        total: this.gd.specialConcepts.definitionConcepts.length,
        displayedConceptCnt: setOp('intersection', this.gd.specialConcepts.definitionConcepts, displayedConceptIds).length,
        hiddenConceptCnt: setOp('difference', this.gd.specialConcepts.definitionConcepts, displayedConceptIds).length,
      },
      nonDefinitionConcepts: {
        name: "Non-definition concepts", displayOrder: displayOrder++,
        total: this.gd.specialConcepts.nonDefinitionConcepts.length,
        displayedConceptCnt: setOp('intersection', this.gd.specialConcepts.nonDefinitionConcepts, displayedConceptIds).length,
        hiddenConceptCnt: setOp('difference', this.gd.specialConcepts.nonDefinitionConcepts, displayedConceptIds).length,
      },
      /*
      added: {
        name: "Added to compared", displayOrder: displayOrder++,
        total: get(this.gd.specialConcepts, 'added.length', undefined),
        hiddenConceptCnt: setOp('difference', this.gd.specialConcepts.added, displayedConceptIds).length,
      },
      removed: {
        name: "Removed from compared", displayOrder: displayOrder++,
        total: get(this.gd.specialConcepts, 'removed.length', undefined),
        hiddenConceptCnt: setOp('difference', this.gd.specialConcepts.removed, displayedConceptIds).length,
      },
       */
      standard: {
        name: "Standard concepts", displayOrder: displayOrder++,
        total: this.gd.concepts.filter(c => c.standard_concept === 'S').length,
        displayedConceptCnt: setOp('intersection', this.gd.concepts.filter(c => c.standard_concept === 'S').map(d =>d.concept_id), displayedConceptIds).length,
        hiddenConceptCnt: setOp('difference', this.gd.concepts.filter(c => c.standard_concept === 'S').map(d =>d.concept_id), displayedConceptIds).length,
      },
      classification: {
        name: "Classification concepts", displayOrder: displayOrder++,
        total: this.gd.concepts.filter(c => c.standard_concept === 'C').length,
        displayedConceptCnt: setOp('intersection', this.gd.concepts.filter(c => c.standard_concept === 'C').map(d =>d.concept_id), displayedConceptIds).length,
        hiddenConceptCnt: setOp('difference', this.gd.concepts.filter(c => c.standard_concept === 'C').map(d =>d.concept_id), displayedConceptIds).length,
      },
      nonStandard: {
        name: "Non-standard", displayOrder: displayOrder++,
        total: this.gd.specialConcepts.nonStandard.length,
        displayedConceptCnt: setOp('intersection', this.gd.specialConcepts.nonStandard, displayedConceptIds).length,
        hiddenConceptCnt: setOp('difference', this.gd.specialConcepts.nonStandard, displayedConceptIds).length,
      },
      zeroRecord: {
        name: "Zero records / patients", displayOrder: displayOrder++,
        total: this.gd.specialConcepts.zeroRecord.length,
        displayedConceptCnt: setOp('intersection', this.gd.specialConcepts.zeroRecord, displayedConceptIds).length,
        hiddenConceptCnt: setOp('difference', this.gd.specialConcepts.zeroRecord, displayedConceptIds).length,
      },
      rxNormExtension: {
        name: "RxNorm Extension", displayOrder: displayOrder++,
        total: this.gd.specialConcepts.rxNormExtension.length,
        displayedConceptCnt: setOp('intersection', this.gd.specialConcepts.rxNormExtension, displayedConceptIds).length,
        hiddenConceptCnt: setOp('difference', this.gd.specialConcepts.rxNormExtension, displayedConceptIds).length,
      },
      allButFirstOccurrence: {
        name: "All but first occurrence", displayOrder: displayOrder++,
        total: this.gd.specialConcepts.allButFirstOccurrence.length,
        displayedConceptCnt: get(graphOptions, 'specialConceptTreatment.allButFirstOccurrence', true)
            ? 0
            : this.gd.specialConcepts.allButFirstOccurrence.length,
        hiddenConceptCnt: get(graphOptions, 'specialConceptTreatment.allButFirstOccurrence', true)
            ? this.gd.specialConcepts.allButFirstOccurrence.length
            : 0,
        /* special_v_displayed: () => {
          let special = this.gd.specialConcepts.allButFirstOccurrence.map(p => p.join('/'));
          let displayed = flatten(Object.values(this.displayedNodePaths).map(paths => paths.map(path => path.join('/'))))
          return [special, displayed];
        }, */
      },
    }
    for (let type in displayOptions) {
      let displayOption = {...get(this, ['graphDisplayConfig', type], {}), ...displayOptions[type]};  // don't lose stuff previously set
      // if (typeof(displayOption.total) === 'undefined') // don't show displayOptions that don't represent any concepts
      if (! (displayOption.total > 0)) {  // addedCids was 0 instead of undefined. will this hide things that shouldn't be hidden?
        // console.log(`deleting ${type} from statsopts`);
        delete displayOptions[type];
        continue;
      }
      displayOption.type = type;
      if (typeof(displayOption.specialTreatmentDefault) !== 'undefined') {
        if (typeof (displayOption.specialTreatment) === 'undefined') {
          // set specialTreatment to default only when initializing stats options
          // type === 'addedCids' && console.log(`setting ${type} to default`);
          displayOption.specialTreatment = displayOption.specialTreatmentDefault;
        }
        if (typeof(graphOptions.specialConceptTreatment[type]) === 'undefined') {
          // set specialConceptTreatment[type] only when not already in graphOptions
          // type === 'addedCids' && console.log(`setting graphOption.specialConceptTreatment.${type} to ${displayOption.specialTreatment}`);
          graphOptions.specialConceptTreatment[type] = displayOption.specialTreatment;
        } else {
          // already have an option set, use that
          // this is wrong, but allows flipping bit if other bit is true
          // graphOptions.specialConceptTreatment[type] = (Boolean(graphOptions.specialConceptTreatment[type] + displayOption.specialTreatment) % 2);
          // no this is wrong
          displayOption.specialTreatment = graphOptions.specialConceptTreatment[type];
          // type === 'addedCids' && console.log(`just set specialTreatment.${type} to ${displayOption.specialTreatment}`);
        }
      }
      displayOptions[type] = displayOption;

    }
    // TODO: gotta assemble whatever's needed for graphOptions
    this.graphDisplayConfigList = sortBy(displayOptions, d => d.displayOrder);
    this.graphDisplayConfig = displayOptions;
  }

  graphLayout(maxWidth=12) {
    const layerSpacing = 120;
    const nodeSpacing = 120;
    const graph = this.graph.copy();
    for (let nodeId in this.nodes) {
      graph.replaceNodeAttributes(nodeId, {...this.nodes[nodeId]});
    }
    const layers = computeLayers(graph, maxWidth); // Use a copy to keep the original graph intact
    // const layers = coffmanGrahamLayering(graph, maxWidth); // Use a copy to keep the original graph intact
    // that algorithm (both are from chatgpt) doesn't include all the nodes. dropping the ones left
    //    out of layering for the moment
    for (let nodeId in setOp('difference', graph.nodes(), flatten(layers))) {
      graph.dropNode(nodeId);
    }

    layers.forEach((layer, i) => {
      layer.forEach((node, j) => {
        graph.setNodeAttribute(node, 'size', 4);
        graph.setNodeAttribute(node, 'position', j); // Spread nodes horizontally within a layer
        graph.setNodeAttribute(node, 'layer', i); // Stack layers vertically
        // Here we are simply setting x and y for visualization
        // Spacing might need adjustments based on your visualization container's size
        graph.setNodeAttribute(node, 'x', j * nodeSpacing); // Spread nodes horizontally within a layer
        graph.setNodeAttribute(node, 'y', i * layerSpacing); // Stack layers vertically
      });
    });
    console.log(layers);
    return graph;
  }

  // TODO: probably don't need this anymore because already have allRows somewhere
  //       and maybe this doesn't work right or the same way, not sure
  wholeHierarchy() {
    // deep copy the node so we don't mutate the original
    let nodes = cloneDeep(this.nodes);
    let rows = [];
    function traverse(nodeId, depth = 0) {
      let node = nodes[nodeId];
      node.depth = depth;
      rows.push(node);
      node.hasChildren && node.childIds.forEach(childId => {
        traverse(childId, depth + 1); // Recurse
      });
    }
    for (let rootId of sortBy(this.roots, this.sortFunc)) {
      traverse(rootId);
    }
    return rows;
  }

  getDescendants(startNode) {
    let descendants = [];
    dfsFromNode(this.graph, startNode, function (node, attr, depth) {
      // console.log(node, attr, depth);
      descendants.push(node);
    });
    return descendants;
  }
}

function coffmanGrahamLayering(graph, maxWidth) {
  let layers = [];
  let currentLayer = [];
  let visited = new StringSet();

  // Function to find nodes with in-degree 0
  function findSources() {
    return graph.nodes().filter(node => {
      return graph.inDegree(node) === 0 && !visited.has(node);
    });
  }

  // Assign nodes to layers
  while (visited.size < graph.order) {
    let sources = findSources();
    if (sources.length === 0) {
      break; // Avoid infinite loop for cyclic graphs
    }

    for (let node of sources) {
      if (currentLayer.length < maxWidth) {
        currentLayer.push(node);
        visited.add(node);
      }
      if (currentLayer.length === maxWidth) {
        layers.push(currentLayer);
        currentLayer = [];
      }
    }

    // Remove nodes from graph to simulate "layer assignment"
    sources.forEach(node => {
      // graph.dropNode(node);
    });
  }

  if (currentLayer.length > 0) {
    layers.push(currentLayer); // Add remaining nodes to layers
  }

  return layers;
}
/*
   chatgpt graph layering stuff:
     https://chat.openai.com/share/443602bd-e90f-48cb-92a7-4f85b0accad2
 */
function computeLayers(graph, maxWidth) {
  const inDegrees = {};
  graph.nodes().forEach(node => {
    inDegrees[node] = graph.inDegree(node);
  });

  const layers = [];
  let currentLayer = [];
  let layerIndex = 0;

  while (Object.keys(inDegrees).length > 0) {
    // Select nodes with in-degree of 0 up to the maxWidth
    Object.entries(inDegrees).forEach(([node, inDegree]) => {
      if (inDegree === 0 && currentLayer.length < maxWidth) {
        currentLayer.push(node);
      }
    });

    // If no node was added but there are still nodes left, increment the layer index to avoid an infinite loop
    if (currentLayer.length === 0 && Object.keys(inDegrees).length > 0) {
      layerIndex++;
      continue;
    }

    // Update inDegrees for the next iteration
    currentLayer.forEach(node => {
      graph.outEdges(node).forEach(edge => {
        const target = graph.target(edge);
        if (inDegrees[target] !== undefined) {
          inDegrees[target]--;
        }
      });
      delete inDegrees[node];
    });

    if (layers[layerIndex] === undefined) {
      layers[layerIndex] = [];
    }

    // Add current layer to layers and prepare for next iteration
    layers[layerIndex] = layers[layerIndex].concat(currentLayer);
    currentLayer = [];

    // If the current layer is full or no more nodes can be added, move to the next layer
    if (layers[layerIndex].length >= maxWidth || !Object.values(inDegrees).some(inDegree => inDegree === 0)) {
      layerIndex++;
    }
  }

  return layers;
}
