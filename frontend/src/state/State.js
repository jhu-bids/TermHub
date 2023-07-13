import React, {createContext, useContext, useEffect, useState} from "react";
// TODO: move createSearch... to SearchParamsProvider
import CircularProgress from "@mui/material/CircularProgress";
import Box from "@mui/material/Box";
import {Inspector} from 'react-inspector'; // https://github.com/storybookjs/react-inspector
import {pct_fmt} from "../components/utils";
import {useSearchParamsState} from "./SearchParamsProvider";
import {useAppState} from "./AppState";
import {useDataCache} from "../state/DataCache";
import {useDataGetter} from "./DataGetter";

const stateDoc = `
    URL query string: SearchParamsProvider, useSearchParams
      codeset_ids
      editCodesetId
      csetEditState
      sort_json
      use_example

    reducers and context
    handled by useAppState, AppStateProvider, useStateSlice(slice)
      really using:
        hierarchySettings
      WIP, not using:
        codeset_ids
        concept_ids
        editCset

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
  const [sp, spDispatch] = useSearchParamsState();
  const appState = useAppState();
  const dataCache = useDataCache();
  return (<div style={{margin: 30, }}>
    <h1>Current state</h1>

    <h2>query string parameters</h2>
    <Inspector data={sp} />

    <h2>app state (reducers)</h2>
    <Inspector data={appState.getState()} />

    <h2>dataCache</h2>
    <Inspector data={dataCache.getWholeCache()} />

    <h2>The different kinds of state</h2>
    <pre>{stateDoc}</pre>
  </div>);
}

// const TotalStateContext = createContext(null);
// export function TotalStateProvider({children}) {
//   const {sp, updateSp} = useSearchParamsState();
//   const appState = useAppState();
//   const dataCache = useDataCache();
//   const dataGetter = useDataGetter();
//
//   const [lastRefresh, setLastRefresh] = useState(dataCache.lastRefreshed());
//   useEffect(() => {
//     (async () => {
//       const timestamp = await dataCache.cacheCheck(dataGetter);
//       if (timestamp > lastRefresh) {
//         setLastRefresh(timestamp);
//       }
//     })();
//   });
//
//   let stateParts = {sp, updateSp, appState, dataCache};
//   let totalState = {...sp, ...appState.getState(), ...dataCache.getWholeCache(), stateParts, };
//   return (
//       <TotalStateContext.Provider value={totalState}>
//         {children}
//       </TotalStateContext.Provider>
//   );
// }
//
// export function useTotalState() {
//   return useContext(TotalStateContext);
// }