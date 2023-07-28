import React, {createContext, useContext, useReducer} from "react";
import {flatten, fromPairs, get, isEmpty} from "lodash";
import {createPersistedReducer} from "./usePersistedReducer";
import {alertsReducer} from "../components/AlertMessages";
import {useSearchParamsState} from "./SearchParamsProvider";

export const NEW_CSET_ID = -1;

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

const HierarchySettingsContext = createContext(null);
const HierarchySettingsDispatchContext = createContext(null);
/*
// since hierarchySettings is getting saved to url and maybe
//  having problems because of saving the initial value to url,
//  let's try to just save differences from the default to url
 */
const defaultHierarchySettingsState = { nested: true, collapsePaths: {},
  collapsedDescendantPaths: {}, hideRxNormExtension: true, hideZeroCounts: false, };
export function HierarchySettingsProvider({ children }) {
  const storageProvider = useSearchParamsState();
  const usePersistedReducer = createPersistedReducer('hierarchySettings',
    storageProvider, defaultHierarchySettingsState);

  function hierarchySettingsReducer(state, action) {
    if ( ! ( action || {} ).type ) return state;
    let {collapsePaths, collapsedDescendantPaths,
      nested, hideRxNormExtension, hideZeroCounts} = {...defaultHierarchySettingsState, ...state};
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
  /* const initialState = { nested: true, collapsePaths: {}, collapsedDescendantPaths: {},
                          hideRxNormExtension: true, hideZeroCounts: false, };
  const [state, dispatch] = usePersistedReducer(
      hierarchySettingsReducer, () => storageProvider.hierarchySettings || initialState); */

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
const csetEditsReducer = (csetEdits, action) => {
};