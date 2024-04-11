import React, {createContext, useContext, useReducer, useState} from "react";
import {get, sum, sortBy, uniq, flatten, intersection, cloneDeep,
        differenceWith, unionWith, intersectionWith, isEmpty, some} from "lodash";
import Graph from "graphology";
import {bidirectional} from 'graphology-shortest-path/unweighted';
import {dfsFromNode} from "graphology-traversal/dfs";

window.graphFuncs = {bidirectional, dfsFromNode};

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

const graphReducer = (gc, action) => {
  if (!(action && action.type)) return gc;
  // let { graph, nodes } = gc;
  let graph;
  switch (action.type) {
    case 'CREATE':
      gc = new GraphContainer(action.payload);
      break;
    case 'TOGGLE_NODE_EXPANDED':
      gc.toggleNodeExpanded(action.payload.nodeId);
      gc = new GraphContainer(null, gc);
      break;
    case 'TOGGLE_OPTION':
      const type = action.payload.type;
      gc.toggleOption(type);
      gc = new GraphContainer(null, gc);
      break;
    case 'TOGGLE_EXPAND_ALL':
      gc.options.expandAll = !gc.options.expandAll;
      Object.values(gc.nodes).forEach(n => {if (n.hasChildren) n.expanded = gc.options.expandAll;});
      gc = new GraphContainer(null, gc);
      break;
    default:
      throw new Error(`unexpected action.type ${action.type}`);
  }
  return gc;
};

export class GraphContainer {
  constructor(graphData, cloneThis) {
    if (cloneThis) {
      // shallow copy cloneThis's properties to this
      Object.assign(this, cloneThis);
      this.getDisplayedRows();
      window.graphW = this; // for debugging
      return;
    }
    window.graphW = this; // for debugging
    // this.gd holds inputs -- except
    // this.gd.specialConcepts.allButFirstOccurrence which is added later
    //    it's also a list of paths; all the other specialConcepts are lists of concept_ids
    this.gd = graphData;  // concepts, specialConcepts, csmi, edges, concept_ids, filled_gaps,
                          // missing_from_graph, hidden_by_vocab, nonstandard_concepts_hidden
    this.gd.specialConcepts.allButFirstOccurrence = [];
    [this.graph, this.nodes] = makeGraph(this.gd.edges, this.gd.concepts);

    this.roots = this.graph.nodes().filter(n => !this.graph.inDegree(n));
    this.leaves = this.graph.nodes().filter(n => !this.graph.outDegree(n));
    this.unlinkedConcepts = intersection(this.roots, this.leaves);
    // this.partiallyExpandedNodes = new Set();  // from path version of show though collapsed
    this.displayedRows = [];
    this.displayedNodeRows = new StringKeyMap();    // map from nodeId to row (node copy)
    this.showThoughCollapsed = new StringSet();
    this.hideThoughExpanded = new StringSet();

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
    this.roots = this.graph.nodes().filter(n => !this.graph.inDegree(n));
    this.leaves = this.graph.nodes().filter(n => !this.graph.outDegree(n));

    this.#computeAttributes();

    this.options = {
      specialConceptTreatment: {},
    };
    this.setStatsOptions();
    this.getDisplayedRows();
  }
  toggleNodeExpanded(nodeId) {
    const node = this.nodes[nodeId];
    node.expanded =!node.expanded;

    /*  if switching back to other show though collapsed method, uncomment the following
    if (node.not_a_concept && node.parent) {
      let parent = this.nodes[node.parent];
      delete parent.partialExpansion;
    } else {
      dfsFromNode(this.graph, nodeId, (descendantId, attr, depth) => {
        let descendant = this.nodes[descendantId];
        delete descendant.partialExpansion;
      }, {mode: 'outbound'});
    }
     */
  }
  toggleOption(type) {
    let gc = this;
    gc.options.specialConceptTreatment[type] = ! gc.options.specialConceptTreatment[type];
    gc.statsOptions[type].specialTreatment = gc.options.specialConceptTreatment[type];
  }

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

