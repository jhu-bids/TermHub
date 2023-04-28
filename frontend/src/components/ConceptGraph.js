import React, {useState, useEffect} from "react";
import {dataAccessor} from "./State";
import _ from "../supergroup/supergroup";

export function currentConceptIds(props) {
  const concepts = props?.cset_data?.concepts ?? [];
  return concepts.map(c => c.concept_id);
}
export function ConceptGraph(props) {
  const {concept_ids, } = props;
  const [concepts, setConcepts] = useState([]);
  const [edges, setEdges] = useState([]);

  console.log({concept_ids, concepts});

  useEffect(() => {
    async function fetchData() {
      const _concepts = await dataAccessor.getConcepts(concept_ids, 'array');
      setConcepts(_concepts);
    }
    fetchData();
  }, []);
  useEffect(() => {
    async function fetchData() {
      const _edges = await dataAccessor.getSubgraphEdges(concept_ids, 'array');
      setEdges(_edges);
    }
    fetchData();
  }, []);

  if (edges.length) {
    // return <pre>{JSON.stringify(edges, null, 2)}</pre>;
    // edge looks like {
    //     "sub": "N3C:46274124",       // child
    //     "pred": "rdfs:subClassOf",
    //     "obj": "N3C:36684328",       // parent
    //     "meta": null
    //   },

    let tree = _.hierarchicalTableToTree(edges, 'obj', 'sub')
    let paths = tree.flattenTree().map(d => d.namePath());
    console.log(paths);
    return <pre>{paths.join('\n')}</pre>;
  }
  if (concepts.length) {
    // return <pre>{JSON.stringify(concepts, null, 2)}</pre>;
  }
  return <pre>{JSON.stringify(concept_ids)}</pre>;
}
