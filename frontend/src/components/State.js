import React, {
  createContext,
  useContext,
  useReducer,
  useState /* useRef, useLayoutEffect, */,
} from "react";
// import useCombinedReducers from 'use-combined-reducers';
import axios from "axios";
import { API_ROOT } from "../env";
import CircularProgress from "@mui/material/CircularProgress";
import Box from "@mui/material/Box";
import { useQuery } from "@tanstack/react-query";
import {queryClient} from "../App";
import { createSearchParams, useSearchParams } from "react-router-dom";
import { isEmpty, get, uniq, pullAt, fromPairs, flatten, union } from "lodash";
import { pct_fmt } from "./utils";
import WarningRoundedIcon from '@mui/icons-material/WarningRounded';
import { CheckCircleRounded } from "@mui/icons-material";
import { Inspector } from 'react-inspector'; // https://github.com/storybookjs/react-inspector

const stateDoc = `
    URL query string
    handled by QueryStringStateMgr updateSearchParams(props) and searchParamsToObj(searchParams)
      codeset_ids
      editCodesetId
      csetEditState
      sort_json
      use_example

    Fetch at top level and passing props down from there
    handled by DataContainer, useDataWidget, react-query, etc.
      from cr-hierarchy
        all_csets
        cset_data
          edges
          cset_members_items
          selected_csets
          researchers
          related_csets
          concepts

    reducers and context
    handled by useAppState, AppStateProvider, useStateSlice(slice)
      really using:
        hierarchySettings
      WIP, not using:
        codeset_ids
        concept_ids
        editCset

    DataAccessor
        getConcepts -- much more efficient than getting from cr-hierarchy, and it works, but
          not really using it

    local to components, useState, etc.

    Goals:
      Manage all/
`;

export function ViewCurrentState(props) {
  const [searchParams, setSearchParams] = useSearchParams();
  const sp = searchParamsToObj(searchParams, setSearchParams);
  const appState = useAppState();
  return (<div style={{margin: 30, }}>
    <h1>Current state</h1>

    <h2>query string parameters</h2>
    <Inspector data={sp} />

    <h2>props</h2>
    <Inspector data={props} />

    <h2>app state (reducers)</h2>
    <Inspector data={appState.getState()} />

    <h2>dataAccessor</h2>
    <Inspector data={dataAccessor.getCache()} />


    <h2>The different kinds of state</h2>
    <pre>{stateDoc}</pre>
  </div>);
}
export async function fetchItems(itemType, paramList, storeToCacheFunc,
                                 strategy = '1-to-1') {
  let url;

  // We expect a 1-to-1 relationship between paramList items (concept_ids) and retrieved items (concepts)
  if (itemType === 'concept') { // expects paramList of concept_ids
    url = backend_url('get-concepts?' + paramList.map(key => `id=${key}`).join('&'));

  } else if (itemType === 'cset_members_items') { // expects paramList of codeset_ids
    url = backend_url('get-cset-members-items?'+ paramList.map(key => `codeset_ids=${key}`).join('&'));

  } else if (itemType === 'concept_ids_from_codeset_ids') { // expects paramList of codeset_ids
    /* This one is weird. With concept and cset_members_items we expect a 1-to

     */
    const concept_id_groups = await Promise.all(paramList.map(
      async codeset_id => {
        url = backend_url(`get-concept_ids-from-codeset_ids?codeset_ids=${codeset_id}`);
        const queryKey = [`concept_ids_for_${codeset_id}`];
        const queryFn = () => axiosGet(url);
        console.log("fetching", url);
        const data = await queryClient.fetchQuery({ queryKey, queryFn })
        return data;
      }));
    try {
      storeToCacheFunc(concept_id_groups);
    } catch (error) {
      console.log(error);
    }
    // return union(Object.values(concept_ids_by_codeset_id));
    return concept_id_groups;

  } else if (itemType === 'edge') { // expects paramList of concept_ids
    url = backend_url('subgraph?'+ paramList.map(key => `id=${key}`).join('&'));

  } else {
    throw new Error(`Don't know how to fetch ${itemType}`);
  }
  const queryKey = [itemType, JSON.stringify(paramList)];
  // https://tanstack.com/query/v4/docs/react/reference/QueryClient#queryclientfetchquery
  const queryFn = () => axiosGet(url);
  console.log("fetching", url);
  const data = await queryClient.fetchQuery({ queryKey, queryFn })
  if (storeToCacheFunc) {
    try {
      storeToCacheFunc(data);
    } catch (error) {
      console.log(error);
    }
  }
  return data;
}

