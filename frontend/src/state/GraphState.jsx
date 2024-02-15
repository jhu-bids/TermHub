import React, {createContext, useContext, useReducer, useState} from "react";
import {get, once, sum, sortBy, uniq, flatten, intersection, difference, differenceWith, isEmpty} from "lodash";
import Graph from "graphology";
import {bidirectional} from 'graphology-shortest-path/unweighted';

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
      gc.options.specialConceptsHidden[type] = ! gc.options.specialConceptsHidden[type];
      gc.statsOptionsRows[type].isHidden = gc.options.specialConceptsHidden[type];
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
      this.getVisibleRows();
      return;
    }
    let {concepts, specialConcepts, edges, concept_ids, filled_gaps, missing_from_graph,
      hidden_by_vocab, nonstandard_concepts_hidden} = graphData;
    Object.assign(this, {concept_ids, filled_gaps, missing_from_graph,
      hidden_by_vocab, nonstandard_concepts_hidden});
    let graphConceptIds = uniq(flatten(edges));
    // this.graphConcepts = concepts.filter(c => graphConceptIds.includes(c.concept_id));
    this.#makeGraph(edges, concepts);  // sets this.graph and this.nodes

    this.roots = this.graph.nodes().filter(n => !this.graph.inDegree(n));
    this.leaves = this.graph.nodes().filter(n => !this.graph.outDegree(n));
    this.unlinkedConcepts = intersection(this.roots, this.leaves);

    let unlinkedConceptsParent = {
      "concept_id": 'unlinked',
      "concept_name": "Concepts in set but not linked to others",
      "vocabulary_id": "--",
      "standard_concept": "",
      "total_cnt": 0,
      "distinct_person_cnt": "0",
      "status": ""
    };
    this.graph.addNode('unlinked');
    this.nodes['unlinked'] = unlinkedConceptsParent;
    for (let c of this.unlinkedConcepts) {
      this.graph.addDirectedEdge('unlinked', c);
    }
    this.roots = this.graph.nodes().filter(n => !this.graph.inDegree(n));
    this.leaves = this.graph.nodes().filter(n => !this.graph.outDegree(n));

    this.#computeAttributes();
    this.concepts = concepts;
    this.specialConcepts = specialConcepts;

    this.options = {
      specialConceptsHidden: {},
    };
    this.specialConceptTypeCnt = 0;
    for (let type in this.specialConcepts) {
      this.options.specialConceptsHidden[type] = true;
      this.specialConceptTypeCnt += 1;
      // should include expressionItems and, optionally, added and removed
    }
    this.getVisibleRows();
  }
  toggleNodeExpanded(nodeId) {
    const node = this.nodes[nodeId];
    this.nodes = {...this.nodes, [nodeId]: {...node, expanded:!node.expanded}};
  }
  setStatsOptionsRows({concepts, concept_ids, csmi,}) {
    const visibleCids = this.visibleRows.map(r => r.concept_id);
    let displayOrder = 0;
    let rows = {
      visibleRows: {
        name: "Visible rows", displayOrder: displayOrder++,
        value: this.visibleRows.length,
      },
      concepts: {
        name: "Concepts", displayOrder: displayOrder++,
        value: concept_ids.length,
        hiddenConceptCnt: cidDiff(concept_ids, visibleCids),
      },
      expressionItems: {
        name: "Definition concepts", displayOrder: displayOrder++,
        value: this.specialConcepts.expressionItems.length,
        hiddenConceptCnt: cidDiff(this.specialConcepts.expressionItems, visibleCids),
        hideByDefault: false,
      },
      added: {
        name: "Added", displayOrder: displayOrder++,
        value: get(this.specialConcepts, '.added.length', undefined),
        hiddenConceptCnt: cidDiff(this.specialConcepts.added, visibleCids),
        hideByDefault: true,
      },
      removed: {
        name: "Removed", displayOrder: displayOrder++,
        value: get(this.specialConcepts, '.removed.length', undefined),
        hiddenConceptCnt: cidDiff(this.specialConcepts.removed, visibleCids),
        hideByDefault: true,
      },
      expansion: {
        name: "Expansion concepts", displayOrder: displayOrder++,
        value: uniq(flatten(Object.values(csmi).map(Object.values))
                .filter(c => c.csm).map(c => c.concept_id)).length,
        hiddenConceptCnt: cidDiff(concept_ids, visibleCids),
      },
      standard: {
        name: "Standard concepts", displayOrder: displayOrder++,
        value: concepts.filter(c => c.standard_concept === 'S').length,
      },
      classification: {
        name: "Classification concepts", displayOrder: displayOrder++,
        value: concepts.filter(c => c.standard_concept === 'C').length,
      },
      nonStandard: {
        name: "Non-standard", displayOrder: displayOrder++,
        value: this.specialConcepts.nonStandard.length,
        hiddenConceptCnt: cidDiff(this.specialConcepts.nonStandard, visibleCids),
        hideByDefault: false,
      },
    }
    for (let type in rows) {
      let row = {...get(this, ['statsOptionsRows', type], {}), ...rows[type]};
      if (typeof(row.value) === 'undefined') {
        delete rows[type];
        continue;
      }
      row.type = type;
      if (isEmpty(this.statsOptionsRows) && typeof(row.hideByDefault) !== 'undefined') {
        row.isHidden = row.hideByDefault;
      }
      rows[type] = row;
    }
    this.statsOptionsRows = rows;
  };
  getStatsOptionsRows() {
    return sortBy(this.statsOptionsRows, d => d.displayOrder);
  }

  addNodeToVisible(nodeId, displayedRows, alwaysShow, depth = 0) {
    const node = {...this.nodes[nodeId], depth};
    displayedRows.push(node);
    const childIds = this.graph.outNeighbors(nodeId); // Get outgoing neighbors (children)
    if (node.expanded) {
      childIds.forEach(childId => {
        this.addNodeToVisible(childId, displayedRows, alwaysShow, depth + 1); // Recurse
      });
    } else {
      alwaysShow.forEach(alwaysShowId => {
        if (alwaysShowId != nodeId) {
          try {
            let path = bidirectional(this.graph, nodeId, alwaysShowId);
            if (path) {
              path.shift();
              const id = path.pop();
              console.assert(id == alwaysShowId);
              const nd = {...this.nodes[id], depth: depth + 1, path};

              displayedRows.push(nd);
              alwaysShow.delete(id);
              if (nd.expanded) {
                const childIds = this.graph.outNeighbors(id); // Get outgoing neighbors (children)
                sortBy(childIds, this.sortFunc).forEach(childId => {
                  this.addNodeToVisible(childId, displayedRows, alwaysShow, depth + 2); // Recurse
                });
              }
              /*
              path.forEach((id, i) => {
                displayedRows.push({...this.nodes[id], depth: depth + 1 + i});
                alwaysShow.delete(id);
              });
              */
            }
          } catch (e) {
            console.log(e);
          }
        } else {
          alwaysShow.delete(alwaysShowId);
        }
      })
    }
    // return displayedRows;
  }

  sortFunc = (d => {
    let n = this.nodes[d];
    let statusRank = n.isItem && 3 + n.added && 2 + n.removed && 1 || 0;
    // return - (n.drc || n.descendantCount || n.levelsBelow || n.status ? 1 : 0);
    return - (n.levelsBelow || n.descendantCount || n.status ? 1 : 0);
  })

  getVisibleRows(props) {
    // TODO: need to treat things to hide differently from things to always show.
    // let { specialConcepts = [] } = props;
    let alwaysShow = new Set();
    for (let type in this.options.specialConceptsHidden) {
      if (! this.options.specialConceptsHidden[type]) {
        for (let id of this.specialConcepts[type] || []) {
          alwaysShow.add(id);
        }
      }
    }

    // const {/*collapsedDescendantPaths, */ collapsePaths, hideZeroCounts, hideRxNormExtension, nested } = hierarchySettings;
    let displayedRows = [];

    for (let nodeId of sortBy(this.roots, this.sortFunc)) {
      this.addNodeToVisible(nodeId, displayedRows, alwaysShow);
    }

    return this.visibleRows = displayedRows;
  }
  
  #makeGraph(edges, concepts) {
    const [graph, nodes] = makeGraph(edges, concepts);
    this.graph = graph;
    this.nodes = nodes;
  }
  #computeAttributes() {
    const graph = this.graph;
    let nodes = this.nodes;
    function computeAttributesFunc(nodeId, level) {
      let node = nodes[nodeId];
      // Check if the attributes have already been computed to avoid recomputation
      if (node.descendantCount !== undefined) {
        return node;
      }

      let levelsBelow = 0;


      const childIds = graph.outNeighbors(node.concept_id); // Get outgoing neighbors (children)
      let descendants = childIds;

      childIds.forEach(childId => {
        let child = computeAttributesFunc(childId, level + 1);

        levelsBelow = Math.max(levelsBelow, 1 + child.levelsBelow); // Update max depth if this path is deeper
        if (child.descendants) {
          descendants = descendants.concat(child.descendants);
        }
      });

      // nodes[nodeId] = node = {...node, descendantCount: descendants.length, levelsBelow, drc};
      nodes[nodeId] = node = {...node};
      // node.level = level; not sure why level isn't always correct;
      //  to see problem, try `gc.visibleRows.filter(d => d.depth != d.level)` from comparison renderer
      node.levelsBelow = levelsBelow;
      node.descendantCount = 0;
      node.childCount = 0;
      node.drc = node.total_cnt || 0;

      if (levelsBelow > 0) {
        node.expanded = false;  // TODO: deal with expanded differently for shown and hidden
        node.hasChildren = true;
        node.descendants = uniq(descendants); // Remove duplicates
        node.descendantCount = node.descendants.length;
        node.drc += sum(node.descendants.concat(nodeId).map(d => nodes[d].total_cnt || 0)); // Compute descendant counts
        node.children = childIds;
        node.childCount = childIds.length;
      }

      return node;
    }

    // Iterate over all nodes to compute and store attributes
    this.graph.nodes().forEach(node => {
      computeAttributesFunc(node, 0);
    });
    return nodes;
  }
  withAttributes(edges) {
    // this is temporary just to keep the indented stuff working a little while longer
    const graph = new Graph({allowSelfLoops: false, multi: false, type: 'directed'});
    // add each concept as a node in the graph, the concept properties become the node attributes
    Object.entries(this.nodes).forEach(([nodeId, node]) => {
      graph.addNode(nodeId, {...node});
    })
    for (let edge of edges) {
      graph.addDirectedEdge(edge[0], edge[1]);
    }
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
function cidDiff(a, b) {
  return differenceWith(a, b, (a, b) => a == b).length;
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
