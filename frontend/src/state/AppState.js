import React, {createContext, useContext, useReducer, useState} from "react";
import {flatten, fromPairs, get, pick, isEqual, isEmpty} from "lodash";
import {createPersistedReducer} from "./usePersistedReducer";
import {alertsReducer} from "../components/AlertMessages";
import {useSearchParamsState} from "./SearchParamsProvider";
import {SOURCE_APPLICATION, SOURCE_APPLICATION_VERSION} from "../env";

export const NEW_CSET_ID = -1;

const codesetIdsReducer = (state, action) => {
  if (!(action && action.type)) return state;
  switch (action.type) {
    case "add_codeset_id": {
      return [...state, parseInt(action.codeset_id)].sort();
    }
    case "delete_codeset_id": {
      return state.filter((d) => d != action.codeset_id);
    }
    case "set_all": {
      return [...action.codeset_ids];
    }
      /*  ends up toggling multiple times now that not using context provider
      case "toggle": {
        if (state.includes(action.codesetId)) {
          return state.filter(d => d !== action.codesetId);
        }
        return [...state, parseInt(action.codesetId)].sort();
      }
       */
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
      debugger;
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

/*
Don't need Context provider since the reducer is getting persisted anyway
But in case this doesn't work, here's all the code for reverting to context provider

const HierarchySettingsContext = createContext(null);
const HierarchySettingsDispatchContext = createContext(null);
// since hierarchySettings is getting saved to url and maybe
//  having problems because of saving the initial value to url,
//  let's try to just save differences from the default to url
export function HierarchySettingsProvider({ children }) {
  [all the stuff that's now in useHierarchySettings]
  return (
    <HierarchySettingsContext.Provider value={state}>
      <HierarchySettingsDispatchContext.Provider value={dispatch}>
        {children}
      </HierarchySettingsDispatchContext.Provider>
    </HierarchySettingsContext.Provider>
  );
}
export function useHierarchySettings() {
  return useContext(HierarchySettingsContext);
}
export function useHierarchySettingsDispatch() {
  return useContext(HierarchySettingsDispatchContext);
}
 */
export function useHierarchySettings() {
  const unpersistedDefaultState = { nested: true, collapsePaths: {},
    collapsedDescendantPaths: {}, hideRxNormExtension: true, hideZeroCounts: false, };
  const storageProvider = useSearchParamsState();
  const usePersistedReducer = createPersistedReducer('hierarchySettings',
    storageProvider, unpersistedDefaultState);

  function hierarchySettingsReducer(state, action) {
    if ( ! ( action || {} ).type ) return state;
    let {collapsePaths, collapsedDescendantPaths,
      nested, hideRxNormExtension, hideZeroCounts} = {...unpersistedDefaultState, ...state};
    switch (action.type) {
      case "collapseDescendants": {
        const {row, allRows, collapseAction} = action;
        // this toggles the collapse state of the given row
        const collapse = !get(collapsePaths, row.pathToRoot);
        // collapsePaths are the paths to all the rows the user collapsed
        //  these rows still appear in the table, but their descendants don't
        if (collapseAction === 'collapse') {
          collapsePaths = {...collapsePaths, [row.pathToRoot]: true};
        } else {
          collapsePaths = {...collapsePaths};
          delete collapsePaths[row.pathToRoot];
        }
        // collapsedDescendantPaths are all the paths that get hidden, the descendants of all the collapsePaths
        const hiddenRows = flatten(Object.keys(collapsePaths).map(collapsedPath => {
          return allRows.map(r => r.pathToRoot).filter(
              p => p.length > collapsedPath.length && p.startsWith(collapsedPath));
        }));
        collapsedDescendantPaths = fromPairs(hiddenRows.map(p => [p, true]));
        return {...state, collapsePaths, collapsedDescendantPaths};
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
    }
  }
  const [state, dispatch] = usePersistedReducer(hierarchySettingsReducer);
  return [state, dispatch];
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
        codeset_intention: "From TermHub",
        limitations: "From TermHub",
        update_message: "TermHub testing",
        // "codeset_created_at": "2022-07-28 16:14:13.085000+00:00", // will be set by enclave
        // "codeset_created_by": "e64b8f7b-7af8-4b44-a570-557b812c0eeb", // will be set by enclave
        provenance: `TermHub url: ${window.location.href}${window.location.search ? '&' : '?'}sstorage=${JSON.stringify(sessionStorage)}`,
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
    case "addDefinition": {
      state = {...state, definitions: {...state.definitions, [action.definition.concept_id]: action.definition }}
    }
    case "deleteDefinition": {
      let definitions = {...state.definitions};
      delete definitions[action.concept_id];
      state = {...state, definitions, };
    }
    /*
    case "currentUserId": {
      if (state.newCset) {
        if (state.newCset['on-behalf-of']) {
          if (state.newCset['on-behalf-of'] === action.currentUserId) {
            return state;
          } else {
            throw new Error("not expecting a different userId!");
          }
        } else {
          state = {...state,
                    newCset: {...state.newCset,
                              ['on-behalf-of']: action.currentUserId,
                              ['researchers']: [action.currentUserId], } };
          return {...state, currentUserId: action.currentUserId};
        }
      }
      return {...state, currentUserId: action.currentUserId};
    }
     */
    /*
    case "add_definitions": {
      let {definitions = {}} = state;
      definitions = {...definitions, ...action.payload};
      return {...state, ...definitions};
    }
     */
  }
  state = {...state, counts: {...state.counts, 'Expression items': Object.keys(state.definitions).length}};
  return state
};
const NewCsetContext = createContext(null);
export function NewCsetProvider({ children }) {
  const [stateUpdate, setStateUpdate] = useState(); // just to force consumers to rerender
  // const storageProvider = useSearchParamsState();
  const storageProvider = sessionStorage; // for now, for simplicity, just save to sessionStorage
  let state = JSON.parse(storageProvider.getItem('newCset')) || {};

  const dispatch = action => {
    let latestState = JSON.parse(storageProvider.getItem('newCset'));
    const stateAfterDispatch = newCsetReducer(latestState, action);
    if (!isEqual(latestState, stateAfterDispatch)) {
      storageProvider.setItem('newCset', JSON.stringify(stateAfterDispatch));
      console.log(stateAfterDispatch);
      setStateUpdate(stateAfterDispatch);
    }
  }
  console.log(state);
  return (
      <NewCsetContext.Provider value={[state, dispatch]}>
        {children}
      </NewCsetContext.Provider>
  );
}
export function useNewCset() {
  return useContext(NewCsetContext);
}
export function newCsetAtlasJson(cset) {
  if (isEmpty(cset.definitions)) {
    return;
  }
  const atlasDefs = Object.values(cset.definitions).map(d => pick(d, [
    'concept_id', 'includeDescendants', 'includeMapped', 'isExcluded', 'annotation' ]));
  const atlasJson = JSON.stringify(atlasDefs, null, 2);
  return atlasJson;
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