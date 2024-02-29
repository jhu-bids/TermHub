import React, { FC, useEffect, useState, useMemo } from "react";
// import seedrandom from "seedrandom";
import { faker, Faker } from "@faker-js/faker";
import { SigmaContainer, useSigma, useLoadGraph, useRegisterEvents } from "@react-sigma/core";
import { useLayoutCircular } from "@react-sigma/layout-circular";
import Graph from "graphology";
import "@react-sigma/core/lib/react-sigma.min.css";
import {useSearchParamsState} from "../state/SearchParamsProvider";
import {getResearcherIdsFromCsets, useDataGetter} from "../state/DataGetter";
import {flatten, isEmpty, max, sum, union, uniq} from "lodash";
import * as d3dag from "d3-dag";
// import {formatEdges} from "./ConceptGraph";
// import { Attributes } from "graphology-types";
import {assignLayout} from 'graphology-layout/utils';
import {collectLayout} from 'graphology-layout/utils';
import {fetchGraphData} from "./CsetComparisonPage";
import {useGraphContainer} from "../state/GraphState";

// import {useSeedRandom} from "react-seed-random";
export const ConceptGraph/*: React.FC*/ = () => {
  // const sigma = useSigma();
  const {sp} = useSearchParamsState();
  let {codeset_ids=[], cids=[], use_example=false} = sp;
  const dataGetter = useDataGetter();
  const {gc, gcDispatch} = useGraphContainer();
  const [data, setData] = useState({ cids: [], graph_data: {}, concepts: [], });
  const { concept_ids, selected_csets, conceptLookup, csmi,
            concepts, specialConcepts, comparison_rpt, } = data;

  useEffect(() => {
    (async () => {

      await dataGetter.getApiCallGroupId();

      const graphData = fetchGraphData({dataGetter, sp, gcDispatch, codeset_ids})

      let { concept_ids, selected_csets, conceptLookup, csmi, concepts, specialConcepts,
        comparison_rpt } = await graphData;

      setData(current => ({
        ...current, concept_ids, selected_csets, conceptLookup, csmi,
        concepts, specialConcepts, comparison_rpt,
      }));
    })()
  }, []);

  const MyGraph = () => {
    const loadGraph = useLoadGraph();

    useEffect(() => {
      // Create the graph
      // const graph = new MultiDirectedGraph();
      /*
      const graph = new Graph();
      graph.addNode("A", { x: 0, y: 0, label: "Node A", size: 10 });
      graph.addNode("B", { x: 1, y: 1, label: "Node B", size: 10 });
      graph.addEdgeWithKey("rel1", "A", "B", { label: "REL_1" });
       */
      if (gc && gc.graph) {
        let laidOutGraph = gc.graphLayout();
        loadGraph(laidOutGraph);
      }
    }, [loadGraph, gc]);

    return null;
  };

  return (
    <SigmaContainer style={{ height: "1500px" }}>
      <MyGraph />
    </SigmaContainer>
  );
}

export const DisplayGraph/*: React.FC*/ = () => {
  const RandomCircleGraph/*: React.FC*/ = () => {
    const { faker, randomColor } = useSeedRandom();
    const sigma = useSigma();
    const { positions, assign } = useLayoutCircular();
    const registerEvents = useRegisterEvents();
    const [draggedNode, setDraggedNode] = useState<string | null>(null);


    const loadGraph = useLoadGraph();

    useEffect(() => {
      const order = 100;
      const probability = 0.1;

      // Create the graph
      const graph = new Graph();
      for (let i = 0; i < order; i++) {
        graph.addNode(i, {
          label: faker.name.fullName(),
          size: faker.datatype.number({ min: 4, max: 20, precision: 1 }),
          color: randomColor(),
          x: 0,
          y: 0,
        });
      }
      for (let i = 0; i < order; i++) {
        for (let j = i + 1; j < order; j++) {
          if (Math.random() < probability) graph.addDirectedEdge(i, j);
          if (Math.random() < probability) graph.addDirectedEdge(j, i);
        }
      }

      loadGraph(graph);
      assign();
      // console.log(positions());
    }, [assign, loadGraph, faker.datatype, faker.name, randomColor]);

    return null;
  };

  return (
    <SigmaContainer style={{ height: "1500px" }}>
      <RandomCircleGraph />
    </SigmaContainer>
  );
};
function sugiyamaLayout(edges) {
  const connect = d3dag.dagConnect();
  const dag = connect(edges); // using d3dag for the sugiyama layout
  const graphSize = d3dag.sugiyama();
  const layout = d3dag.sugiyama();
  const {width, height} = layout(dag);


  const graph = new Graph();  // but using graphology graph with sigma
  let slayout = {};

  for (let dn of dag.descendants()) {
    // let n = parseInt(dn.data.id);
    let n = dn.data.id; // I think it turns graph node ids into strings
    slayout[n] = { x: dn.x, y: dn.y,}; // for TermHub example, this is too wide
    // slayout[n] = { x: dn.y, y: dn.x,}; // now too tall, not helpful
  }
  return {graph, graphSize, slayout};
}