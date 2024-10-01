import React, {createContext, useContext, useState, useCallback, useMemo, useEffect} from "react";
import {createSearchParams, useSearchParams, /* useLocation, Navigate, */ } from "react-router-dom";
// import {isEmpty, omit} from "lodash";
import {isJsonString} from "../utils";

const SessionStorageContext = createContext(null);
export function SessionStorageProvider({children}) {
  const providerName = 'sessionStorage';
  const [storage, setStorage] = useState(() => {
    const items = { codeset_ids: [], ...window.sessionStorage };
    delete items.AI_buffer;    // added by chrome ai stuff i think...I don't want it
    delete items.AI_sentBuffer;
    let sstorage = Object.keys(items).reduce((acc, key) => {
      let value = items[key];
      acc[key] = isJsonString(value) ? JSON.parse(items[key]) : value;
      return acc;
    }, {});
    return sstorage;
  });

  const extend = (obj) => {
    for (const key in obj) {
      this.setItem(key, obj[key]);
    }
  };
  const getItem = (key) => {
    try {
      const item = window.sessionStorage.getItem(key);
      return item ? JSON.parse(item) : null;
    } catch (error) {
      console.error(error);
      return null;
    }
  };

  const setItem = (key, value) => {
    try {
      window.sessionStorage.setItem(key, JSON.stringify(value));
      setStorage((prevStorage) => ({
        ...prevStorage,
        [key]: value,
      }));
    } catch (error) {
      console.error(error);
    }
  };

  const removeItem = (key) => {
    try {
      window.sessionStorage.removeItem(key);
      setStorage((prevStorage) => {
        const { [key]: _, ...rest } = prevStorage;
        return rest;
      });
    } catch (error) {
      console.error(error);
    }
  };

  const clear = () => {
    try {
      window.sessionStorage.clear();
      setStorage({});
    } catch (error) {
      console.error(error);
    }
  };

  // is this stuff working right?
  function addToArray(key, val) {
    let item = getItem(key);
    if (!Array.isArray(item)) throw new Error("not an array");
    setItem(key, [...item, val]);
  }
  function removeFromArray(key, val) {
    let item = getItem(key) || [];
    setItem(key, item.filter(d => d != val));
  }

  let ss = {
    providerName,
    getItem,
    setItem,
    removeItem,
    clear,
    extend,
    addToArray,
    removeFromArray,
    storage,
    sp: storage, // so code like `{sp} = useSearchParamsState();` works
    dontStringifySetItem: true,
  };
  return (
    <SessionStorageContext.Provider value={ss}>
      {children}
    </SessionStorageContext.Provider>
  );
}

export function useSessionStorage() {
  return useContext(SessionStorageContext);
}

/*

const SessionStorageContext = createContext(null);

const SessionStorageProto = {
  getItem(key) {
    try {
      const item = window.sessionStorage.getItem(key);
      return item ? JSON.parse(item) : null;
    } catch (error) {
      console.error(error);
      return null;
    }
  },

  setItem(key, value) {
    try {
      window.sessionStorage.setItem(key, JSON.stringify(value));
      this._forceUpdate();
    } catch (error) {
      console.error(error);
    }
  },

  removeItem(key) {
    try {
      window.sessionStorage.removeItem(key);
      this._forceUpdate();
    } catch (error) {
      console.error(error);
    }
  },

  clear() {
    try {
      window.sessionStorage.clear();
      this._forceUpdate();
    } catch (error) {
      console.error(error);
    }
  },

  addToArray(key, val) {
    const item = this.getItem(key);
    if (!Array.isArray(item)) {
      this.setItem(key, [val]);
    } else if (!item.includes(val)) {
      this.setItem(key, [...item, val]);
    }
  },

  removeFromArray(key, val) {
    const item = this.getItem(key);
    if (Array.isArray(item)) {
      this.setItem(key, item.filter(d => d !== val));
    }
  },
};

export function SessionStorageProvider({ children }) {
  const [, forceUpdate] = useState({});

  const sessionStorageObj = useMemo(() => {
    const ss = Object.create(SessionStorageProto);
    ss._forceUpdate = () => forceUpdate({});
    return new Proxy(ss, {
      get(target, prop) {
        if (prop in target) return target[prop];
        return target.getItem(prop);
      },
      set(target, prop, value) {
        target.setItem(prop, value);
        return true;
      },
    });
  }, []);

  return (
    <SessionStorageContext.Provider value={sessionStorageObj}>
      {children}
    </SessionStorageContext.Provider>
  );
}

export function useSessionStorage() {
  return useContext(SessionStorageContext);
}

 */



const SEARCH_PARAM_STATE_CONFIG = {
  scalars: ["editCodesetId", "sort_json", "use_example", "show_alerts", "optimization_experiment",
            // "comparison_rpt",
            "compare_opt"],
  serialize: ["newCset", ], // "appOptions"
};

const SearchParamsContext = createContext(null);

