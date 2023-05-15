/*
  from state-management-refactor 9b5b92b2 commit:
- in the middle of big refactor of state management and UI. not totally
  broken at the moment.
- eventually moving all the querystring state stuff to AppStateProvider
  along with some other state not currently managed in querystring
- after app state and data state are ready, have another provider for
  DerivedState
- Not currently using contentItems. May come back to it after more immediate
  requirements handled and after doing some more explicit design work.
  ContentItems are going to be pieces of UI whose state will be managed
  in AppState. The (very rough) idea is that there will be buttons or
  something to let user show some piece of content, and then a close
  icon will make it disappear and make the button reappear.
 */
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
import { createSearchParams } from "react-router-dom";
import { isEmpty, get, memoize, pullAt } from "lodash";
import { pct_fmt } from "./utils";
import WarningRoundedIcon from '@mui/icons-material/WarningRounded';
import { CheckCircleRounded } from "@mui/icons-material";
// import {contentItemsReducer, defaultContentItems} from "./contentControl";

class DataAccess {
  constructor() {
    this.cache = this.loadCache() ?? {} // just a big js obj, add functionality to persist it
  }
  saveCache = () => {
    localStorage.setItem('dataAccessor', JSON.stringify(this.cache));
    return null;
  }
  loadCache = () => {
    return JSON.parse(localStorage.getItem('dataAccessor'));
  }
  /* concept stuff as methods here. not sure if it would be worthwhile to do any
      subclassing to handle specific data objects (codesets, concepts, subgraphs, etc.)
    concepts will be a slice of the cache, looking like
    cache: {
      concepts: {
        123: {
          concept_id: 123,
          concept_name: ...
        }
        456: {
          concept_id: 456,
          concept_name: ...
        }
      }
   }
   */
  async getConcepts(concept_ids=[], shape='array' /* or obj */) {

    let allCachedConcepts = get(this.cache, 'concepts', {});
    let cachedConcepts = {};
    let uncachedConceptIds = [];
    let uncachedConcepts = {};
    concept_ids.forEach(concept_id => {
      if (allCachedConcepts[concept_id]) {
        cachedConcepts[concept_id] = allCachedConcepts[concept_id];
      } else {
        uncachedConceptIds.push(concept_id);
      }
    })
    if (uncachedConceptIds.length) {
      const url = backend_url(
          "get-concepts?" + uncachedConceptIds.map(c=>`id=${c}`).join("&")
      );
      const queryKey = ['concepts', ...concept_ids];
      // https://tanstack.com/query/v4/docs/react/reference/QueryClient#queryclientfetchquery
      const data = await this.fetch(
          'concepts',
          url,
          queryKey,
          this.store_concepts_to_cache);
      data.forEach(c => uncachedConcepts[c.concept_id] = c);
    }
    const results = { ...cachedConcepts, ...uncachedConcepts };
    const not_found = concept_ids.filter(
        x => !Object.values(results).map(c=>c.concept_id).includes(x));
    if (not_found.length) {
      // TODO: let user see warning somehow
      console.warn("Warning in DataAccess.getConcepts: couldn't find concepts for " +
            not_found.join(', '))
    }

    if (shape === 'array') {
      return Object.values(results);
    }
    return results;
  }
  store_concepts_to_cache = (concepts=[]) => {
    concepts.forEach(c => {
      this.cache.concepts = this.cache.concepts ?? {};
      this.cache.concepts[c.concept_id] = c;
    })
  }
  async getSubgraphEdges(concept_ids=[]) {
    // edges are more complicated than concepts, not trying to cache individual
    // edges like caching individual concepts above. for right now, cache will
    // only hold most recent subgraph call, which is pretty useless (already
    //   cached by queryClient/persistor anyway)

    const url = backend_url(
        "subgraph?" + concept_ids.map(c=>`id=${c}`).join("&")
    );
    const queryKey = ['subgraph', ...concept_ids];
    // https://tanstack.com/query/v4/docs/react/reference/QueryClient#queryclientfetchquery
    const data = await this.fetch(
        'subgraph',
        url,
        queryKey,
       data => this.cache.subgraph = data);
    return data;
  }
  async fetch(path,
              url,
              queryKey /* can be array or str, i think */,
              cacheSaveFunc) {
    console.log("fetching", url);
    const queryFn = () => axiosGet(url);
    const data = await queryClient.fetchQuery({ queryKey, queryFn })
    try {
      cacheSaveFunc(data);
      return data;
    } catch (error) {
      console.log(error);
    }
    return data;
  }
}
export const dataAccessor = new DataAccess();
window.addEventListener("beforeunload", dataAccessor.saveCache);
// window.onload = dataAccessor.loadCache; happens at wrong time. moving this to constructor
// for debugging
window.dataAccessorW = dataAccessor;