  getDisplayedRows(props) {
    // const {/*collapsedDescendantPaths, */ collapsePaths, hideZeroCounts, hideRxNormExtension, nested } = hierarchySettings;
    Object.values(this.nodes).forEach(node => {delete node.childRows});
    this.displayedRows.splice(0, this.displayedRows.length); // keeping same array ref to help with debugging using graphW
    this.displayedNodeRows.clear();
    this.gd.specialConcepts.allButFirstOccurrence = [];

    // add root nodes and their children if expanded to displayed
    let rootRows = [];
    for (let nodeId of sortBy(this.roots, this.sortFunc)) {
      let rootRow = this.addNodeToDisplayed(nodeId, []);
      rootRows.push(rootRow);
    }

    this.arrangeDisplayRows(rootRows);
    const displayedRowsBeforeSpecial = [...this.displayedRows];

    this.showThoughCollapsed.clear();
    this.hideThoughExpanded.clear();
    for (let type in this.options.specialConceptTreatment) {
      if (this.statsOptions[type].specialTreatmentRule === 'show though collapsed' && this.options.specialConceptTreatment[type]) {
        for (let id of this.gd.specialConcepts[type] || []) {
          this.showThoughCollapsed.add(id);
        }
      }
    }

    // if there are showThoughCollapsed nodes to show, find each one's
    //  nearest parents add them at those path locations
    let shown = new StringSet();
    const insertShowThoughCollapsed = (path) => {
      // path starts with the nodeIdToShow and recurses up, prepending parents
      const nodeIdToShow = path[path.length - 1]; // remains the same through recursion
      if (shown.has(nodeIdToShow)) return; // already displayed
      if (this.displayedNodeRows.has(nodeIdToShow)) {
        throw new Error(`nodeToShow ${nodeIdToShow} is already displayed`);
      }
      // so, only one nodeIdToShow, but separate nodeToShow copies for each path
      let nodeToShowRows = [];
      let parents = this.graph.inNeighbors(path[0]);
      for (let parentId of parents) {
        if (this.showThoughCollapsed.has(parentId)) {
          // if the parent is also a showThoughCollapsed node, do it first
          insertShowThoughCollapsed([parentId, ...(path.slice(0, -1))]);
        }
        let parentNode = this.nodes[parentId];
        if (this.displayedNodeRows.has(parentId)) {  // parent is already displayed
          if (parentNode.expanded) {
            throw new Error(`parent ${parentId} is expanded; we shouldn't be here`);
          }
          parentNode.childRows = parentNode.childRows || [];

          // put the nodeIdToShow below its paths
          for (let parentRow of this.displayedNodeRows.get(parentId)) {
            let nodeToShowRow = {...this.nodes[nodeIdToShow]};
            nodeToShowRow.depth = parentRow.depth + 1;
            nodeToShowRow.rowPath = [...parentRow.rowPath, nodeIdToShow]; // straight from visible ancestor to nodeToShowRow
            nodeToShowRow.pathFromDisplayedNode = path.slice(0, -1);  // intervening path between them
            nodeToShowRows.push(nodeToShowRow);
            parentNode.childRows.push(nodeToShowRow); // add to parent's childRows
            parentRow.childRows = parentNode.childRows;
          }
        } else {
          insertShowThoughCollapsed([parentId, ...path]);
          return;
        }
      }
      if (this.displayedNodeRows.has(nodeIdToShow)) {
        throw new Error(`nodeToShow ${nodeIdToShow} is already displayed`);
      }
      this.displayedNodeRows.set(nodeIdToShow, []);
      nodeToShowRows.forEach((nodeToShowRow, i) => {
        this.displayedNodeRows.get(nodeIdToShow).push(nodeToShowRow);
      });
      shown.add(nodeIdToShow);
    }
    this.showThoughCollapsed.forEach(nodeIdToShow => {
      if (this.displayedNodeRows.has(nodeIdToShow)) return; // already displayed
      this.showThoughCollapsed.add(nodeIdToShow);
      insertShowThoughCollapsed([nodeIdToShow]);
    });


    this.arrangeDisplayRows(rootRows);
    // this.displayedRows.forEach(row => { row.levelsBelow = this.sortFunc(row) }); // for debugging
    // this.gd.specialConcepts.allButFirstOccurrence = this.displayedRows.filter(row => row.nodeOccurrence > 0).map(d => d.rowPath);
    // this.statsOptions.allButFirstOccurrence

    for (let type in this.options.specialConceptTreatment) {
      if (this.statsOptions[type].specialTreatmentRule === 'hide though expanded' && this.options.specialConceptTreatment[type]) {
        // gather all the hideThoughExpanded ids
        this.gd.specialConcepts[type].forEach(id => {
          this.hideThoughExpanded.add(id);
        })
      }
    }
    for (let type in this.options.specialConceptTreatment) {
      if (this.statsOptions[type].specialTreatmentRule === 'hide though expanded' && this.options.specialConceptTreatment[type]) {
        let [special, displayed] = [
            this.gd.specialConcepts[type],
            this.displayedRows.map(d => d.concept_id)];
        for (let id of setOp('intersection', special, displayed)) {
          let nodeToHide = this.nodes[id];
          if (nodeToHide.expanded) {
            if (!some(nodeToHide.childIds, id => this.displayedNodeRows.has(id) && !this.hideThoughExpanded.has(id))) {
              // don't hide if it has children that should be shown
              // that is, if it's already displayed and not hidden
              this.hideThoughExpanded.delete(id);
            }
          }
          /* if (!nodeToHide.expanded) {
            // this.hideThoughExpanded.add(id);
            this.displayedNodeRows.delete(id); // remove from displayedNodeRows map
          } */
        }
      }
    }
    this.hideThoughExpanded.forEach(id => {
      this.displayedNodeRows.delete(id); // remove from displayedNodeRows map
    });

    this.arrangeDisplayRows(rootRows);
    return this.displayedRows;
  }

