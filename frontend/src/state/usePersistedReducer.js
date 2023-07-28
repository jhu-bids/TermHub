import React, { useEffect, useReducer } from 'react';

export const usePersistedReducer = (reducer, initialState, init, key, storage) => {
  const [state, dispatch] = React.useReducer(reducer, storage.get(key, initialState), init);

  useEffect(() => {
    storage.set(key, state);
  }, [state]);

  return [state, dispatch];
};

const createStorage = (provider) => ({
  get(key, initialState) {
    const json = provider.getItem(key);
    let ret = json === null
        ? typeof initialState === 'function'
            ? initialState()
            : initialState
        : JSON.parse(json);
    console.log(`get(${key}, ${initialState}`, ret);
  },
  set(key, value) {
    provider.setItem(key, JSON.stringify(value));
  },
});

export const createPersistedReducer = (key, provider = /* globalThis. */localStorage) => {
  if (provider) {
    const storage = createStorage(provider);
    return (reducer, initialState, init) =>
      usePersistedReducer(reducer, initialState, init, key, storage);
  }
  return useReducer;
};