export function SearchParamsProvider({children}) {
  const [searchParams, setSearchParams] = useSearchParams();
  const [sp, setSp] = useState(searchParams);

  const searchParamsToObj = useCallback(searchParams => {
    const qsKeys = Array.from(new Set(searchParams.keys()));
    qsKeys.forEach((key) => {
      // if (SEARCH_PARAM_STATE_CONFIG.ignore.includes(key)) { return; }
      let vals = searchParams.getAll(key);
      sp[key] = vals.map((v) => (parseInt(v) == v ? parseInt(v) : v)); //   ok to disable sort? it's messing up codeset_id order; .sort(); // eslint-disable-line
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
    // console.log('returning sp', sp);
    return sp;
  }, [searchParams]);

  function updateSearchParams(props) {
    const {addProps = {}, delProps = [], replaceAllProps} = props;
    let sp;
    if (replaceAllProps) {
      sp = replaceAllProps;
    } else {
      sp = searchParamsToObj(searchParams);
    }
    /* SEARCH_PARAM_STATE_CONFIG.global_props_but_not_search_params.forEach((p) => { delete sp[p]; }); */
    delProps.forEach((p) => {
      delete sp[p];
    });
    sp = {...sp, ...addProps};
    SEARCH_PARAM_STATE_CONFIG.serialize.forEach((p) => {
      if (sp[p] && typeof(sp[p] !== 'string')) {
        sp[p] = JSON.stringify(sp[p]);
      }
    });
    const csp = createSearchParams(sp);
    if (csp+'' !== searchParams+'') {
      // console.log(csp, sp);
      setSearchParams(csp);
      setSp(sp);
    }
  }

  // getItem and setItem are so SearchParams can be used with usePersistedReducer
  function getItem(key) {
    let sp = searchParamsToObj(searchParams);
    return sp[key] ?? null ;
  }

  function setItem(key, value) {
    updateSearchParams({addProps: {[key]: value}});
  }

  function removeItem(key) {
    updateSearchParams({delProps: [key]});
  }

  function clear() {
    const csp = createSearchParams();
    setSearchParams(csp);
    [...reducerResetFuncs].map(f => f());
  }

  function addToArray(key, val) {
    let item = this.getItem(key);
    if (!Array.isArray(item)) {
      item = [];
    }
    if (!item.includes(val)) {
      this.setItem(key, [...item, val]);
    }
  }

  function removeFromArray(key, val) {
    let item = this.getItem(key);
    if (Array.isArray(item)) {
      this.setItem(key, item.filter(d => d != val));
    }
  }

  const value = { sp, updateSp: updateSearchParams, getItem, setItem, removeItem, clear, addToArray, removeFromArray, };
  return (
      <SearchParamsContext.Provider value={value} >
        {children}
      </SearchParamsContext.Provider>
  );
}

export function useSearchParamsState() {
  const ctx = useContext(SearchParamsContext);
  return ctx;
}

/*
const SearchParamsProto = {
  updateSearchParams({ addProps = {}, delProps = [], replaceAllProps }) {
    let sp = replaceAllProps || this._searchParamsToObj(this._searchParams);
    delProps.forEach((p) => { delete sp[p]; });
    sp = { ...sp, ...addProps };
    SEARCH_PARAM_STATE_CONFIG.serialize.forEach((p) => {
      if (sp[p] && typeof sp[p] !== 'string') {
        sp[p] = JSON.stringify(sp[p]);
      }
    });
    const csp = createSearchParams(sp);
    if (csp.toString() !== this._searchParams.toString()) {
      this._setSearchParams(csp);
    }
  },

  getItem(key) {
    return this._searchParamsToObj(this._searchParams)[key] ?? null;
  },

  setItem(key, value) {
    this.updateSearchParams({ addProps: { [key]: value } });
  },

  removeItem(key) {
    this.updateSearchParams({ delProps: [key] });
  },

  clear() {
    this._setSearchParams(createSearchParams());
  },

  addToArray(key, val) {
    let item = this.getItem(key);
    if (!Array.isArray(item)) {
      item = [];
    }
    if (!item.includes(val)) {
      this.setItem(key, [...item, val]);
    }
  },

  removeFromArray(key, val) {
    let item = this.getItem(key);
    if (Array.isArray(item)) {
      this.setItem(key, item.filter(d => d != val));
    }
  },

  _searchParamsToObj(searchParams) {
    const qsKeys = Array.from(new Set(searchParams.keys()));
    let sp = {};
    qsKeys.forEach((key) => {
      let vals = searchParams.getAll(key);
      sp[key] = vals.map((v) => (parseInt(v) == v ? parseInt(v) : v));
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
    return sp;
  },
};

const SearchParamsContext = createContext(null);

export function SearchParamsProvider({ children }) {
  const [searchParams, setSearchParams] = useSearchParams();
  const [, forceUpdate] = useState({});

  const setSearchParamsWrapper = useCallback((newParams) => {
    setSearchParams(newParams);
    forceUpdate({});
  }, [setSearchParams]);

  const searchParamsObj = useMemo(() => {
    const sp = Object.create(SearchParamsProto);
    Object.assign(sp, {
      _searchParams: searchParams,
      _setSearchParams: setSearchParamsWrapper,
    });
    return new Proxy(sp, {
      get(target, prop) {
        if (prop in target) return target[prop];
        return target._searchParamsToObj(target._searchParams)[prop];
      },
      set(target, prop, value) {
        target.setItem(prop, value);
        return true;
      },
    });
  }, [searchParams, setSearchParamsWrapper]);

  useEffect(() => {
    forceUpdate({});
  }, [searchParams]);

  return (
    <SearchParamsContext.Provider value={searchParamsObj}>
      {children}
    </SearchParamsContext.Provider>
  );
}

export function useSearchParamsState() {
  return useContext(SearchParamsContext);
}
*/