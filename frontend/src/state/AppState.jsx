import React, {
  createContext,
  useContext,
  useEffect,
  useReducer,
  useState,
} from 'react';
import {PropTypes} from 'prop-types';
import Markdown from 'react-markdown';
import { fromPairs, get, isEmpty, isEqual, pick, } from 'lodash';
// import {compressToEncodedURIComponent} from "lz-string";
// import {createPersistedReducer} from "./usePersistedReducer";
import {
  useSearchParamsState,
  useSessionStorage,
} from './StorageProvider';
import { SOURCE_APPLICATION, SOURCE_APPLICATION_VERSION } from '../env';
import { pct_fmt, setOp } from '../utils';
// import Box from '@mui/material/Box';
// import CircularProgress from '@mui/material/CircularProgress';
import { useDataCache } from './DataCache';
import { Inspector } from 'react-inspector';

export const NEW_CSET_ID = -1;

// const resetFuncs: (() => unknown)[] = [];
const resetFuncs = [];

export const [CodesetIdsProvider, useCodesetIds] = makeProvider(
    { stateName: 'codeset_ids',
      reducer: codesetIdsReducer,
      initialSettings: [],
      storageProviderGetter: useSearchParamsState, });

export const [CidsProvider, useCids] = makeProvider(
    { stateName: 'cids',
      reducer: cidsReducer,
      initialSettings: [],
      storageProviderGetter: useSessionStorage, });

/*
export const [AppOptionsProvider, useAppOptions] = makeProvider(
    { stateName: 'appOptions',
      reducer: appOptionsReducer,
      initialSettings: [],
        // use_example: false,
        // optimization_experiment: '', // probably will never get this working again, for controlling which
                                     // experimental cset/comparison methods are being used
        // comparison_pair: '', // pair of codeset_ids that will be provided on the command line
      storageProviderGetter: useSearchParamsState, });

function appOptionsReducer(state, action) {
  if (!(action && action.type)) return state;
  throw new Error("fix appOptionsReducer");
}
*/

/*
interface GraphOpts {
    specialConceptTreatment: { [key: string]: boolean },
    nested: boolean,
    // hideRxNormExtension: true,
    // hideZeroCounts: false,
    specificNodesCollapsed: number[],
    specificNodesExpanded: number[],
    expandAll: boolean,
}
 */

export const graphOptionsInitialState = {
    specialConceptTreatment: {},
    nested: true,
    // hideRxNormExtension: true,
    // hideZeroCounts: false,
    specificNodesCollapsed: [],
    specificNodesExpanded: [],
};

export const [GraphOptionsProvider, useGraphOptions] = makeProvider(
  { stateName: 'graphOptions',
    reducer: graphOptionsReducer,
    initialSettings: graphOptionsInitialState,
    storageProviderGetter: useSessionStorage, });

export function resetReducers() {
    resetFuncs.forEach(f => f());
}

function codesetIdsReducer( state, action) {
    /* state: number[],
    action: {type: string, codeset_id: number|string,
             codeset_ids: [number|string], resetValue: [number]}) { */
  if (!(action && action.type)) return state;
  console.log(`codesetIdsReducer ${JSON.stringify(action)}`)
  switch (action.type) {
    case "add_codeset_id": {
      return [...state, action.codeset_id]; // .sort();
    }
    case "delete_codeset_id": {
      return state.filter((d) => d != action.codeset_id);
    }
    case "set_all": {
      return [...action.codeset_ids];
    }
    case "reset": {
      return action.resetValue;
    }
    default:
      throw new Error(`unexpected action.type ${action.type}`);
  }
}

function cidsReducer(state, action) {
    // state: number[], action: {type: string, cids: [number|string], resetValue: [void]}) {
  if (!(action && action.type)) return state;
  switch (action.type) {
    case "add": {
      state = setOp('union', state, action.cids);
      break;
    }
    case "delete": {
      state = setOp('difference', state, action.cids);
      break;
    }
    case "set_all": {
      state = [...action.cids.map(Number)];
      break;
    }
    case "reset": {
      return action.resetValue;
    }
    default:
      throw new Error(`unexpected action.type ${action.type}`);
  }
  return state.map(Number);
}

