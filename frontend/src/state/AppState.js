import React, {createContext, useContext, useReducer} from "react";
import {flatten, fromPairs, get} from "lodash";

import {alertsReducer} from "../components/AlertMessages";

export function useStateSlice(slice) {
  const appState = useAppState();
  return appState.getSlice(slice);
  // const [state, dispatch] = appState.getSlice(slice);
  // return {state, dispatch};  // should probably return array instead of object?
}

const CombinedReducersContext = createContext(null);

export function AppStateProvider({children}) {
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
    editCset: () => useReducer(editCsetReducer, {}),
    alerts: useReducer(alertsReducer, {}),
    hierarchySettings: [hierarchySettings, hsDispatch],
  }
  /*
  const reducers = {
    hierarchySettings: [hierarchySettings, hsDispatch],
    editCset: useReducer(editCsetReducer, {}),
    alerts: useReducer(alertsReducer, {}),
    // contentItems: useReducer(contentItemsReducer, defaultContentItems),
    // codeset_ids: useReducer(codeset_idsReducer, []),
    // concept_ids: useReducer(currentConceptIdsReducer, []),
    // more stuff needed
  };
   */

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
  if (!action || !action.type) return state;
  switch (action.type) {
    case "create_new_cset": {
      let newCset = {
        "codeset_id": 0,
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