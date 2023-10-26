// TODO: get rid of this entirely (I think)...found a simpler way to do it
//   in AppState CodesetIdsContext
// start with code from https://github.com/johnayeni/use-persisted-reducer

import React, { useEffect, useReducer } from 'react';
import {get, isEmpty, } from 'lodash';
import {oneSidedObjectDifference} from "../components/utils";

/*
  - Had to do weird thing by allowing default state instead of (or
    in addition to) initial state because updating url for default
    (initial) values of hierarchySettings was making extra rerenders and
    maybe causing problems. Instead only need to persist differences
    from default state, but, when accessing state, see the default with
    the changes applied:  state = {...unpersistedDefaultState, ...state}

    unpersistedDefaultState is used:
      - in usePersistedReducer to augment the persisted state with the default values
      - in storage.get to return default value if key doesn't appear in the persisted state
      - in storage.set to only save values that differ from what's in the default
      - in the specific reducer being passed in to get any values it needs from
        the default if they aren't in the persisted state. that is, the reducer state
        is only the difference, but the reducer may need access the to the default values
        anyway

 */

export const usePersistedReducer = (reducer, initialState, key, storage, unpersistedDefaultState) => {
  const storageState = storage.get(key, initialState);
  let [state, dispatch] = React.useReducer(reducer, storageState);

  useEffect(() => {
    storage.set(key, state);
  }, [state]);

  if (unpersistedDefaultState) {
    state = {...unpersistedDefaultState, ...state};
  }
  return [state, dispatch];
};

// meant to be usable with localStorage or url query param storage, which needs
//  to be small and acts weird when trying to throw initialState onto it, so
//  allowing unpersistedDefaultState as an alternative to initialState
const createStorage = (provider, unpersistedDefaultState) => ({
  get(key, initialState) {
    let ret;
    const json = provider.getItem(key);
    try {
      if (json === null) {
        ret = typeof(initialState) === 'function' ? initialState() : initialState;
      } else {
        // if getItem give an object instead of a JSON string, don't parse it
        ret = typeof(json) === 'string' ? JSON.parse(json) : json;
      }
    } catch(err) {
      if (err.name === 'SyntaxError') {
        ret = json;
      } else {
        throw err;
      }
    }
    // console.log(`get(${key}, ${initialState}) with ${unpersistedDefaultState}`, ret);
    return ret ?? (unpersistedDefaultState || {})[key];
  },
  set(key, value) {
    if (unpersistedDefaultState) {
      value = oneSidedObjectDifference(unpersistedDefaultState, value);
    }
    if (isEmpty(value)) {
      provider.removeItem(key);
      return;
    }
    if (!provider.dontStringifySetItem) {
      value = JSON.stringify(value);
    }
    provider.setItem(key, value);
  },
  // not sure if these will be needed:
  // remove(key) { provider.removeItem(key); }
  // clear() { provider.clear(); }
});

export const createPersistedReducer = (key, provider, unpersistedDefaultState) => {
  if (provider) {
    const storage = createStorage(provider, unpersistedDefaultState);
    return (reducer, initialState) =>
      usePersistedReducer(reducer, initialState, key, storage, unpersistedDefaultState);
  }
  return useReducer;
};