function graphOptionsReducer(state, action) {
  /* state: GraphOpts, action: {
        type: string, graphOptions: GraphOpts, direction: string,
        nodeId: number, specialConceptType: string, resetValue: GraphOpts, }) { */
  if ( ! ( action || {} ).type ) return state;
  // let {collapsePaths, // collapsedDescendantPaths,
  //   nested, hideRxNormExtension, hideZeroCounts} = {...unpersistedDefaultState, ...state};
  const {type, nodeId, specialConceptType, } = action;

  let graphOptions = get(action, 'graphOptions') || state;

  switch (type) {
    // case "graphOptions": { return {...state, graphOptions}; }
    // took this from GraphState, but it still stores graphOptions state there as well as here

    case 'NEW_GRAPH_OPTIONS':
      return graphOptions;
    case 'TOGGLE_NODE_EXPANDED': {
      const expand = new Set(graphOptions.specificNodesExpanded);
      const collapse = new Set(graphOptions.specificNodesCollapsed);
      if (action.direction === 'expand') {
        // TODO: don't do both! only expand if not previously collapsed
        //  See #873
        expand.add(nodeId);
        collapse.delete(nodeId);
      } else if (action.direction === 'collapse') {
        // TODO: don't do both! only collapse if not previously expanded
        expand.delete(nodeId);
        collapse.add(nodeId);
      } else {
        console.error("have to give direction for TOGGLE_NODE_EXPANDED");
      }
      // TODO: quit storing expanded/collapsed nodes in row!!!
      graphOptions = {
        ...graphOptions,
        specificNodesExpanded: [...expand],
        specificNodesCollapsed: [...collapse]
      };
      // gc.toggleNodeExpanded(action.payload.nodeId);
      // graphOptions = {
      //   ...graphOptions,
      //   expandedNodes: {...graphOptions.expandedNodes, [action.payload.nodeId]:!graphOptions.expandedNodes[action.payload.nodeId]}
      // };
      break;
    }
    case 'TOGGLE_OPTION':
      graphOptions = {...graphOptions, specialConceptTreatment: {
        ...graphOptions.specialConceptTreatment,
          [specialConceptType]: !graphOptions.specialConceptTreatment[specialConceptType]}};
      break;
    case 'TOGGLE_EXPAND_ALL':
      graphOptions = {...graphOptions, expandAll:!graphOptions.expandAll};
      // Object.values(gc.nodes).forEach(n => {if (n.hasChildren) n.expanded = graphOptions.expandAll;});
      break;
    case "reset": {
      return action.resetValue;
    }

      /* OLD STUFF
      case "nested": { return {...state, nested: action.nested} }
      case "hideRxNormExtension": { return {...state, hideRxNormExtension: action.hideRxNormExtension} }
      case "hideZeroCounts": { return {...state, hideZeroCounts: action.hideZeroCounts} } */
  }
  return {...state, ...graphOptions};
}

/*
if (process.env.NODE_ENV !== 'production') {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    (window as any).appStateW = {};
}
*/

