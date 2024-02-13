import React, {createContext, useContext, useReducer, useState} from "react";
import {sum, sortBy, uniq, flatten, intersection, difference} from "lodash";
import Graph from "graphology";
import {bidirectional} from 'graphology-shortest-path/unweighted';

const graphReducer = (gc, action) => {
  if (!(action && action.type)) return gc;
  // let { graph, nodes } = gc;
  let graph;
  switch (action.type) {
    case 'CREATE':
      gc = new GraphContainer(action.payload);
      break;
    case 'TOGGLE_NODE_EXPANDED':
      gc = new GraphContainer(null, gc);
      gc.toggleNodeExpanded(action.payload.nodeId);
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
      return;
    }
    let {concepts, edges, concept_ids, filled_gaps, missing_from_graph,
      hidden_by_vocab, nonstandard_concepts_hidden} = graphData;
    Object.assign(this, {concept_ids, filled_gaps, missing_from_graph,
      hidden_by_vocab, nonstandard_concepts_hidden});
    let graphConceptIds = uniq(flatten(edges));
    // this.graphConcepts = concepts.filter(c => graphConceptIds.includes(c.concept_id));
    this.#makeGraph(edges, concepts);  // sets this.graph and this.nodes

    this.roots = this.graph.nodes().filter(n => !this.graph.inDegree(n));
    this.leaves = this.graph.nodes().filter(n => !this.graph.outDegree(n));
    this.isolatedConcepts = intersection(this.roots, this.leaves);

    let isolatedConceptsParent = {
      "concept_id": 'isolated',
      "concept_name": "Concepts in set but not linked to others",
      "vocabulary_id": "--",
      "standard_concept": "",
      "total_cnt": 0,
      "distinct_person_cnt": "0",
      "status": ""
    };
    this.graph.addNode('isolated');
    this.nodes['isolated'] = isolatedConceptsParent;
    for (let c of this.isolatedConcepts) {
      this.graph.addDirectedEdge('isolated', c);
    }
    this.roots = this.graph.nodes().filter(n => !this.graph.inDegree(n));
    this.leaves = this.graph.nodes().filter(n => !this.graph.outDegree(n));

    this.#computeAttributes();
    this.concepts = concepts;
  }
  toggleNodeExpanded(nodeId) {
    const node = this.nodes[nodeId];
    this.nodes = {...this.nodes, [nodeId]: {...node, expanded:!node.expanded}};
  }

  addNodeToVisible(nodeId, displayedRows, alwaysShow, depth = 0) {
    const node = {...this.nodes[nodeId], depth};
    displayedRows.push(node);
    const neighborIds = this.graph.outNeighbors(nodeId); // Get outgoing neighbors (children)
    if (node.expanded) {
      neighborIds.forEach(neighborId => {
        this.addNodeToVisible(neighborId, displayedRows, alwaysShow, depth + 1); // Recurse
      });
    } else {
      alwaysShow.all.forEach(alwaysShowId => {
        if (alwaysShowId != nodeId) {
          try {
            let path = bidirectional(this.graph, nodeId, alwaysShowId);
            if (path) {
              path.shift();
              const id = path.pop();
              console.assert(id == alwaysShowId);
              const nd = {...this.nodes[id], depth: depth + 1, path};

              displayedRows.push(nd);
              alwaysShow.all.delete(id);
              if (nd.expanded) {
                const neighborIds = this.graph.outNeighbors(id); // Get outgoing neighbors (children)
                sortBy(neighborIds, this.sortFunc).forEach(neighborId => {
                  this.addNodeToVisible(neighborId, displayedRows, alwaysShow, depth + 2); // Recurse
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
          alwaysShow.all.delete(alwaysShowId);
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
    let { alwaysShow = [] } = props;
    alwaysShow.all = new Set(flatten(['expressionItems','added','removed'].map(d => alwaysShow[d])))

    // const {/*collapsedDescendantPaths, */ collapsePaths, hideZeroCounts, hideRxNormExtension, nested } = hierarchySettings;
    let displayedRows = [];

    for (let nodeId of sortBy(this.roots, this.sortFunc)) {
      this.addNodeToVisible(nodeId, displayedRows, alwaysShow);
    }

    return displayedRows;
  }
  #makeGraph(edges, concepts) {
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
    this.graph = graph;
    this.nodes = nodes;
  }
  #computeAttributes() {
    const graph = this.graph;
    let nodes = this.nodes;
    function computeAttributesFunc(nodeId) {
      let node = nodes[nodeId];
      // Check if the attributes have already been computed to avoid recomputation
      if (node.descendantCount !== undefined) {
        return node;
      }

      let levelsBelow = 0;


      const neighborIds = graph.outNeighbors(node.concept_id); // Get outgoing neighbors (children)
      let descendants = neighborIds;

      neighborIds.forEach(neighborId => {
        let child = computeAttributesFunc(neighborId);

        levelsBelow = Math.max(levelsBelow, 1 + child.levelsBelow); // Update max depth if this path is deeper
        if (child.descendants) {
          descendants = descendants.concat(child.descendants);
        }
      });

      descendants = uniq(descendants); // Remove duplicates
      const drc = sum(descendants.concat(nodeId).map(d => nodes[d].total_cnt || 0)); // Compute descendant counts
      nodes[nodeId] = node = {...node, descendantCount: descendants.length, levelsBelow, drc};
      if (levelsBelow > 0) {
        node.hasChildren = true;
        node.expanded = false;
      }

      return node;
    }

    // Iterate over all nodes to compute and store attributes
    this.graph.nodes().forEach(node => {
      computeAttributesFunc(node, this.graph, this.nodes);
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
