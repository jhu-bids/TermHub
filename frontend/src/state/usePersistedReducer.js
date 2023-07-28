import React, { useEffect, useReducer } from 'react';
import {get} from 'lodash';

export const usePersistedReducer = (reducer, initialState, key, storage, unpersistedDefaultState) => {
  let [state, dispatch] = React.useReducer(reducer, storage.get(key, initialState));

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
//  allowing unpersistedDefaultState as an alternative
const createStorage = (provider, unpersistedDefaultState) => ({
  get(key, initialState) {
    let ret;
    const json = provider.getItem(key);
    try {
      ret = json === null
          ? typeof initialState === 'function'
              ? initialState()
              : initialState
          : JSON.parse(json);
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
    if (get(unpersistedDefaultState, key) == value) {
      return;  // trying to set something already in the default
    }
    if (!provider.dontStringifySetItem) {
      value = JSON.stringify(value);
    }
    provider.setItem(key, value);
  },
});

export const createPersistedReducer = (key, provider, unpersistedDefaultState) => {
  if (provider) {
    const storage = createStorage(provider, unpersistedDefaultState);
    return (reducer, initialState) =>
      usePersistedReducer(reducer, initialState, key, storage, unpersistedDefaultState);
  }
  return useReducer;
};