function makeProvider({stateName, reducer, initialSettings, storageProviderGetter, jsonify=false, }) {
  // makes provider to manage both a regular reducer and a storage provider
  // I think the idea was to put update logic into reducers and try to have storage providers
  //  just emulate localStorage (whether for localStorage, sessionStorage, or querystring)
  const regularReducer = (state, action) => {
    const newState = reducer(state, action);
    const returnState = isEqual(state, newState) ? state : newState;
    window.appStateW[stateName] = returnState;
    return returnState;
  };

  const Context = createContext();
  const Provider = ({children}) => {
    const storageProvider = storageProviderGetter();
    const [state, dispatch] = useReducer(regularReducer, initialSettings, (initial) => {
      let storedSettings = storageProvider.getItem(stateName);
      if (storedSettings) {
        return jsonify ? JSON.stringify(storedSettings) : storedSettings;
      }
      return initial;
    });

    useEffect(() => {
      let newState = jsonify ? JSON.stringify(state) : state;
      storageProvider.setItem(stateName, newState);
    }, [stateName, state]);

    const resetFunc = () => dispatch({type: 'reset', resetValue: initialSettings});
    resetFuncs.push(resetFunc);

    return (
        <Context.Provider value={[state, dispatch]}>
          {children}
        </Context.Provider>
    );
  }
  Provider.propTypes = {
    children: PropTypes.ReactNode,
  }
  const useReducerWithStorage = () => {
    const context = useContext(Context);
    if (!context) {
      throw new Error(`use ${stateName} must be called within a makeProvider provider`);
    }
    return context;
  }

  return [Provider, useReducerWithStorage];
}

const newCsetReducer = (state, action) => {
  /*
      state structure in storageProvider.newCset should look like:
        {
          codeset_id: 1234,
          concept_set_name: 'New Cset',
          ...
          definitions: {
            concept_id: 12345,
            includeDescendants: true,
            ...
          },
          members: {
            // this won't work for a while
          },
        }
   */
  if (!action || !action.type) return state;
  switch (action.type) {
    case "createNewCset": {
      let cset = {
        codeset_id: NEW_CSET_ID,
        concept_set_version_title: "New Cset (Draft)",
        concept_set_name: "New Cset",
        alias: "New Cset",
        source_application: SOURCE_APPLICATION,
        source_application_version: SOURCE_APPLICATION_VERSION,
        codeset_intention: "From VS-Hub",
        limitations: "From VS-Hub",
        update_message: "VS-Hub testing",
        // "codeset_created_at": "2022-07-28 16:14:13.085000+00:00", // will be set by enclave
        // "codeset_created_by": "e64b8f7b-7af8-4b44-a570-557b812c0eeb", // will be set by enclave
        is_draft: true,
        researchers: [],
        counts: {'Expression items': 0},
        intersecting_concepts: 0,
        precision: 0,
        recall: 0,
      };
      /*
      if (state.currentUserId) {
        newCset['on-behalf-of'] = state.currentUserId;
        newCset.researchers = [state.currentUserId];
      }
       */
      return {...cset, definitions: {}};
    }
    case "restore": {
      let definitions = unabbreviateDefinitions(action.newCset.definitions);
      return {...action.newCset, definitions};
    }
    case "reset": {
      return {};
    }

    case "addDefinition": {
      state = {...state, definitions: {...state.definitions, [action.definition.concept_id]: action.definition }}
      break;
    }
    case "addDefinitions": {
      state = {...state, definitions: {...state.definitions, ...action.definitions }}
      break;
    }
    case "deleteDefinition": {
      let definitions = {...state.definitions};
      delete definitions[action.concept_id];
      state = {...state, definitions, };
      break;
    }
  }

  // const restoreUrl = urlWithSessionStorage();
  // provenance: `VS-Hub url: ${urlWithSessionStorage()}`,
  state = {
    ...state,
    counts: {...state.counts, 'Expression items': Object.keys(state.definitions).length},
    // provenance: `VS-Hub url: ${restoreUrl}`, // not really needed currently. not displaying on newCset card because
                                              //  it's too ugly, and no current way to save metadata to enclave
  };
  return state
};


