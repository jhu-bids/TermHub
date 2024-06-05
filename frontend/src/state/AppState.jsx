import React, {createContext, useCallback, useContext, useReducer, useState} from "react";
import {flatten, fromPairs, get, pick, isEqual, isEmpty} from "lodash";
// import {compressToEncodedURIComponent} from "lz-string";
// import {createPersistedReducer} from "./usePersistedReducer";
import {alertsReducer} from "../components/AlertMessages";
import {useSearchParamsState, useSessionStorage} from "./StorageProvider";
import {SOURCE_APPLICATION, SOURCE_APPLICATION_VERSION} from "../env";
import {createSearchParams, useSearchParams} from "react-router-dom";

export const NEW_CSET_ID = -1;

const codesetIdsReducer = (state, action) => {
  if (!(action && action.type)) return state;
  switch (action.type) {
    case "add_codeset_id": {
      return [...state, parseInt(action.codeset_id)]; // .sort();
    }
    case "delete_codeset_id": {
      return state.filter((d) => d != action.codeset_id);
    }
    case "set_all": {
      return [...action.codeset_ids];
    }
    default:
      throw new Error(`unexpected action.type ${action.type}`);
  }
};
const CodesetIdsContext = createContext(null);
export function CodesetIdsProvider({ children }) {
  const storageProvider = useSearchParamsState();
  let state = storageProvider.getItem('codeset_ids') || [];

  const dispatch = action => {
    let latestState = storageProvider.getItem('codeset_ids') || [];
    const stateAfterDispatch = codesetIdsReducer(latestState, action);
    if (!isEqual(latestState, stateAfterDispatch)) {
      storageProvider.setItem('codeset_ids', stateAfterDispatch);
    }
  }
  return (
      <CodesetIdsContext.Provider value={[state, dispatch]}>
        {children}
      </CodesetIdsContext.Provider>
  );
}
export function useCodesetIds() {
  return useContext(CodesetIdsContext);
}


const cidsReducer = (state, cids) => {
  return cids || state;
};
const CidsContext = createContext(null);
export function CidsProvider({ children }) {
  const storageProvider = useSearchParamsState();
  let state = storageProvider.getItem('cids') || [];

  const dispatch = action => {
    let latestState = storageProvider.getItem('cids') || [];
    const stateAfterDispatch = cidsReducer(latestState, action);
    if (!isEqual(latestState, stateAfterDispatch)) {
      storageProvider.setItem('cids', stateAfterDispatch);
    }
  }
  return (
      <CidsContext.Provider value={[state, dispatch]}>
        {children}
      </CidsContext.Provider>
  );
}
export function useCids() {
  return useContext(CidsContext);
}

function settingsReducer(state, action) {
  if ( ! ( action || {} ).type ) return state;
  // let {collapsePaths, // collapsedDescendantPaths,
  //   nested, hideRxNormExtension, hideZeroCounts} = {...unpersistedDefaultState, ...state};

  let { graphOptions } = state;
  let { specialConceptTreatment, expandAll, specificNodesCollapsed, specificNodesExpanded, } = graphOptions; // hide, show

  let {type, nodeId, specialConceptType, } = action;
  // this is all for graphOptions appSettings, but someday i'll want appSettings besides graphOptions, rights?

  switch (type) {
    // case "graphOptions": { return {...state, graphOptions}; }
      // took this from GraphState, but it still stores graphOptions state there as well as here
    case 'TOGGLE_NODE_EXPANDED':
      console.error("have to fix this and persist nodes expanded");
      // gc.toggleNodeExpanded(action.payload.nodeId);
      // graphOptions = {
      //   ...graphOptions,
      //   expandedNodes: {...graphOptions.expandedNodes, [action.payload.nodeId]:!graphOptions.expandedNodes[action.payload.nodeId]}
      // };
      break;
    case 'TOGGLE_OPTION':
      graphOptions = {...graphOptions, specialConceptTreatment: {
        ...graphOptions.specialConceptTreatment,
          [specialConceptType]:!graphOptions.specialConceptTreatment[specialConceptType]}};
      break;
    case 'TOGGLE_EXPAND_ALL':
      graphOptions = {...graphOptions, expandAll:!graphOptions.expandAll};
      // Object.values(gc.nodes).forEach(n => {if (n.hasChildren) n.expanded = graphOptions.expandAll;});
      break;

      // OLD STUFF
      /*
      case "collapseDescendants": {
        console.log(state, action);
        // this toggles the collapse state of the given row
        const {row, allRows, collapseAction} = action;
        const collapse = !get(collapsePaths, row.pathToRoot);
        // collapsePaths are the paths to all the rows the user collapsed
        //  these rows still appear in the table, but their descendants don't
        if (collapseAction === 'collapse') {
          collapsePaths = {...collapsePaths, [row.pathToRoot]: true};
        } else {
          collapsePaths = {...collapsePaths};
          delete collapsePaths[row.pathToRoot];
        }
        return {...state, collapsePaths /*, collapsedDescendantPaths * /};
      }
    case "nested": {
      return {...state, nested: action.nested}
    }
    case "hideRxNormExtension": {
      return {...state, hideRxNormExtension: action.hideRxNormExtension}
    }
    case "hideZeroCounts": {
      return {...state, hideZeroCounts: action.hideZeroCounts}
    }
    default:
      return state;
      */
  }
  return {...state, graphOptions};
}
const SettingsContext = createContext(null);
export function SettingsProvider({ children }) {    // settings 1
  const initialSettings = {
    graphOptions: {
      specialConceptTreatment: {},
      nested: true,
      // hideRxNormExtension: true,
    }
    // collapsePaths: {}, // collapsedDescendantPaths: {}, // hideZeroCounts: false,
  };
  const storageProvider = useSearchParamsState();
  let state = storageProvider.getItem('appSettings') || initialSettings;

  const dispatch = action => {
    let latestState = storageProvider.getItem('appSettings') || initialSettings;
    const stateAfterDispatch = settingsReducer(latestState, action);
    if (!isEqual(latestState, stateAfterDispatch)) {
      storageProvider.setItem('appSettings', stateAfterDispatch);
    }
  }
  return (
      <SettingsContext.Provider value={[state, dispatch]}>
        {children}
      </SettingsContext.Provider>
  );
}
export function useSettings() {
  return useContext(SettingsContext);
}
/*
export function useHierarchySettings() {
  const unpersistedDefaultState = {
    specialConceptTreatment: {},
    nested: true,
    // collapsePaths: {},
    // collapsedDescendantPaths: {},
    hideRxNormExtension: true,
    // hideZeroCounts: false,
  };
  const storageProvider = useSearchParamsState();
  // const storageProvider = useSessionStorage();
  const usePersistedReducer = createPersistedReducer('hierarchySettings',
    storageProvider, unpersistedDefaultState);

  // reducer was here

  const [state, dispatch] = usePersistedReducer(hierarchySettingsReducer);
  return [state, dispatch];
}
 */

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
    }
    case "addDefinitions": {
      state = {...state, definitions: {...state.definitions, ...action.definitions }}
    }
    case "deleteDefinition": {
      let definitions = {...state.definitions};
      delete definitions[action.concept_id];
      state = {...state, definitions, };
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