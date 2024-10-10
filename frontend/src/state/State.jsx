import React, {createContext, useContext, useEffect, useState} from "react";
// TODO: move createSearch... to SearchParamsProvider
import CircularProgress from "@mui/material/CircularProgress";
import Box from "@mui/material/Box";
import {Inspector} from 'react-inspector'; // https://github.com/storybookjs/react-inspector
import {pct_fmt} from "../components/utils";
import {useSearchParamsState} from "./SearchParamsProvider";
import {useAlerts, useHierarchySettings, useNewCset} from "./AppState";
import {useDataCache} from "../state/DataCache";
import {useDataGetter} from "./DataGetter";

const stateDoc = `
    2023-08
    State management is pretty messed up at the moment. We need decent performance....
    Here's what needs to be tracked in state and description of how it's all related.

    codeset_ids, selected in a few different ways:
      - with a list on the About page
      - on search page by selecting from drop down and clicking load concept sets
      - on search page after some are chosen by clicking a selected cset to deselect it
        or clicking a related cset to add it to the selection

    concept_ids and concept (metadata) for them:
      - for all definition (expression) items and expansion members of selected codeset_ids
        PLUS:
          - Additional concepts from vocab hierarchies needed to connect the already selected concept_ids
          - Concept_ids (but don't need all the metadata) for for all the related concept sets in order to
            calculate share, precision, and recall
          - Additional concepts of interest to users -- not implemented yet, but important (and these will
            probably require the concept metadata, not just concept_ids)
      - The way that all works (will work) is:
        1. Call concept_ids_by_codeset_id for all selected codeset_ids
        2. Call subgraph to get hierarchy for all resulting concept_ids (and any additionally requested concept_ids);
           this will add a few more concept_ids for filling in gaps. Subgraph returns edges. Edge list is unique for
           each unique set of input concept_ids. --- which makes this step horrible for caching and a possible performance
           bottleneck.
        3. Call codeset_ids_by_concept_id for all concept_ids from step 1 (or 2?)
        4. Call concept_ids_by_codeset_id again for all codeset_ids from step 3. This is also a performance/caching
           problem because it's a lot of data.

        For steps 2 and 3, the union of all concept_ids is what we need. For step 4, we need the list of concept_ids
        associated with each codeset_id in order to perform the calculations (shared/prec/recall.)

    Coming up with the right caching strategy that balances ease of use (programming-wise), data retrieval and
    storage efficiency, and stability has been hard and I don't have a decent solution at the moment. Considering
    trying to move (back) to something simpler.





    URL query string: SearchParamsProvider, useSearchParams
      codeset_ids
      sort_json
      use_example

    reducers and context
      alerts, hierarchySettings, newCset
      newCset

    DataCache
      all_csets
      edges
      cset_members_items
      selected_csets
      researchers
      concepts
      ????

    local to components, useState, etc.

    Goals:
      Manage all/
`;

function Progress(props) {
  return (
    <Box sx={{ display: "flex" }}>
      <CircularProgress {...props} size="35px" />
    </Box>
  );
}

export function StatsMessage(props) {
  const { codeset_ids = [], all_csets = [], relatedCsets,
          concept_ids, selected_csets, } = props;

  const relcsetsCnt = relatedCsets.length;
  return (
    <p style={{ margin: 0, fontSize: "small" }}>
      The <strong>{codeset_ids.length} concept sets </strong>
      selected contain{" "}
      <strong>{(concept_ids || []).length.toLocaleString()} distinct concepts</strong>. The
      following <strong>{relcsetsCnt.toLocaleString()} concept sets </strong>(
      {pct_fmt(relcsetsCnt / all_csets.length)}) have 1 or more
      concepts in common with the selected sets. Click rows below to select or
      deselect concept sets.
    </p>
  );
}

export function ViewCurrentState() {
  const {sp} = useSearchParamsState();
  const alerts = useAlerts();
  const [hierarchySettings, hsDispatch] = useHierarchySettings();
  debugger;
  const newCset = useNewCset();
  const dataCache = useDataCache();
  return (<div style={{margin: 30, }}>
    <h1>Current state</h1>

    <h2>query string parameters</h2>
    <Inspector data={sp} />

    <h2>app state (reducers)</h2>
    <Inspector data={{alerts, hierarchySettings, newCset}} />

    <h2>dataCache</h2>
    <Inspector data={dataCache.getWholeCache()} />

    <h2>The different kinds of state</h2>
    <pre>{stateDoc}</pre>
  </div>);
}
