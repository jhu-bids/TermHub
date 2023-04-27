import React, {useState, useEffect} from "react";
import {dataAccessor} from "./State";

export function currentConceptIds(props) {
  const concepts = props?.cset_data?.concepts ?? [];
  return concepts.map(c => c.concept_id);
}
export function ConceptGraph(props) {
  const {concept_ids, } = props;
  const [concepts, setConcepts] = useState([]);

  console.log({concept_ids, concepts});

  useEffect(() => {
    async function fetchData() {
      const _concepts = await dataAccessor.getConcepts(concept_ids, 'array');
      setConcepts(_concepts);
    }
    fetchData();
  }, []);

  if (concepts.length) {
    return <pre>{JSON.stringify(concepts, null, 2)}</pre>;
  }
  return <pre>{JSON.stringify(concept_ids)}</pre>;
}
