import React, {createContext, useContext, useState, useCallback, useEffect} from "react";
import {createSearchParams, useSearchParams, /* useLocation, Navigate, */ } from "react-router-dom";
import {isEmpty, omit} from "lodash";
import {isJsonString} from "../utils";

// starting from https://chat.openai.com/share/6cc19197-8a46-49ce-9100-84a83d0d2bf1
// at least for now, moving all search params to sessionStorage
export function useSessionStorage() {
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
  return ss;
}

const SEARCH_PARAM_STATE_CONFIG = {
  scalars: ["editCodesetId", "use_example", "sstorage", "show_alerts",
  "optimization_experiment", "comparison_rpt"],
  global_props_but_not_search_params: [], // ["searchParams", "setSearchParams"],
  // ignore: ["sstorage"],
  serialize: ["newCset", "graphOptions"],
  intArray: ["codeset_ids"],
};

const SearchParamsContext = createContext(null);
export function SearchParamsProvider({children}) {
  const providerName = 'searchParams';
  const [searchParams, setSearchParams] = useSearchParams();

  const searchParamsToObj = useCallback(searchParams => {
    const qsKeys = Array.from(new Set(searchParams.keys()));
    let sp = {};
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

  let sp = searchParamsToObj(searchParams);
  // console.log('got sp', sp);

  // gets state (codeset_ids for now) from query string, passes down through props
  // const [codeset_ids, setCodeset_ids] = useState(sp.codeset_ids || []);

  const { codeset_ids = [] } = sp;

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
      // for some reason this isn't just setting the querystring, it's getting rid of the path
      // setSearchParams(csp);
      let url = new (window.URL)(window.location);
      let path = url.pathname.slice(1);
      url.search = csp + '';
      window.location.href = url.toString();
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
  }
  function addToArray(key, val) {
    let sp = searchParamsToObj(searchParams);
    let arr = sp[key] ?? [];
    updateSearchParams({addProps: {[key]: [...arr, val]}});
  }
  function removeFromArray(key, val) {
    let sp = searchParamsToObj(searchParams);
    let arr = sp[key] ?? [];
    updateSearchParams({addProps: {[key]: arr.filter(d => d != val)}});
  }

  if (!sp.codeset_ids) {
    sp.codeset_ids = [];
  }
  const value = { providerName, sp, getItem, setItem, removeItem, clear, addToArray, removeFromArray, dontStringifySetItem: true, };
  return (
      <SearchParamsContext.Provider value={value} >
        {children}
      </SearchParamsContext.Provider>
  );
}
export function useSearchParamsState() {
    return useContext(SearchParamsContext);
}

const SSSPContext = createContext(null);
export function SessionStorageWithSearchParamsProvider({children}) {
  const providerName = 'sessionStorageWithSearchParamsProvider';
  // combines searchParams into sessionStorage and deletes searchParams
  // this is so we can save state into a url for sharing or returning to
  //  but then maintain it in sessionStorage to prevent the url getting
  //  unmanageably large and ugly
  let ss = useSessionStorage();
  const [providerStorage, setProviderStorage] = useState({...ss.storage});
  const [searchParams, setSearchParams] = useSearchParams();
  const searchParamsToObj = useCallback(searchParams => {
    const qsKeys = Array.from(new Set(searchParams.keys()));
    let sp = {};
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

  useEffect(() => {
    if (!ss) {
      throw new Error("why would this be?");
    }
    let storage = {...ss.storage};  // just the values, not the methods
    if (searchParams.toString()) {
      // if there are any search params, add them on top of sessionStorage
      let sp = searchParamsToObj(searchParams);
      for (let k in sp) {
        ss.setItem(k, sp[k]);
      }
    }
    setSearchParams();
  }, []);

  // ss (sessionStorage) has a storage prop for the values it holds. ss.storage is
  //  identical to ss.sp. sp (searchParams) is there because of other code that expects
  //  to find the storage values there
  // the rest of ss is getItem, setItem, clear, etc.
  // let value = {...ss, dontStringifySetItem: true};
  // value.storage = value.sp = providerStorage;

  return (
      <SSSPContext.Provider value={ss} >
        {children}
      </SSSPContext.Provider>
  );
}

export function useSessionStorageWithSearchParams() {
  return useContext(SSSPContext);
}