const NewCsetContext = createContext(null);
export function NewCsetProvider({ children }) {
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  const [stateUpdate, setStateUpdate] = useState(); // just to force consumers to rerender
  // const storageProvider = useSearchParamsState();
  const storageProvider = sessionStorage; // for now, for simplicity, just save to sessionStorage
  // const storageProvider = CompressedSessionStorage; // for now, for simplicity, just save to sessionStorage
  let state = JSON.parse(storageProvider.getItem('newCset')) || {};

  const dispatch = action => {
    let latestState = JSON.parse(storageProvider.getItem('newCset'));
    const stateAfterDispatch = newCsetReducer(latestState, action);
    if (!isEqual(latestState, stateAfterDispatch)) {
      storageProvider.setItem('newCset', JSON.stringify(stateAfterDispatch));
      console.log(stateAfterDispatch);
      setStateUpdate(stateAfterDispatch);
    }
    return stateAfterDispatch;
  }
  return (
      <NewCsetContext.Provider value={[state, dispatch]}>
        {children}
      </NewCsetContext.Provider>
  );
}
NewCsetProvider.propTypes = {
  children: PropTypes.ReactNode,
}
export function useNewCset() {
  return useContext(NewCsetContext);
}
export function abbreviateDefinitions(defs) {
  let definitions = {};
  for (let d in defs) {
    let def = defs[d];
    let flags = `${def.includeDescendants ? 'D' :''}` +
        `${def.includeMapped ? 'M' :''}` +
        `${def.isExcluded ? 'X' :''}`;
    definitions[d] = flags;
  }
  return definitions;
}
export function unabbreviateDefinitions(defs) {
  let definitions = {};
  for (let d in defs) {
    let def={item: true, codeset_id: NEW_CSET_ID, concept_id: parseInt(d)};
    let flags = defs[d].split('');
    for (let flag of flags) {
      if (flag === 'D') def.includeDescendants = true;
      if (flag === 'M') def.includeMapped = true;
      if (flag === 'X') def.isExcluded = true;
    }
    definitions[d] = def;
  }
  return definitions;
}

// TODO: make sure this works with useSessionStorage. It probably doesn't
export function getSessionStorage() {
  const sstorage = fromPairs(Object.entries(sessionStorage).map(([k,v]) => ([k, JSON.parse(v)])));
  delete sstorage.AI_buffer;    // added by chrome ai stuff i think...I don't want it
  delete sstorage.AI_sentBuffer;
  return sstorage;
}
export function serializeSessionStorage({newCset} = {}) {
  const sstorage = getSessionStorage();
  newCset = newCset || sstorage.newCset || {};
  if (newCset) {
    newCset = {...newCset};
    delete newCset.provenance;  // it's a mess. not using for now
    newCset.definitions = abbreviateDefinitions(newCset.definitions);
    sstorage.newCset = newCset;
  }
  let sstorageString = JSON.stringify(sstorage);
  /*
  if (zip) {
    // compressing doesn't do much when you have to uri it
    sstorageString = compressToEncodedURIComponent(sstorageString);
  }
   */
  return sstorageString;
}

// TODO: this probably needs fixing after refactor
export function urlWithSessionStorage({newCset} = {}) {
  const sstorageString = serializeSessionStorage({newCset});
  return window.location.href + (window.location.search ? '&' : '?') + `sstorage=${sstorageString}`;
}
export function newCsetProvenance(newCset) {
  return `${SOURCE_APPLICATION} (v${SOURCE_APPLICATION_VERSION}) link: ${urlWithSessionStorage({newCset})}`;
}
export function newCsetAtlasJson(cset, conceptLookup) {
  if (isEmpty(cset.definitions)) {
    return;
  }
  let defs = Object.values(cset.definitions).map(
      d => {
        let item = pick(d, ['includeDescendants', 'includeMapped', 'isExcluded']);
        let concept = conceptLookup[d.concept_id];
        let atlasConcept = {};
        Object.entries(concept).forEach(([k, v]) => {
          atlasConcept[k.toUpperCase()] = v;
        })
        item.concept = atlasConcept;
        return item;
      }
  );
  const jsonObj = {items: defs};
  const atlasJson = JSON.stringify(jsonObj, null, 2);
  return atlasJson;
}

