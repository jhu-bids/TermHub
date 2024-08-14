import React, { FC, useEffect, useState, useMemo } from "react";
import { SigmaContainer, useSigma, useLoadGraph, useRegisterEvents } from "@react-sigma/core";
import { useLayoutCircular } from "@react-sigma/layout-circular";
import Graph from "graphology";
import "@react-sigma/core/lib/react-sigma.min.css";
import {useSearchParamsState} from "../state/StorageProvider";
import {getResearcherIdsFromCsets, useDataGetter} from "../state/DataGetter";
import {flatten, isEmpty, max, sum, union, uniq} from "lodash";
import * as d3dag from "d3-dag";
// import {formatEdges} from "./ConceptGraph";
// import { Attributes } from "graphology-types";
import {assignLayout} from 'graphology-layout/utils';
import {collectLayout} from 'graphology-layout/utils';
import {fetchGraphData} from "./CsetComparisonPage";
import {useCodesetIds, useCids} from "../state/AppState";
// import {useGraphContainer} from "../state/GraphState";

// import {useSeedRandom} from "react-seed-random";
export const ConceptGraph/*: React.FC*/ = () => {
  // const sigma = useSigma();

  const [appOptions, setAppOptions] = useAppOptions();
  const {comparison_pair} = appOptions();
  const [codeset_ids, ] = useCodesetIds();
  const [cids, ] = useCids();

  const dataGetter = useDataGetter();
  // const [data, setData] = useState({ cids: [], graph_data: {}, concepts: [], });
  // const { concept_ids, selected_csets, conceptLookup, csmi, concepts, specialConcepts, comparison_rpt, } = data;
  // const {gc, gcDispatch} = useGraphContainer();

  useEffect(() => {
    (async () => {

      await dataGetter.getApiCallGroupId();

      const graphData = fetchGraphData({dataGetter, comparison_pair, gcDispatch, codeset_ids});

      let { concept_ids, selected_csets, conceptLookup, csmi, concepts, specialConcepts, comparison_rpt } = await graphData;

      setData(current => ({
        ...current, concept_ids, selected_csets, conceptLookup, csmi, concepts, specialConcepts, comparison_rpt,
      }));
    })();
  }, []);

  const SigmaGraph = () => {
    const loadGraph = useLoadGraph();

    useEffect(() => {
      if (gc && gc.graph) {
        let laidOutGraph = gc.graphLayout();
        loadGraph(laidOutGraph);
      }
    }, [loadGraph, gc]);

    throw new Error("need to get graph container...no longer available through useGraphContainer");
    // return null;
  };

  return (
    <SigmaContainer style={{ height: "1200px" }}>
      <SigmaGraph />
    </SigmaContainer>
  );
}
