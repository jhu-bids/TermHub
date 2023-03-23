import React, { createContext, useContext, useReducer, useState, /* useRef, useLayoutEffect, */ } from 'react';
// import useCombinedReducers from 'use-combined-reducers';
import axios from "axios";
import {API_ROOT} from "./env";
import CircularProgress from '@mui/material/CircularProgress';
import Box from '@mui/material/Box';
import { useQuery } from '@tanstack/react-query'
import { createSearchParams, } from "react-router-dom";
import { isEmpty, memoize, } from 'lodash';
import {pct_fmt, } from "./utils";

const DerivedStateContext = createContext();
export function useDerivedState() {
  return useContext(DerivedStateContext);
}
export function DerivedStateProvider(props) {
  const {children, cset_data} = props;
  const {hierarchy={}, selected_csets=[], concepts=[], cset_members_items=[], } = cset_data;
  const appState = useAppState();
  const editCsetState = appState.getSliceState('editCset');
  let derivedState = {};

  return (
      <DerivedStateContext.Provider value={derivedState} >
        {children}
      </DerivedStateContext.Provider>
  );
}
// going to try to refactor all the state stuff using reducers and context, but still save to url
const CombinedReducersContext = createContext();
export function AppStateProvider({children}) {
  const reducers = {
    contentItems: useReducer(contentItemsReducer, defaultContentItems),
    codeset_ids:  useReducer(codeset_idsReducer, []),
    editCset:     useReducer(editCsetReducer),
  }
  const getters = {
    getSliceState : (slice) => reducers[slice][0],
    getSliceDispatch : (slice) => reducers[slice][1],
    getSlice: (slice) => reducers[slice],
    getSliceNames: () => Object.keys(reducers),
    getReducers: () => reducers,
    getState: () => Object.fromEntries(Object.entries(reducers).map(([k,v]) => [k, v[0]])),
  }
  return (
      <CombinedReducersContext.Provider value={getters}>
        {children}
      </CombinedReducersContext.Provider>
  );
}
export function useAppState() {
  return useContext(CombinedReducersContext);
}
/*
const StateContext = createContext();
const DispatchContext = createContext();
export function AppStateProvider({children}) {
  const [state, dispatch] = useCombinedReducers({
    contentItems: useReducer(contentItemsReducer, defaultContentItems),
    codeset_ids: useReducer(codeset_idsReducer, []),
    editCsetReducer: useReducer(editCsetReducer),
  });

  return (
      <DispatchContext.Provider value={dispatch}>
        <StateContext.Provider value={state}>
          {children}
        </StateContext.Provider>
      </DispatchContext.Provider>
  );
}
export function useAppState() {
  return useContext(StateContext);
}
export function useAppStateDispatch() {
  return useContext(DispatchContext);
}
*/
const editCsetReducer = (state, action) => {
  if (!(action && action.type)) return state;
  const type = getTypeForSlice('editCset', action.type);
  if (!type) return state;
  if (state === action.payload) return null; // if already set to this codeset_id, turn off
  return action.payload;
};
function DummyComponent({foo}) {
  return <h3>dummy component: {foo}</h3>
}
const defaultContentItems = [ // see ContentItems
  {
    name: 'dummy',
    show: false,
    Component: DummyComponent,
    props: {foo: 'bar'},
  }
];
const getTypeForSlice = memoize((slice, actionType) => {
  const [reducerSlice, type] = actionType.split(/-(.*)/s); // https://stackoverflow.com/questions/4607745/split-string-only-on-first-instance-of-specified-character
  return (reducerSlice === slice) && type;
});

const contentItemsReducer = (state=[], action) => {
  console.log({state,action});
  if (!(action && action.type)) return state;
  const type = getTypeForSlice('contentItems', action.type);
  if (!type) return state;
  if (['show','hide','toggle'].includes(type)) {
    const idx = state.findIndex(o => o.name === action.name);
    let option = {...state[idx]};
    switch (type) {
      case 'show': option.show = true; break;
      case 'hide': option.show = false; break;
      case 'toggle': option.show = !option.show;
    }
    state[idx] = option;
    return [...state];
  }
  if (type === 'new') {
    return [...state, action.payload];
  }
  throw new Error(`invalid action.type: ${action}`)
};

// actions
const codeset_idsReducer = (state, action) => {
  if (!(action && action.type)) return state;
  const type = getTypeForSlice('contentItem', action.type);
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

const combineReducers = (slices) => (state, action) =>
    // from https://stackoverflow.com/questions/59200785/react-usereducer-how-to-combine-multiple-reducers
  Object.keys(slices).reduce(
    (acc, prop) => ({
      ...acc,
      [prop]: slices[prop](acc[prop], action),
    }),
    state
  );

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
