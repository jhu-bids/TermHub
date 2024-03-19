import React, { FC, useEffect, useState, useMemo } from "react";
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

  const GraphEvents = () => {
    const registerEvents = useRegisterEvents();
    const sigma = useSigma();
    useEffect(() => {
      registerEvents({
        enterNode: (event) => {
          console.log(
              sigma.getGraph().getNodeAttribute(event.node, "concept_name"),
              sigma.getGraph().getNodeAttribute(event.node, "layer"),
              sigma.getGraph().getNodeAttribute(event.node, "position"),
          );
        }
      })
    }, [registerEvents, sigma, ])
  }

  return (
    <SigmaContainer style={{ height: "1500px" }}>
      <MyGraph />
      <GraphEvents />
    </SigmaContainer>
  );
}