  addNodeToDisplayed(nodeId, rowPath, depth = 0) {
    /* adds the node to the list of displayed nodes
        if it is set to be expanded, recurse and add its children to the list */
    let node = this.nodes[nodeId];
    let row = {...node, depth};
    row.rowPath = [...rowPath, nodeId];

    if (this.displayedNodeRows.has(nodeId)) {
      let rowsForThisNode = this.displayedNodeRows.get(nodeId);
      rowsForThisNode.push(row);
    } else {
      this.displayedNodeRows.set(nodeId, [row]);
    }

    // this.displayedRows.push(row);

    if (row.expanded) {
      // if it's expanded, it must have children
      row.childRows = row.childRows = sortBy(node.childIds, this.sortFunc).map(childId => {
        const childRow = this.addNodeToDisplayed(childId, row.rowPath, depth + 1); // Recurse
        return childRow;
      });
    }
    return row;
  }
  arrangeDisplayRows(rows) {
    this.displayedRows.splice(0, this.displayedRows.length);
    let nodeOccurrences = {};
    const f = (rows) => {
      for (let row of sortBy(rows, this.sortFunc)) {
        nodeOccurrences[row.concept_id] = nodeOccurrences[row.concept_id] ?? -1;
        row.nodeOccurrence = ++nodeOccurrences[row.concept_id];
        if (this.hideThoughExpanded && this.hideThoughExpanded.has(row.concept_id)) continue;
        this.displayedRows.push(row);
        // const node = this.nodes[row.concept_id];
        if (row.childRows) {
          f(row.childRows);
        }
      }
    }
    f(rows);
  }

  sortFunc = (d => {
    let n = typeof(d) === 'object' ? d : this.nodes[d];
    return n.not_a_concept
        ? Infinity
        : (
            (n.pathFromDisplayedNode && !n.hasChildren
                ? -(10**9)
                : 0
            ) + (n.pathFromDisplayedNode || []).length * 10**6 - n.drc);
    let statusRank = n.isItem && 3 + n.added && 2 + n.removed && 1 || 0;
    // return - (n.drc || n.descendantCount || n.levelsBelow || n.status ? 1 : 0);
    return - (n.levelsBelow || n.descendantCount || n.status ? 1 : 0);
  })