class DataAccess {
  #cache = {};
  constructor() {
    this.#cache = this.loadCache() ?? {};
  }
  getCache() {
    return this.#cache;
  }
  saveCache = () => {
    localStorage.setItem('dataAccessor', JSON.stringify(this.#cache));
    return null;
  }
  loadCache = () => {
    return JSON.parse(localStorage.getItem('dataAccessor'));
  }
  async cacheCheck() {
    const url = 'http://127.0.0.1:8000/last-refreshed';
    const tsStr = await axiosGet(url);
    const ts = new Date(tsStr);
    if (isNaN(ts.getDate())) {
      throw new Error(`invalid date from ${url}: ${tsStr}`);
    }
    const lrStr = this.lastRefreshed();
    const lr = new Date(lrStr);
    if (isNaN(lr.getDate()) || ts > lr) {
      console.log(`previous DB refresh: ${lrStr}; latest DB refresh: ${ts}. Clearing localStorage.`);
      localStorage.clear();
      return this.#cache.lastRefreshTimestamp = ts;
    } else {
      console.log(`no change since last refresh at ${lr}`);
      return lr;
    }
  }
  lastRefreshed() {
    // console.log('dataAccessor cache', this.getCache());
    const lr = get(this.#cache,'lastRefreshTimestamp');
    return lr;
  }
  async getItemsByKey({ itemType,
                        keyName,
                        keys=[],
                        shape='array', /* or obj */
                        returnFunc
  }) {
    // use this for concepts and cset_members_items
    let wholeCache = get(this.#cache, itemType, {});
    let cachedItems = {};     // this will hold the requested items that are already cached
    let uncachedKeys = []; // requested items that still need to be fetched
    let uncachedItems = {};   // this will hold the newly fetched items

    keys.forEach(key => {
      if (wholeCache[key]) {
        cachedItems[key] = wholeCache[key];
      } else {
        uncachedKeys.push(key);
      }
    })
    if (uncachedKeys.length) {
      const data = await fetchItems(
          itemType,
          uncachedKeys,
          this.storeItemsByKeys({itemType, keys:uncachedKeys}));
      data.forEach((item, i) => uncachedItems[keys[i]] = item);
    }
    const results = { ...cachedItems, ...uncachedItems };
    const not_found = uncachedKeys.filter(key => !(key in results));
    if (not_found.length) {
      // TODO: let user see warning somehow
      console.warn(`Warning in DataAccess.getItemsByKey: failed to fetch ${itemType}s for ${not_found.join(', ')}`);
    }
    if (returnFunc) {
      return returnFunc(results);
    }
    if (shape === 'array') {
      return Object.values(results);
    }
    return results;
  }
  storeItemsByKeys = ({itemType, keyName, keys=[]}) => {
    return items => {
      if (!isEmpty(keys)) {
        if (items.length !== keys.length) {
          throw new Error("mismatching items and keys lengths");
        }
      }
      items.forEach((item,i) => {
        this.#cache[itemType] = this.#cache[itemType] ?? {};
        const key = keyName ? item[keyName] : keys[i];
        this.#cache[itemType][key] = item;
      });
    };
  }
  getConceptIds(codeset_ids=[], ) {
  }
}
export const dataAccessor = new DataAccess();
window.addEventListener("beforeunload", dataAccessor.saveCache);
// window.onload = dataAccessor.loadCache; happens at wrong time. moving this to constructor
// for debugging
window.dataAccessorW = dataAccessor;



export function useStateSlice(slice) {
  const appState = useAppState();
  const [state, dispatch] = appState.getSlice(slice);
  return { state, dispatch };  // should probably return array instead of object?
}
const CombinedReducersContext = createContext(null);
export function AppStateProvider({ children }) {
  const [hierarchySettings, dispatch] = useReducer(hierarchySettingsReducer, {
    nested: true,
    collapsePaths: {},
    collapsedDescendantPaths: {},
    hideRxNormExtension: true,
    hideZeroCounts: false,
  });
  const hsDispatch = (...args) => {
    window.Pace.restart();
    setTimeout(() => dispatch(...args), 100);
  }
  const reducers = {
    // contentItems: useReducer(contentItemsReducer, defaultContentItems),
    codeset_ids: useReducer(codeset_idsReducer, []),
    concept_ids: useReducer(currentConceptIdsReducer, []),
    editCset: useReducer(editCsetReducer),
    // more stuff needed
    hierarchySettings: [hierarchySettings, hsDispatch],
  };

  const getters = {
    getSliceState: (slice) => reducers[slice][0],
    getSliceDispatch: (slice) => reducers[slice][1],
    getSlice: (slice) => reducers[slice],
    getSliceNames: () => Object.keys(reducers),
    getReducers: () => reducers,
    getState: () =>
      Object.fromEntries(Object.entries(reducers).map(([k, v]) => [k, v[0]])),
  };
  /*  before doing the getter stuff for the slices, i was having the slice name be a prefix on the action.type
      probably won't return to this, but keeping around for a bit
  const getTypeForSlice = memoize((slice, actionType) => {
    const [reducerSlice, type] = actionType.split(/-(.*)/s); // https://stackoverflow.com/questions/4607745/split-string-only-on-first-instance-of-specified-character
    return (reducerSlice === slice) && type;
  });
    if (!(action && action.type)) return state;
    const type = getTypeForSlice('c ontentItems', action.type);
   */
  return (
    <CombinedReducersContext.Provider value={getters}>
      {children}
    </CombinedReducersContext.Provider>
  );
}
export function useAppState() {
  return useContext(CombinedReducersContext);
}
const editCsetReducer = (state, action) => {
  if (!(action && action.type)) return state;
  if (!action.type) return state;
  if (state === action.payload) return null; // if already set to this codeset_id, turn off
  return action.payload;
};

// actions
const codeset_idsReducer = (state, action) => { // not being used
  if (!(action && action.type)) return state;
  switch (action.type) {
    case "add_codeset_id": {
      return [...state, parseInt(action.payload)].sort();
    }
    case "delete_codeset_id": {
      return state.filter((d) => d != action.payload);
    }
    default:
      return state;
  }
};

const currentConceptIdsReducer = (state, action) => { // not being used
  if (!(action && action.type)) return state;
  switch (action.type) {
    case "add_codeset_id": {
      return [...state, parseInt(action.payload)].sort();
    }
    case "delete_codeset_id": {
      return state.filter((d) => d != action.payload);
    }
    default:
      return state;
  }
};
const csetEditsReducer = (csetEdits, action) => {};

function hierarchySettingsReducer(state, action) {
  if (!(action && action.type)) return state;
  if (!action.type) return state;
  let {collapsePaths, collapsedDescendantPaths, nested, hideRxNormExtension, hideZeroCounts} = state;
  switch (action.type) {
    case "collapseDescendants": {
      const {row, allRows, collapseAction} = action;
      // this toggles the collapse state of the given row
      const collapse = !get(collapsePaths, row.pathToRoot);
      // collapsePaths are the paths to all the rows the user collapsed
      //  these rows still appear in the table, but their descendants don't
      if (collapseAction === 'collapse') {
        collapsePaths = { ...collapsePaths, [row.pathToRoot]: true };
      } else {
        collapsePaths = { ...collapsePaths };
        delete collapsePaths[row.pathToRoot];
      }
      // collapsedDescendantPaths are all the paths that get hidden, the descendants of all the collapsePaths
      const hiddenRows = flatten(Object.keys(collapsePaths).map(collapsedPath => {
        return allRows.map(r => r.pathToRoot).filter(
            p => p.length > collapsedPath.length && p.startsWith(collapsedPath));
      }));
      collapsedDescendantPaths = fromPairs(hiddenRows.map(p => [p, true]));
      return { ...state, collapsePaths, collapsedDescendantPaths };
    }
    case "nested": {
      return { ...state, nested: action.nested}
    }
    case "hideRxNormExtension": {
      return { ...state, hideRxNormExtension: action.hideRxNormExtension}
    }
    case "hideZeroCounts": {
      return { ...state, hideZeroCounts: action.hideZeroCounts}
    }
    default:
      return state;
  }
}

const SEARCH_PARAM_STATE_CONFIG = {
  scalars: ["editCodesetId", "sort_json", "use_example"],
  global_props_but_not_search_params: ["searchParams", "setSearchParams"],
  serialize: ["csetEditState"],
};
export function searchParamsToObj(searchParams) {
  const qsKeys = Array.from(new Set(searchParams.keys()));
  let sp = {};
  qsKeys.forEach((key) => {
    let vals = searchParams.getAll(key);
    sp[key] = vals.map((v) => (parseInt(v) == v ? parseInt(v) : v)).sort(); // eslint-disable-line
    if (SEARCH_PARAM_STATE_CONFIG.scalars.includes(key)) {
      if (sp[key].length !== 1) {
        throw new Error("Didn't expect that!");
      }
      sp[key] = sp[key][0];
    }
    if (SEARCH_PARAM_STATE_CONFIG.serialize.includes(key)) {
      sp[key] = JSON.parse(sp[key]);
    }
  });

  /* if the editState has changes for a cset no longer selected, it will cause an
      error. just get rid of those changes.
   */
  let fixSearchParams = {}; // don't need to do all this
  if (sp.editCodesetId) {
    if (!(sp.codeset_ids || []).includes(sp.editCodesetId)) {
      delete sp.editCodesetId;
      fixSearchParams.delProps = ["editCodesetId"];
    }
  }
  if (sp.csetEditState) {
    let editState = { ...sp.csetEditState };
    let update = false;
    for (const cid in editState) {
      if (!(sp.codeset_ids || []).includes(parseInt(cid))) {
        delete editState[cid];
        update = true;
      }
    }
    if (update) {
      if (isEmpty(editState)) {
        delete sp.csetEditState;
        fixSearchParams.delProps = [
          ...(fixSearchParams.delProps || []),
          "csetEditState",
        ];
        // updateSearchParams({..._globalProps, delProps: ['csetEditState' ]});
      } else {
        sp.csetEditState = editState;
        fixSearchParams.addProps = { csetEditState: editState };
        // updateSearchParams({..._globalProps, addProps: {csetEditState: editState}});
      }
      //return;
    }
    if (!isEmpty(fixSearchParams)) {
      // didn't need to set up fixSearchParams, just need to know if it's needed
      sp.fixSearchParams = true;
    }
  }
  // console.log({sp});
  return sp;
}
export function updateSearchParams(props) {
  const { addProps = {}, delProps = [], searchParams, setSearchParams } = props;
  let sp = searchParamsToObj(searchParams);
  SEARCH_PARAM_STATE_CONFIG.global_props_but_not_search_params.forEach((p) => {
    delete sp[p];
  });
  delProps.forEach((p) => {
    delete sp[p];
  });
  sp = { ...sp, ...addProps };
  SEARCH_PARAM_STATE_CONFIG.serialize.forEach((p) => {
    if (sp[p]) {
      sp[p] = JSON.stringify(sp[p]);
    }
  });
  const csp = createSearchParams(sp);
  setSearchParams(csp);
}
function Progress(props) {
  return (
    <Box sx={{ display: "flex" }}>
      <CircularProgress {...props} size="35px" />
    </Box>
  );
}

/* TODO: This is a total disaster. do something with it */
function DataWidget(props) {
  const { isLoading, error, isFetching, ukey, url, putData, status } = props;
  // console.log(props);
  const callType = putData ? "Put" : "Get";
  let msg = {};
  // target="_blank" for opening in a new tab
  // rel="noreferrer" for security
  msg.call = (
    <p>
      <a
        href={url}
        target="_blank"
        rel="noreferrer">{url}</a> ({callType})
    </p>
  );
  msg.icon = <Progress variant="determinate" value={100} />;
  if (isLoading) {
    msg.status = "Loading";
    msg.icon = <Progress />;
  }
  if (isFetching) {
    msg.status = "Fetching";
    msg.icon = <Progress />;
  }
  if (error) {
    msg.status = `${error}`;
    msg.icon = <WarningRoundedIcon fontSize="large"/>;
  }
  if (!(isFetching || isLoading || error)) {
    msg.icon = <CheckCircleRounded fontSize="large"/>
  }
  return (
    <Box
      sx={{
        border: "2px solid",
        borderRadius: "10px",
        borderColor: error ? "lightcoral" : "dodgerblue",
        background: error ? "mistyrose" : "aliceblue",
        margin: "20px",
        padding: "20px",
        fontFamily: "sans-serif",
        color: error ? "darkred" : "unset",
        // display: 'flex',
      }}
    >
      <h2 style={{display: "flex", alignItems: "center", gap: 10}}>
        {msg.icon}
        {`${status}`.charAt(0).toUpperCase() + `${status}`.slice(1)}
      </h2>
      {msg.status} <br />
      {msg.call} <br />
    </Box>
  );
}

export function useDataWidget(ukey, url, putData=false) {
  const ax = putData ? () => axiosPut(url, putData) : () => axiosGet(url);
  const axVars = useQuery([ukey], ax);
  let dwProps = { ...axVars, ukey, url, putData };
  const dw = <DataWidget {...dwProps} />;
  return [dw, dwProps]; // axVars.data];
}

export const backend_url = (path) => `${API_ROOT}/${path}`;

export function axiosGet(path, backend = false) {
  let url = backend ? backend_url(path) : path;
  console.log("axiosGet url: ", url);
  return axios.get(url).then((res) => res.data);
}

export function axiosPut(path, data, backend = true) {
  let url = backend ? backend_url(path) : path;
  console.log("axiosPut url: ", url);
  return axios.post(url, data);
}

export function StatsMessage(props) {
  const { codeset_ids = [], all_csets = [], cset_data = {} } = props;
  const { related_csets = [], concepts } = cset_data;

  return (
    <p style={{ margin: 0, fontSize: "small" }}>
      The <strong>{codeset_ids.length} concept sets </strong>
      selected contain{" "}
      <strong>{(concepts || []).length} distinct concepts</strong>. The
      following <strong>{related_csets.length} concept sets </strong>(
      {pct_fmt(related_csets.length / all_csets.length)}) have 1 or more
      concepts in common with the selected sets. Click rows below to select or
      deselect concept sets.
    </p>
  );
}