/* more complicated than I thought.... have to save (uncompressed probably) to this
    as well as (compressed) to sessionStorage. and be able to load/decompress everything
export let CompressedSessionStorage = {
  store: sessionStorage,
  setItem: (k, v) => this.store.setItem(k, compress(v)),
  getItem: (k) => this.store.getItem(decompress(k)),
}

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
 */

/*
import { alertsReducer } from '../components/AlertMessages';
const AlertsContext = createContext(null);
const AlertsDispatchContext = createContext(null);
export function AlertsProvider({ children }) {
  const [alerts, dispatch] = useReducer(alertsReducer, {});

  return (
      <AlertsContext.Provider value={alerts}>
        <AlertsDispatchContext.Provider value={dispatch}>
          {children}
        </AlertsDispatchContext.Provider>
      </AlertsContext.Provider>
  );
}
export function useAlerts() {
  return useContext(AlertsContext);
}
export function useAlertsDispatch() {
  return useContext(AlertsDispatchContext);
}
 */

const stateDoc = `
# 2024-08-14, refactoring

State managers / reducer providers and their storage providers
  - DataCache (not a reducer provider)
    - all_csets
    - edges
    - cset_members_items
    - selected_csets
    - researchers
    - concepts
    - ????  not sure if this is up-to-date
  - Uses SearchParamsProvider/useSearchParamsState
    - Provider created using MakeProvider
      - appOptions
      - codeset_ids
  - Uses useSessionStorage
    - newCset -- sessionStorage
    - Provider created using MakeProvider
      - graphOptions
      - cids


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
  use_example

reducers and context
  alerts, graphOptions, newCset
  newCset

DataCache

local to components, useState, etc.

Goals:
  Manage all/

`;

export function ViewCurrentState () {
  const { sp } = useSearchParamsState();
  // const alerts = useAlerts();
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  const [graphOptions, graphOptionsDispatch] = useGraphOptions();
  const newCset = useNewCset();
  const dataCache = useDataCache();
  const sstorage = getSessionStorage();
  return (<div style={{ margin: 30 }}>
    <h1>Current state</h1>

    <h2>query string parameters</h2>
    <Inspector data={sp}/>

    <h2>sessionStorage</h2>
    <Inspector data={sstorage}/>
    <ul>
      <li>Current state URL: <a
        href={urlWithSessionStorage()}>{urlWithSessionStorage()}</a></li>
    </ul>

    <h2>app state (reducers)</h2>
    <Inspector data={{ /*alerts, */ graphOptions, newCset }}/>

    <h2>dataCache</h2>
    <Inspector data={dataCache.getWholeCache()}/>

    <h2>The different kinds of state</h2>
    <Markdown>{stateDoc}</Markdown>
    {/*<pre>{stateDoc}</pre>*/}
  </div>);
}

/* function Progress (props) {
  return (
    <Box sx={{ display: 'flex' }}>
      <CircularProgress {...props} size="35px"/>
    </Box>
  );
} */

export function StatsMessage (props) {
  const { codeset_ids = [], all_csets = [], relatedCsets, concept_ids, } = props;

  const relcsetsCnt = relatedCsets.length;
  return (
    <p style={{ margin: 0, fontSize: 'small' }}>
      The <strong>{codeset_ids.length} concept sets </strong>
      selected contain{' '}
      <strong>{(concept_ids || []).length.toLocaleString()} distinct
        concepts</strong>. The
      following <strong>{relcsetsCnt.toLocaleString()} concept sets </strong>(
      {pct_fmt(relcsetsCnt / all_csets.length)}) have 1 or more
      concepts in common with the selected sets. Click rows below to select or
      deselect concept sets.
    </p>
  );
}
StatsMessage.propTypes = {
  codeset_ids: PropTypes.array,
  all_csets: PropTypes.array,
  relatedCsets: PropTypes.array,
  concept_ids: PropTypes.array,
}
