/*
  from state-management-refactor 9b5b92b2 commit:
- in the middle of big refactor of state management and UI. not totally
  broken at the moment.
- eventually moving all the querystring state stuff to AppStateProvider
  along with some other state not currently managed in querystring
- after app state and data state are ready, have another provider for
  DerivedState
- ContentItems are going to be pieces of UI whose state will be managed
  in AppState. The (very rough) idea is that there will be buttons or
  something to let user show some piece of content, and then a close
  icon will make it disappear and make the button reappear.
 */
import React, { createContext, useContext, useReducer, useState, /* useRef, useLayoutEffect, */ } from 'react';
// import useCombinedReducers from 'use-combined-reducers';
import axios from "axios";
import {API_ROOT} from "./env";
import CircularProgress from '@mui/material/CircularProgress';
import Box from '@mui/material/Box';
import { useQuery } from '@tanstack/react-query'
import { createSearchParams, } from "react-router-dom";
import { isEmpty, memoize, pullAt} from 'lodash';
import {pct_fmt, } from "./utils"
import {contentItemsReducer, defaultContentItems} from "./contentControl";

const DerivedStateContext = createContext(null);
export function DerivedStateProvider(props) {
  // when I put this provider up at the App level, it didn't update
  //    but at the CsetComparisonPage level it did. don't know why
  const {children, cset_data} = props;
  const {hierarchy={}, selected_csets=[], concepts=[], cset_members_items=[], } = cset_data;
  const appState = useAppState();
  // const editCsetState = appState.getSliceState('editCset');
  const hierarchySettings = appState.getSliceState('hierarchySettings');
  const {collapsed, displayOption} = hierarchySettings;

  const rowData = makeHierarchyRows({
    concepts, selected_csets, cset_members_items, hierarchy, collapsed});

  let derivedState = {
    foo: 'bar',
    comparisonRowData: rowData,
  };
  // console.log(derivedState);

  return (
      <DerivedStateContext.Provider value={derivedState} >
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
  return {state, dispatch};
}
const CombinedReducersContext = createContext(null);
export function AppStateProvider({children}) {
  const reducers = {
    contentItems: useReducer(contentItemsReducer, defaultContentItems),
    codeset_ids:  useReducer(codeset_idsReducer, []),
    editCset:     useReducer(editCsetReducer),
    // more stuff needed
    hierarchySettings: useReducer(hierarchySettingsReducer, {
      displayOption: 'fullHierarchy', // or 'flat'
      collapsed: {},
    })
  }
  const getters = {
    getSliceState : (slice) => reducers[slice][0],
    getSliceDispatch : (slice) => reducers[slice][1],
    getSlice: (slice) => reducers[slice],
    getSliceNames: () => Object.keys(reducers),
    getReducers: () => reducers,
    getState: () => Object.fromEntries(Object.entries(reducers).map(([k,v]) => [k, v[0]])),
  }
  /*  before doing the getter stuff for the slices, i was having the slice name be a prefix on the action.type
      probably won't return to this, but keeping around for a bit
  const getTypeForSlice = memoize((slice, actionType) => {
    const [reducerSlice, type] = actionType.split(/-(.*)/s); // https://stackoverflow.com/questions/4607745/split-string-only-on-first-instance-of-specified-character
    return (reducerSlice === slice) && type;
  });
    if (!(action && action.type)) return state;
    const type = getTypeForSlice('contentItems', action.type);
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
const codeset_idsReducer = (state, action) => {
  if (!(action && action.type)) return state;
  switch (action.type) {
    case 'add_codeset_id': {
      return [...state, parseInt(action.payload)].sort();
    }
    case 'delete_codeset_id': {
      return state.filter(d => d != action.payload);
    }
    default:
      return state;
  }
};
const csetEditsReducer = (csetEdits, action) => {
};

function hierarchySettingsReducer(state, action) {
  /*
  const [collapsed, setCollapsed] = useState({});

  function toggleCollapse(row) {
    let _collapsed = {...collapsed, [row.pathToRoot]: !get(collapsed, row.pathToRoot.join(','))};
    setCollapsed(_collapsed);
  }
   */
  return state;
}

// const DataContext = createContext(null);
const SPContext = createContext(null);
const SPDispatchContext = createContext(null);

const SEARCH_PARAM_STATE_CONFIG = {
  scalars: ['editCodesetId', 'sort_json'],
  global_props_but_not_search_params: ['searchParams', 'setSearchParams'],
  serialize: ['csetEditState'],
}
function searchParamsToObj(searchParams) {
  const qsKeys = Array.from(new Set(searchParams.keys()));
  let sp = {};
  qsKeys.forEach(key => {
    let vals = searchParams.getAll(key);
    sp[key] = vals.map(v => parseInt(v) == v ? parseInt(v) : v).sort(); // eslint-disable-line
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
      fixSearchParams.delProps = ['editCodesetId'];
    }
  }
  if (sp.csetEditState) {
    let editState = {...sp.csetEditState};
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
        fixSearchParams.delProps = [...(fixSearchParams.delProps||[]), 'csetEditState'];
        // updateSearchParams({..._globalProps, delProps: ['csetEditState' ]});
      } else {
        sp.csetEditState = editState;
        fixSearchParams.addProps = {csetEditState: editState};
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
function updateSearchParams(props) {
  const {addProps={}, delProps=[], searchParams, setSearchParams, } = props;
  let sp = searchParamsToObj(searchParams);
  SEARCH_PARAM_STATE_CONFIG.global_props_but_not_search_params.forEach(
      p => { delete sp[p]; } );
  delProps.forEach( p => { delete sp[p]; } );
  sp = {...sp, ...addProps};
  SEARCH_PARAM_STATE_CONFIG.serialize.forEach( p => {
    if (sp[p]) {
      sp[p] = JSON.stringify(sp[p]);
    }
  })
  const csp = createSearchParams(sp);
  setSearchParams(csp);
}
function clearSearchParams(props) {
  const {searchParams, setSearchParams, } = props;
  const sp = searchParamsToObj(searchParams);
  if (! isEmpty(sp)) {
    setSearchParams(createSearchParams({}));
  }
}
function Progress(props) {
  return (
    <Box sx={{ display: 'flex' }}>
      <CircularProgress {...props} />
    </Box>
  );
}

/* TODO: This is a total disaster. do something with it */
function DataWidget(props) {
  const { isLoading, error, isFetching, ukey, url, putData, status } = props;
  console.log(props);
  const callType = putData ? 'Put' : 'Get';
  let msg = {}
  msg.call = <p><a href={url}>{ukey}</a> ({callType})</p>
  msg.icon = <Progress variant="determinate" value={100} />;
  if (isLoading) {
    msg.status = 'Loading';
    msg.icon = <Progress/>;
  }
  if (isFetching) {
    msg.status = 'Fetching';
    msg.icon = <Progress/>;
  }
  if (error) {
    msg.status = `Error: ${error}`;
    msg.icon = <p>(need error icon?)</p>;
  }
  return (
      <Box sx={{
        border: '2px solid blue', margin: '20px', padding: '20px',
        // display: 'flex',
      }} >
        <h2>{status}</h2>
      {msg.status} <br/>
        {msg.call} <br/>
        {msg.icon}
      </Box>
  );
}

function useDataWidget(ukey, url, putData) {
  const ax = putData ? ()=>axiosPut(url, putData) : ()=>axiosGet(url)
  const axVars = useQuery([ukey], ax);
  let dwProps = {...axVars, ukey, url, putData, };
  const dw = <DataWidget {...dwProps} />;
  return [dw, dwProps, ]; // axVars.data];
}

const backend_url = path => `${API_ROOT}/${path}`

function axiosGet(path, backend=false) {
  let url = backend ? backend_url(path) : path;
  console.log('axiosGet url: ', url);
  return axios.get(url).then((res) => res.data);
}

function axiosPut(path, data, backend=true) {
  let url = backend ? backend_url(path) : path;
  console.log('axiosPut url: ', url);
  return axios.post(url, data);
}

function StatsMessage(props) {
  const {codeset_ids=[], all_csets=[], cset_data={}} = props;
  const {related_csets=[], concepts } = cset_data;

  return <p style={{margin:0, fontSize: 'small',}}>The <strong>{codeset_ids.length} concept sets </strong>
    selected contain <strong>{(concepts||[]).length} distinct concepts</strong>.
    The following <strong>{related_csets.length} concept sets </strong>
    ({ pct_fmt(related_csets.length / all_csets.length) })
    have 1 or more concepts in common with the selected sets.
    Click rows below to select or deselect concept sets.</p>
}


export {
  StatsMessage, searchParamsToObj, backend_url, axiosGet, axiosPut, useDataWidget,
  updateSearchParams, clearSearchParams,
};

function makeHierarchyRows({concepts, selected_csets, cset_members_items, hierarchy, collapsed={}}) {
  if (isEmpty(concepts) || isEmpty(selected_csets) || isEmpty(cset_members_items)) {
    return;
  }
  const conceptsMap = Object.fromEntries(concepts.map(d => [d.concept_id, d]));
  return traverseHierarchy({hierarchy, concepts: conceptsMap, collapsed, });
}

function makeRowData({concepts, selected_csets, cset_members_items, hierarchy, collapsed={}}) {
  // replaced by makeHierarchyRows? --- this version helps with nested flag and row count message
  if (isEmpty(concepts) || isEmpty(selected_csets) || isEmpty(cset_members_items)) {
    return;
  }

  const conceptsMap = Object.fromEntries(concepts.map(d => [d.concept_id, d]));
  let _displayOptions = {
    fullHierarchy: {
      rowData: traverseHierarchy({hierarchy, concepts: conceptsMap, collapsed, }),
      nested: true,
      msg: ' lines in hierarchy',
    },
    flat: {
      rowData: concepts,
      nested: false,
      msg: ' flat',
    },
    /*
    csetConcepts: {
      rowData: traverseHierarchy({hierarchy, concepts: csetConcepts, collapsed, }),
      nested: true,
      msg: ' concepts in selected csets',
    },
     */
  }

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

function traverseHierarchy({hierarchy, concepts, collapsed, }) {
  let rowData = [];
  let blanks = [];
  let traverse = (o, pathToRoot=[], level=0) => {
    // console.log({o, pathToRoot, level});
    Object.keys(o).forEach(k => {
      k = parseInt(k);
      let row = {...concepts[k], level, pathToRoot: [...pathToRoot, k]};
      if (!concepts[k]) {
        blanks.push(rowData.length);
      }
      rowData.push(row);
      if (o[k] && typeof(o[k] === 'object')) {
        row.has_children = true;
        if (!collapsed[row.pathToRoot]) {
          traverse(o[k], row.pathToRoot, level+1);
        }
      }
    })
  }
  traverse(hierarchy);
  pullAt(rowData, blanks);
  return rowData;
}