const DerivedStateContext = createContext(null);
export function DerivedStateProvider(props) {
  // when I put this provider up at the App level, it didn't update
  //    but at the CsetComparisonPage level it did. don't know why
  const { children, cset_data } = props;
  const {
    hierarchy = {},
    selected_csets = [],
    concepts = [],
    cset_members_items = [],
  } = cset_data;
  const appState = useAppState();
  // const editCsetState = appState.getSliceState('editCset');
  const hierarchySettings = appState.getSliceState("hierarchySettings");
  const { collapsed, displayOption } = hierarchySettings;

  const rowData = makeHierarchyRows({
    concepts,
    selected_csets,
    cset_members_items,
    hierarchy,
    collapsed,
  });

  let derivedState = {
    foo: "bar",
    comparisonRowData: rowData,
  };
  // console.log(derivedState);

  return (
    <DerivedStateContext.Provider value={derivedState}>
      {children}
    </DerivedStateContext.Provider>
  );
}
export function useDerivedState() {
  return useContext(DerivedStateContext);
}
// going to try to refactor all the state stuff using reducers and context, but still save to url

export function useStateSlice(slice) {
  const appState = useAppState();
  const [state, dispatch] = appState.getSlice(slice);
  return { state, dispatch };  // should probably return array instead of object?
}
const CombinedReducersContext = createContext(null);
export function AppStateProvider({ children }) {
  const reducers = {
    // contentItems: useReducer(contentItemsReducer, defaultContentItems),
    codeset_ids: useReducer(codeset_idsReducer, []),
    editCset: useReducer(editCsetReducer),
    // more stuff needed
    hierarchySettings: useReducer(hierarchySettingsReducer, {
      displayOption: "fullHierarchy", // or 'flat'   not currently using?
      collapsed: {},
    }),
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
const csetEditsReducer = (csetEdits, action) => {};

function hierarchySettingsReducer(state, action) {
  if (!(action && action.type)) return state;
  if (!action.type) return state;
  switch (action.type) {
    case "setCollapsed": {
      const collapsed = action.collapsed;
      return { ...state, collapsed };
    }
    default:
      return state;
  }
}

// const DataContext = createContext(null);
const SPContext = createContext(null);
const SPDispatchContext = createContext(null);

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
export function clearSearchParams(props) {
  const { searchParams, setSearchParams } = props;
  const sp = searchParamsToObj(searchParams);
  if (!isEmpty(sp)) {
    setSearchParams(createSearchParams({}));
  }
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
  console.log(props);
  const callType = putData ? "Put" : "Get";
  let msg = {};
  msg.call = (
    <p>
      <a href={url}>{ukey}</a> ({callType})
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

export function makeHierarchyRows({
  concepts,
  selected_csets,
  cset_members_items,
  hierarchy,
  collapsed = {},
}) {
  if (
    isEmpty(concepts) ||
    isEmpty(selected_csets) ||
    isEmpty(cset_members_items)
  ) {
    return;
  }
  const conceptsMap = Object.fromEntries(
    concepts.map((d) => [d.concept_id, d])
  );
  return traverseHierarchy({ hierarchy, concepts: conceptsMap, collapsed });
}

function makeRowData({
  concepts,
  selected_csets,
  cset_members_items,
  hierarchy,
  collapsed = {},
}) {
  // replaced by makeHierarchyRows? --- this version helps with nested flag and row count message
  if (
    isEmpty(concepts) ||
    isEmpty(selected_csets) ||
    isEmpty(cset_members_items)
  ) {
    return;
  }

  const conceptsMap = Object.fromEntries(
    concepts.map((d) => [d.concept_id, d])
  );
  let _displayOptions = {
    fullHierarchy: {
      rowData: traverseHierarchy({
        hierarchy,
        concepts: conceptsMap,
        collapsed,
      }),
      nested: true,
      msg: " lines in hierarchy",
    },
    flat: {
      rowData: concepts,
      nested: false,
      msg: " flat",
    },
    /*
    csetConcepts: {
      rowData: traverseHierarchy({hierarchy, concepts: csetConcepts, collapsed, }),
      nested: true,
      msg: ' concepts in selected csets',
    },
     */
  };

  for (let k in _displayOptions) {
    let opt = _displayOptions[k];
    opt.msg = opt.rowData.length + opt.msg;
  }
  // setDisplayOptions(_displayOptions);
  window.dopts = _displayOptions;
  return _displayOptions;
}
/*
function hierarchyToFlatCids(h) {
  function f(ac) {
    ac.keys = [...ac.keys, ...Object.keys(ac.remaining)];
    const r = Object.values(ac.remaining).filter(d => d);
    ac.remaining = {};
    r.forEach(o => ac.remaining = {...ac.remaining, ...o});
    return ac;
  }
  let ac = {keys: [], remaining: h};
  while(!isEmpty(ac.remaining)) {
    console.log(ac);
    ac = f(ac);
  }
  return uniq(ac.keys.map(k => parseInt(k)));
}
 */

function traverseHierarchy({ hierarchy, concepts, collapsed }) {
  let rowData = [];
  let blanks = [];
  let traverse = (o, pathToRoot = [], level = 0) => {
    // console.log({o, pathToRoot, level});
    Object.keys(o).forEach((k) => {
      k = parseInt(k);
      let row = { ...concepts[k], level, pathToRoot: [...pathToRoot, k] };
      if (!concepts[k]) {
        blanks.push(rowData.length);
      }
      rowData.push(row);
      if (o[k] && typeof (o[k] === "object")) {
        row.has_children = true;
        if (!collapsed[row.pathToRoot]) {
          traverse(o[k], row.pathToRoot, level + 1);
        }
      }
    });
  };
  traverse(hierarchy);
  pullAt(rowData, blanks);
  return rowData;
}
