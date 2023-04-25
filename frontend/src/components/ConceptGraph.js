import * as React from "react";
import {backend_url, useDataWidget} from "../components/State";

export function currentConceptIds(props) {
  const concepts = props?.cset_data?.concepts ?? [];
  return concepts.map(c => c.concept_id);
}
export function ConceptGraph(props) {
  const {concept_ids, } = props;
  console.log(concept_ids)

  const cidstr = 'get_concepts:' + concept_ids.join("|")
  const url = backend_url(
      "get_concepts?concept_ids=" + concept_ids.map(c=>`id=${c}`).join("&")
  );
  const [widget, cids] = useDataWidget(cidstr, url);
  if (cids.data) {
    return <pre>{JSON.stringify(cids)}</pre>
  }
  return <pre>{JSON.stringify(concept_ids)}</pre>
}
