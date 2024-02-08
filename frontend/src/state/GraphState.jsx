import React, {createContext, useContext, useReducer, useState} from "react";
import {once, flatten, fromPairs, get, pick, isEqual, isEmpty, intersection} from "lodash";
import Graph from "graphology";


const graphReducer = (gc, action) => {
  if (!(action && action.type)) return gc;
  // let { graph, nodes } = gc;
  let graph;
  switch (action.type) {
    case 'CREATE':
      gc = new GraphContainer(action.payload);
      break;
    case 'TOGGLE_NODE_EXPANDED':
      gc = new GraphContainer({self: gc});
      gc.toggleNodeExpanded(action.payload.nodeId);
      break;
    default:
      throw new Error(`unexpected action.type ${action.type}`);
  }
  return gc;
};

const GraphContext = createContext(null);

class GraphContainer {
  constructor(props) {
    const { edges, concepts, self } = props;
    if (self) {
      // cloning to force re-render on change
      this.graph = self.graph;
      this.nodes = self.nodes;
    } else {
      this.#makeGraph(edges, concepts);  // sets this.graph and this.nodes
      this.#computeAttributes();
    }
    this.roots = this.graph.nodes().filter(n => !this.graph.inDegree(n));
    this.leaves = this.graph.nodes().filter(n => !this.graph.outDegree(n));
    this.orphans = intersection(this.roots, this.leaves);
  }
  toggleNodeExpanded(nodeId) {
    const node = this.nodes[nodeId];
    this.nodes = {...this.nodes, [nodeId]: {...node, expanded:!node.expanded}};
  }

  addNodeToVisible(nodeId, displayedRows) {
    const node = this.nodes[nodeId];
    displayedRows.push(node);
    if (node.expanded) {
      const neighborIds = this.graph.outNeighbors(nodeId); // Get outgoing neighbors (children)
      neighborIds.forEach(neighborId => {
        this.addNodeToVisible(neighborId, displayedRows);
      });
    }
    // return displayedRows;
  }

  getVisibleRows(props) {
    // const {/*collapsedDescendantPaths, */ collapsePaths, hideZeroCounts, hideRxNormExtension, nested } = hierarchySettings;
    let displayedRows = [];

    for (let nodeId of this.roots) {
      this.addNodeToVisible(nodeId, displayedRows);
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

      let descendantCount = 0;
      let levelsBelow = 0;
      let totalCountSum = node.total_cnt || 0; // Initialize with the node's own total_cnt

      const neighborIds = graph.outNeighbors(node.concept_id); // Get outgoing neighbors (children)

      neighborIds.forEach(neighborId => {
        const {descendantCount: childCount, levelsBelow: childLevels, totalCountSum: childTotalCountSum} = computeAttributesFunc(neighborId);
        descendantCount += 1 + childCount; // Count child + descendants of child
        levelsBelow = Math.max(levelsBelow, 1 + childLevels); // Update max depth if this path is deeper
        totalCountSum += (childTotalCountSum || 0); // Accumulate total_cnt from descendants
      });

      nodes[nodeId] = node = {...node, descendantCount, levelsBelow, totalCountSum};
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
