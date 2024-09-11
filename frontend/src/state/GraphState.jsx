import React, {createContext, useContext, useReducer, useEffect} from "react";
import {cloneDeep, flatten, get, intersection, isEmpty, some, sortBy, sum, uniq, set} from "lodash";
import Graph from "graphology";
import {bidirectional} from 'graphology-shortest-path/unweighted';
import {dfsFromNode} from "graphology-traversal/dfs";
import {setOp} from "../utils";

window.graphFuncs = {bidirectional, dfsFromNode};

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
    this.gd = graphData;  // concepts, specialConcepts, csmi, edges, concept_ids, filled_gaps,
                          // missing_from_graph, hidden_by_vocab, nonstandard_concepts_hidden

    // this.gd holds inputs -- except this.gd.specialConcepts.allButFirstOccurrence which is added later
    //    it's also a list of paths; all the other specialConcepts are lists of concept_ids
    set(this, 'gd.specialConcepts.allButFirstOccurrence', []);
    this.displayedRows = [];  // array of displayed rows...individual node could occur in multiple places
    this.displayedNodeRows = new StringKeyMap();    // map from nodeId to row (node copy)
    this.showThoughCollapsed = new StringSet();
    this.hideThoughExpanded = new StringSet();

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

  getDisplayedRows(graphOptions) {
    // const {/*collapsedDescendantPaths, */ collapsePaths, hideZeroCounts, hideRxNormExtension, nested } = hierarchySettings;

    // delete childRows for every node because some option might have changed and we need
    //  to recalculate the children
    Object.values(this.nodes).forEach(node => {
      delete node.childRows;
    });
    this.displayedRows.splice(0, this.displayedRows.length); // keeping same array ref to help with debugging using graphW
    this.displayedNodeRows.clear();
    this.gd.specialConcepts.allButFirstOccurrence = [];

    // add root nodes and their children if expanded to displayed
    let rootRows = [];
    for (let nodeId of sortBy(this.roots, this.sortFunc)) {
      let rootRow = this.addNodeToDisplayed(nodeId, graphOptions, []);
      rootRows.push(rootRow);
    }

    this.arrangeDisplayRows(rootRows);  // first time
    const displayedRowsBeforeSpecial = [...this.displayedRows];

    this.showThoughCollapsed.clear();
    this.hideThoughExpanded.clear();

    if (!graphOptions.expandAll) {
      // if there are showThoughCollapsed nodes to show, find each one's
      //  nearest parents add them at those path locations

      for (let type in graphOptions.specialConceptTreatment) {
        if (this.graphDisplayConfig[type].specialTreatmentRule === 'show though collapsed' &&
            graphOptions.specialConceptTreatment[type]) {
          for (let id of this.gd.specialConcepts[type] || []) {
            this.showThoughCollapsed.add(id);
          }
        }
      }
      let shown = new StringSet();
      const insertShowThoughCollapsed = (path) => {
        // path starts with the nodeIdToShow and recurses up, prepending parents
        const nodeIdToShow = path[path.length - 1]; // remains the same through recursion
        if (shown.has(nodeIdToShow)) return; // already displayed
        if (this.displayedNodeRows.has(nodeIdToShow)) {
          return;
          // throw new Error(`nodeToShow ${nodeIdToShow} is already displayed`);
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
      };
      this.showThoughCollapsed.forEach(nodeIdToShow => {
        if (this.displayedNodeRows.has(nodeIdToShow)) return; // already displayed
        this.showThoughCollapsed.add(nodeIdToShow);
        insertShowThoughCollapsed([nodeIdToShow]);
      });
    }


    this.arrangeDisplayRows(rootRows);  // second time
    // this.displayedRows.forEach(row => { row.levelsBelow = this.sortFunc(row) }); // for debugging
    // debugger;
    // TODO: FIX allButFirstOccurrence -- needs to hide paths, not just concept_ids, it's broken
    this.gd.specialConcepts.allButFirstOccurrence = this.displayedRows.filter(row => row.nodeOccurrence > 0).map(d => d.rowPath);
    // this.graphDisplayConfig.allButFirstOccurrence

    for (let type in graphOptions.specialConceptTreatment) {
      if (this.graphDisplayConfig[type].specialTreatmentRule === 'hide though expanded' && graphOptions.specialConceptTreatment[type]) {
        // gather all the hideThoughExpanded ids
        this.gd.specialConcepts[type].forEach(id => {
          this.hideThoughExpanded.add(id);
        })
      }
    }
    for (let type in graphOptions.specialConceptTreatment) {
      if (this.graphDisplayConfig[type].specialTreatmentRule === 'hide though expanded' && graphOptions.specialConceptTreatment[type]) {
        let [special, displayed] = [
            this.gd.specialConcepts[type],
            this.displayedRows.map(d => d.concept_id)];
        for (let id of setOp('intersection', special, displayed)) {
          let nodeToHide = this.nodes[id];
          if (nodeToHide.expanded) {  //
            // does this get used anymore? we shouldn't be using expanded property now
            debugger;
            // TODO:  make sure this still works without using node.expanded
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

    this.arrangeDisplayRows(rootRows);  // third time
    return this.displayedRows;
  }

  addNodeToDisplayed(nodeId, graphOptions, rowPath, depth = 0) {
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

    if ((row.expanded || graphOptions.expandAll ||  // todo: get rid of row.expanded property -- not using anymore, right?
        graphOptions.specificNodesExpanded.find(d => d == row.concept_id) &&
        ! graphOptions.specificNodesCollapsed.find(d => d == row.concept_id))
    ) {
        // now with tracking specificNodesExpanded/Collapsed, I'm not sure if we
        //  still need to check row.expanded
      // if it's expanded, it must have children
      row.childRows = row.childRows = sortBy(node.childIds, this.sortFunc).map(childId => {
        const childRow = this.addNodeToDisplayed(childId, graphOptions, row.rowPath, depth + 1); // Recurse
        return childRow;
      });
    }
    return row;
  }
  arrangeDisplayRows(rootRows) {
    // recursively traverse rootRows and add child rows to display according to all the rules;
    //  I can't remember why this gets called _three_ times
    this.displayedRows.splice(0, this.displayedRows.length); // empty out this.displayedRows and create again
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
    };
    f(rootRows);
  }

  sortFunc = (d => {
    // used to sort each level of the comparison table.
    // todo: allow this to be changed by user
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

  setGraphDisplayConfig(graphOptions) {
    // these are all options that appear in Show Stats/Options

    const displayedConcepts = this.displayedRows || []; // first time through, don't have displayed rows yet
    const displayedConceptIds = displayedConcepts.map(r => r.concept_id);
    let displayOrder = 0;
    let brandNew = isEmpty(graphOptions);
    if (brandNew) {
      graphOptions = {
        specialConceptTreatment: {},
        expandAll: false,
        nested: true,
      };
    }
    let displayOptions = {
      displayedRows: {
        name: "Visible rows", displayOrder: displayOrder++,
        value: displayedConcepts.length,
      },
      concepts: {
        name: "Concepts", displayOrder: displayOrder++,
        value: this.gd.concept_ids.length,
        hiddenConceptCnt: setOp('difference', this.gd.concept_ids, displayedConceptIds).length,
        displayedConceptCnt: setOp('intersection', this.gd.concept_ids, displayedConceptIds).length,
        specialTreatmentRule: 'expandAll',
        specialTreatmentDefault: false,
      },
      addedCids: {
        name: "Individually added concept_ids", displayOrder: displayOrder++,
        value: this.gd.specialConcepts.addedCids.length,
        hiddenConceptCnt: setOp('difference', this.gd.specialConcepts.addedCids, displayedConceptIds).length,
        displayedConceptCnt: setOp('intersection', this.gd.specialConcepts.addedCids, displayedConceptIds).length,
        specialTreatmentDefault: true,
        specialTreatmentRule: 'show though collapsed',
      },
      definitionConcepts: {
        name: "Definition concepts", displayOrder: displayOrder++,
        value: this.gd.specialConcepts.definitionConcepts.length,
        hiddenConceptCnt: setOp('difference', this.gd.specialConcepts.definitionConcepts, displayedConceptIds).length,
        specialTreatmentDefault: false,
        specialTreatmentRule: 'show though collapsed',
      },
      expansionConcepts: {
        name: "Expansion concepts", displayOrder: displayOrder++,
        value: this.gd.specialConcepts.expansionConcepts.length,
        // value: uniq(flatten(Object.values(this.gd.csmi).map(Object.values)) .filter(c => c.csm).map(c => c.concept_id)).length,
        displayedConceptCnt: setOp('intersection', this.gd.specialConcepts.expansionConcepts, displayedConceptIds).length,
        hiddenConceptCnt: setOp('difference', this.gd.concept_ids, displayedConceptIds).length,
        specialTreatmentDefault: false,
        specialTreatmentRule: 'hide though expanded',
      },
      added: {
        name: "Added to compared", displayOrder: displayOrder++,
        value: get(this.gd.specialConcepts, 'added.length', undefined),
        hiddenConceptCnt: setOp('difference', this.gd.specialConcepts.added, displayedConceptIds).length,
        specialTreatmentDefault: false,
        specialTreatmentRule: 'show though collapsed',
      },
      removed: {
        name: "Removed from compared", displayOrder: displayOrder++,
        value: get(this.gd.specialConcepts, 'removed.length', undefined),
        hiddenConceptCnt: setOp('difference', this.gd.specialConcepts.removed, displayedConceptIds).length,
        specialTreatmentDefault: false,
        specialTreatmentRule: 'show though collapsed',
      },
      standard: {
        name: "Standard concepts", displayOrder: displayOrder++,
        value: this.gd.concepts.filter(c => c.standard_concept === 'S').length,
        displayedConceptCnt: setOp('intersection', this.gd.concepts.filter(c => c.standard_concept === 'S'), displayedConceptIds).length,
      },
      classification: {
        name: "Classification concepts", displayOrder: displayOrder++,
        value: this.gd.concepts.filter(c => c.standard_concept === 'C').length,
      },
      nonStandard: {
        name: "Non-standard", displayOrder: displayOrder++,
        value: this.gd.specialConcepts.nonStandard.length,
        displayedConceptCnt: setOp('intersection', this.gd.specialConcepts.nonStandard, displayedConceptIds).length,
        hiddenConceptCnt:  setOp('intersection', this.gd.specialConcepts.nonStandard, this.hideThoughExpanded).length,
        specialTreatmentDefault: false,
        specialTreatmentRule: 'hide though expanded',
      },
      zeroRecord: {
        name: "Zero records / patients", displayOrder: displayOrder++,
        value: this.gd.specialConcepts.zeroRecord.length,
        displayedConceptCnt: setOp('intersection', this.gd.specialConcepts.zeroRecord, displayedConceptIds).length,
        hiddenConceptCnt: setOp('intersection', this.gd.specialConcepts.zeroRecord, [...(this.hideThoughExpanded || [])]).length,
        specialTreatmentDefault: false,
        specialTreatmentRule: 'hide though expanded',
      },
      allButFirstOccurrence: {
        name: "All but first occurrence", displayOrder: displayOrder++,
        value: this.gd.specialConcepts.allButFirstOccurrence.length,
        displayedConceptCnt: get(graphOptions, 'specialConceptTreatment.allButFirstOccurrence', true)
            ? 0
            : this.gd.specialConcepts.allButFirstOccurrence.length,
        hiddenConceptCnt: get(graphOptions, 'specialConceptTreatment.allButFirstOccurrence', true)
            ? this.gd.specialConcepts.allButFirstOccurrence.length
            : 0,
        /* special_v_displayed: () => {
          let special = this.gd.specialConcepts.allButFirstOccurrence.map(p => p.join('/'));
          let displayed = flatten(Object.values(this.displayedNodePaths)
                                      .map(paths => paths.map(path => path.join('/'))))
          return [special, displayed];
        }, */
        specialTreatmentDefault: true,
        specialTreatmentRule: 'hide though expanded',
      },
    }
    for (let type in displayOptions) {
      let displayOption = {...get(this, ['graphDisplayConfig', type], {}), ...displayOptions[type]};  // don't lose stuff previously set
      if (typeof(displayOption.value) === 'undefined') {  // don't show displayOptions that don't represent any concepts
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
    return graphOptions;
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
