import React, { FC, useEffect, useState, useMemo } from "react";
// import seedrandom from "seedrandom";
import { faker, Faker } from "@faker-js/faker";
import { SigmaContainer, useSigma, useLoadGraph, useRegisterEvents } from "@react-sigma/core";
import { useLayoutCircular } from "@react-sigma/layout-circular";
import Graph from "graphology";
import "@react-sigma/core/lib/react-sigma.min.css";
import {useSearchParamsState} from "../state/SearchParamsProvider";
import {useDataGetter} from "../state/DataGetter";
import {flatten, isEmpty, union, uniq} from "lodash";
// import {formatEdges} from "./ConceptGraph";
// import { Attributes } from "graphology-types";


export const ConceptGraph: React.FC = () => {
  const {sp} = useSearchParamsState();
  const {codeset_ids, use_example=false} = sp;
  const dataGetter = useDataGetter();
  const [data, setData] = useState({ concept_ids: [], graph_data: {}, concepts: [], });
  const { concept_ids, graph_data, concepts, } = data;

  useEffect(() => {
    (async () => {

      await dataGetter.getApiCallGroupId();

      const concept_ids_by_codeset_id = await dataGetter.fetchAndCacheItems(dataGetter.apiCalls.concept_ids_by_codeset_id, codeset_ids);
      let concept_ids = union(flatten(Object.values(concept_ids_by_codeset_id)));

      const graph_data = await dataGetter.fetchAndCacheItems(dataGetter.apiCalls.concept_graph, concept_ids, );
      const {edges, layout, filled_gaps} = graph_data;
      // indentedCids = [[<level>, <concept_id>], ...]
      concept_ids = uniq(concept_ids.concat(filled_gaps));

      const concepts = await dataGetter.fetchAndCacheItems(dataGetter.apiCalls.concepts, concept_ids);

      setData({concept_ids, graph_data, concepts});
    })()
  }, []);

  interface SugiyamaGraphProps {
    graph_data: any;  // Replace 'any' with the actual type of graph_data
  }

  const SugiyamaGraph: React.FC<SugiyamaGraphProps> = (props) => {
    const loadGraph = useLoadGraph();
    const {graph_data} = props;

    useEffect(() => {
      if (isEmpty(graph_data)) {
        return;
      }
      // Create the graph
      const graph = new Graph();

      const {edges, layout, filled_gaps} = graph_data;

      for (let concept_id in layout) {
        const [x, y] = layout[concept_id];
        graph.addNode(concept_id, {
          label: concepts[concept_id].concept_name,
          size: 10,
          // color: randomColor(),
          x, y,
        });
      }
      for (let edge of edges) {
        graph.addDirectedEdge(edge[0], edge[1]);
      }

      loadGraph(graph);
    }, [loadGraph, graph_data])

    return null;
  }

  return (
      <SigmaContainer style={{ height: "1500px" }}>
        {/*<SugiyamaGraph graph_data={graph_data}/>*/}
        <DisplayGraph />
      </SigmaContainer>
  );
}
export const DisplayGraph: React.FC = () => {
  const RandomCircleGraph: React.FC = () => {
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
      console.log(positions());
    }, [assign, loadGraph, faker.datatype, faker.name, randomColor]);

    return null;
  };

  return (
    <SigmaContainer style={{ height: "1500px" }}>
      <RandomCircleGraph />
    </SigmaContainer>
  );
};