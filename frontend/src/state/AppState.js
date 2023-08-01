import React, {createContext, useContext, useReducer} from "react";
import {flatten, fromPairs, get, isEmpty} from "lodash";
import {createPersistedReducer} from "./usePersistedReducer";
import {alertsReducer} from "../components/AlertMessages";
import {useSearchParamsState} from "./SearchParamsProvider";

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
  const usePersistedReducer = createPersistedReducer('codeset_ids', storageProvider);
  const [state, dispatch] = usePersistedReducer(codesetIdsReducer, []);

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

const EditCsetContext = createContext(null);
const EditCsetDispatchContext = createContext(null);
export function EditCsetProvider({ children }) {
  const [state, dispatch] = useReducer(editCsetReducer, {});

  return (
      <EditCsetContext.Provider value={state}>
        <EditCsetDispatchContext.Provider value={dispatch}>
          {children}
        </EditCsetDispatchContext.Provider>
      </EditCsetContext.Provider>
  );
}
export function useEditCset() {
  return useContext(EditCsetContext);
}
export function useEditCsetDispatch() {
  return useContext(EditCsetDispatchContext);
}

const editCsetReducer = (state, action) => {
  if (!action || !action.type) return state;
  switch (action.type) {
    case "create_new_cset": {
      let newCset = {
        "codeset_id": NEW_CSET_ID,
        "concept_set_version_title": "New Cset (Draft)",
        "concept_set_name": "New Cset",
        "alias": "New Cset",
        "source_application": "UNITE",
        // "source_application_version": "2.0",
        // "codeset_created_at": "2022-07-28 16:14:13.085000+00:00",
        "codeset_intention": "From TermHub",
        "limitations": "From TermHub",
        "update_message": "TermHub testing",
        // "codeset_created_by": "e64b8f7b-7af8-4b44-a570-557b812c0eeb",
        "provenance": "TermHub testing.",
        "is_draft": true,
      };

      console.log("editCsetReducer() called");
      return {...state, newCset, definitions: {}};
    }
    case "add_definitions": {
      let {definitions = {}} = state;
      definitions = {...definitions, ...action.payload};
      return {...state, ...definitions};
    }
  }
  if (state === action.payload) return null; // if already set to this codeset_id, turn off
  return action.payload;
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
const csetEditsReducer = (csetEdits, action) => {
};