  #computeAttributes() {
    const graph = this.graph;
    let nodes = this.nodes;
    function computeAttributesFunc(nodeId, level) {
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

      // if (levelsBelow > 0) {
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

  setStatsOptions() {
    const displayedConcepts = this.displayedRows || []; // first time through, don't have displayed rows yet
    const displayedCids = displayedConcepts.map(r => r.concept_id);
    let displayOrder = 0;
    let rows = {
      displayedRows: {
        name: "Visible rows", displayOrder: displayOrder++,
        value: displayedConcepts.length,
      },
      concepts: {
        name: "Concepts", displayOrder: displayOrder++,
        value: this.gd.concept_ids.length,
        hiddenConceptCnt: setOp('difference', this.gd.concept_ids, displayedCids).length,
        displayedConceptCnt: setOp('intersection', this.gd.concept_ids, displayedCids).length,
        specialTreatmentRule: 'expand all',
        specialTreatmentDefault: false,
      },
      definitionConcepts: {
        name: "Definition concepts", displayOrder: displayOrder++,
        value: this.gd.specialConcepts.definitionConcepts.length,
        hiddenConceptCnt: setOp('difference', this.gd.specialConcepts.definitionConcepts, displayedCids).length,
        specialTreatmentDefault: false,
        specialTreatmentRule: 'show though collapsed',
      },
      expansionConcepts: {
        name: "Expansion concepts", displayOrder: displayOrder++,
        value: this.gd.specialConcepts.expansionConcepts.length,
        // value: uniq(flatten(Object.values(this.gd.csmi).map(Object.values)) .filter(c => c.csm).map(c => c.concept_id)).length,
        displayedConceptCnt: setOp('intersection', this.gd.specialConcepts.expansionConcepts, displayedCids).length,
        // hiddenConceptCnt: setOp('difference', this.gd.concept_ids, displayedCids).length,
        // specialTreatmentDefault: false,
        // specialTreatmentRule: 'hide though expanded',
      },
      added: {
        name: "Added", displayOrder: displayOrder++,
        value: get(this.gd.specialConcepts, 'added.length', undefined),
        hiddenConceptCnt: setOp('difference', this.gd.specialConcepts.added, displayedCids).length,
        specialTreatmentDefault: false,
        specialTreatmentRule: 'show though collapsed',
      },
      removed: {
        name: "Removed", displayOrder: displayOrder++,
        value: get(this.gd.specialConcepts, 'removed.length', undefined),
        hiddenConceptCnt: setOp('difference', this.gd.specialConcepts.removed, displayedCids).length,
        specialTreatmentDefault: false,
        specialTreatmentRule: 'show though collapsed',
      },
      standard: {
        name: "Standard concepts", displayOrder: displayOrder++,
        value: this.gd.concepts.filter(c => c.standard_concept === 'S').length,
      },
      classification: {
        name: "Classification concepts", displayOrder: displayOrder++,
        value: this.gd.concepts.filter(c => c.standard_concept === 'C').length,
      },
      nonStandard: {
        name: "Non-standard", displayOrder: displayOrder++,
        value: this.gd.specialConcepts.nonStandard.length,
        displayedConceptCnt: setOp('intersection', this.gd.specialConcepts.nonStandard, displayedCids).length,
        hiddenConceptCnt:  setOp('intersection', this.gd.specialConcepts.nonStandard, this.hideThoughExpanded).length,
        specialTreatmentDefault: false,
        specialTreatmentRule: 'hide though expanded',
      },
      zeroRecord: {
        name: "Zero records / patients", displayOrder: displayOrder++,
        value: this.gd.specialConcepts.zeroRecord.length,
        displayedConceptCnt: setOp('intersection', this.gd.specialConcepts.zeroRecord, displayedCids).length,
        hiddenConceptCnt: setOp('intersection', this.gd.specialConcepts.zeroRecord, [...(this.hideThoughExpanded || [])]).length,
        specialTreatmentDefault: false,
        specialTreatmentRule: 'hide though expanded',
      },
      allButFirstOccurrence: {
        name: "All but first occurrence", displayOrder: displayOrder++,
        value: this.gd.specialConcepts.allButFirstOccurrence.length,
        displayedConceptCnt: this.options.specialConceptTreatment.allButFirstOccurrence
            ? 0
            : this.gd.specialConcepts.allButFirstOccurrence.length,
        hiddenConceptCnt: this.options.specialConceptTreatment.allButFirstOccurrence
            ? this.gd.specialConcepts.allButFirstOccurrence.length
            : 0,
        /* special_v_displayed: () => {
          let special = this.gd.specialConcepts.allButFirstOccurrence.map(p => p.join('/'));
          let displayed = flatten(Object.values(this.displayedNodePaths)
                                      .map(paths => paths.map(path => path.join('/'))))
          return [special, displayed];
        }, */
        specialTreatmentDefault: false,
        specialTreatmentRule: 'hide though expanded',
      },
    }
    for (let type in rows) {
      let row = {...get(this, ['statsOptions', type], {}), ...rows[type]};  // don't lose stuff previously set
      if (typeof(row.value) === 'undefined') {  // don't show rows that don't represent any concepts
        delete rows[type];
        continue;
      }
      row.type = type;
      if (isEmpty(this.statsOptions) && typeof(row.specialTreatmentDefault) !== 'undefined') {
        // set specialTreatment to default only the first time through
        row.specialTreatment = row.specialTreatmentDefault;
      }
      // TODO: figure out if row.specialTreatment and
      //       this.options.specialConceptTreatment are redundant
      //       OR, maybe they are but saving it in this.options is good
      //       for saving the options
      // TODO: implement saving and reloading the options
      if (type in this.gd.specialConcepts) {
        // don't bother setting the option if there are no concepts/items of this type
        this.options.specialConceptTreatment[type] = row.specialTreatment;
      }
      rows[type] = row;
    }
    this.statsOptions = rows;
  };
  getStatsOptions() {
    return sortBy(this.statsOptions, d => d.displayOrder);
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
}

const GraphContext = createContext(null);

export const GraphProvider = ({ children }) => {
  const [gc, gcDispatch] = useReducer(graphReducer, {});

  return (
    <GraphContext.Provider value={{ gc, gcDispatch }}>
      {children}
    </GraphContext.Provider>
  );
};

export const useGraphContainer = () => {
  const context = useContext(GraphContext);
  if (context === undefined) {
    throw new Error('useGraphContainer must be used within a GraphProvider');
  }
  return context;
};

function setOp(op, setA, setB) {
  /*
   * setOp(op, setA, setB)
   *   - op: one of union, difference, intersection
   *   - setA, setB: can be an array, Set, or Iterator (like you get from map.keys())
   *   - returns: a new set of items based on ==, so integers are equivalent to their string representations
   */
  const f = ({
    union: unionWith,
    difference: differenceWith,
    intersection: intersectionWith
  })[op];
  if (setA instanceof Set || setA instanceof Iterator) setA = [...setA];
  if (setB instanceof Set || setB instanceof Iterator) setB = [...setB];
  return f(setA, setB, (itemA, itemB) => itemA == itemB);
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


/* use like:
  const { {graph, nodes}, gcDispatch } = useGraphContainer();
  const toggleNodeAttribute = (nodeId) => {
    gcDispatch({
      type: 'TOGGLE_NODE_ATTRIBUTE',
      payload: { nodeId },
    });
  };
*/

// experiment, from https://chat.openai.com/share/8e817f4d-0581-4b07-aefe-acd5e7110de6
/*
function prepareDataForRendering(graph, startNodeId) {
  let result = [];
  let stack = [{ nodeId: startNodeId, depth: 0 }];
  let visited = new Set([startNodeId]);

  while (stack.length > 0) {
    const { nodeId, depth } = stack.pop();
    const nodeData = graph.getNodeAttributes(nodeId);

    result.push({
                  id: nodeId,
                  name: nodeData.label || nodeId, // Assuming nodes have a 'label' attribute
                  otherData: nodeData.otherData, // Add other node attributes as needed
                  depth,
                  visible: true, // Initially, all nodes are visible
                  hasChildren: graph.outDegree(nodeId) > 0,
                  expanded: false
                });

    // Reverse to maintain the correct order after pushing to stack
    const neighbors = [...graph.neighbors(nodeId)].reverse();
    neighbors.forEach(neighbor => {
      if (!visited.has(neighbor)) {
        visited.add(neighbor);
        stack.push({ nodeId: neighbor, depth: depth + 1 });
      }
    });
  }

  return result;
}
*/
/*

Below is code for another way of showing rows even when parents are collapsed.
Instead of showing the path to the concept from the nearest expanded parent,
it expands up to the nearest expanded and collapses all the siblings that
aren't being specially shown.
TODO: determine if this way is better now with the ability to hide repeated rows

addNodeToVisibleOtherVersion(nodeId, displayedRows, depth = 0) {
  const node = {...this.nodes[nodeId], depth}; // is this necessary?
  // const node = this.nodes[nodeId]; // TODO: try this instead when have a chance to test
  // node.depth = depth;

  displayedRows.push(node);
  if (node.expanded) {
    node.children.forEach(childId => {
      this.addNodeToVisible(childId, displayedRows, depth + 1); // Recurse
    });
  }
}
hideOtherNodesOtherVersion(partialExpansions) {
  for (let parentId in partialExpansions) {
    let parent = this.nodes[parentId];
    parent.expanded = true;
    let others = setOp('difference', parent.children, partialExpansions[parentId]);
    let othersId = `${parentId}-unshown`;
    let othersRow = {
      concept_id: othersId,
      parent: parentId,
      concept_name: `${others.length} concepts not expanded`,
      vocabulary_id: "--",
      standard_concept: "",
      not_a_concept: true,
      depth: parent.depth + 1,
      levelsBelow: 1,
      hasChildren: true,
      children: others,
      childCount: others.length,
      descendants: others,
      descendantCount: others.length,
      drc: sum(others.map(d => this.nodes[d].total_cnt || 0)), // Compute descendant counts
    };
    this.graph.mergeNode(othersId);
    this.graph.mergeDirectedEdge(parentId, othersId);
    this.nodes[othersId] = othersRow;
    console.log(`collapsing ${others.join(',')} under ${parentId}`);
    for (let other of others) {
      this.graph.mergeDirectedEdge(othersId, other);
      this.graph.dropEdge(parentId, other);
      parent.children = setOp('difference', parent.children, [other]);
    }
    parent.children.push(othersId);
  }
}
getPartialExpansionsOtherVersion(nodesToShow, partialExpansions) {
  // For show though collapsed, partially expand the parents of the nodes to show
  // This function adds each node to show to the partialExpansions set for its parents
  for (let showId of nodesToShow) {
    if (!this.graph.hasNode(showId)) continue;
    let parentIds = this.graph.inNeighbors(showId);
    if (isEmpty(parentIds)) continue;
    for (let parentId of parentIds) {
      if (showId == parentId) return; // can't recall why this is necessary -- is it?
      let parent = this.nodes[parentId];
      if (!parent.expanded) {
        partialExpansions[parentId] = partialExpansions[parentId] || new Set();
        partialExpansions[parentId].add(showId);
      }
    }
    // recurse (upwards) to partially expand parents of parents
    this.getPartialExpansions(parentIds, partialExpansions);
  }
}
getVisibleRowsOtherVersion(props) {
  // TODO: need to treat things to hide differently from things to always show.

  let displayedRows = [];

  let partialExpansions = {};
  for (let type in this.options.specialConceptTreatment) {
    if (this.statsOptions[type].specialTreatmentRule === 'show though collapsed' && this.options.specialConceptTreatment[type]) {
      this.getPartialExpansions(this.specialConcepts[type] || [], partialExpansions);
    }
  }
  console.log(partialExpansions);
  this.hideOtherNodes(partialExpansions);

  // const {/*collapsedDescendantPaths, * / collapsePaths, hideZeroCounts, hideRxNormExtension, nested } = hierarchySettings;
  for (let rootId of sortBy(this.roots, this.sortFunc)) {
    this.addNodeToVisible(rootId, displayedRows);
  }

  let hideThoughExpanded = new Set();
  for (let type in this.options.specialConceptTreatment) {
    if (this.statsOptions[type].specialTreatmentRule === 'hide though expanded' && this.options.specialConceptTreatment[type]) {
      for (let id of setOp('intersection', this.specialConcepts[type], displayedRows.map(d => d.concept_id))) {
        hideThoughExpanded.add(id);
      }
    }
  }
  displayedRows = displayedRows.filter(row => ! hideThoughExpanded.has(row.concept_id));

  this.hideThoughExpanded = hideThoughExpanded;
  return this.v'isibleRows = displayedRows;
}
showThoughCollapsed(nodeId) {
  dfsFromNode(this.graph, nodeId, (ancestorId, attr, depth) => {
    let ancestor = this.nodes[ancestorId];
    if (!ancestor.expanded) {
      if (!ancestor.partialExpansion) {
        ancestor.partialExpansion = [];
      }
      ancestor.partialExpansion.push(nodeId);
    }
  }, {mode: 'inbound'});
}
*/