import React, {createContext, useContext, useState, useCallback, } from "react";
import {createSearchParams, useSearchParams, /* useLocation, Navigate, */ } from "react-router-dom";
// import {isEmpty} from "lodash";

const SEARCH_PARAM_STATE_CONFIG = {
  scalars: ["editCodesetId", "sort_json", "use_example", "sstorage", "show_alerts",
  "optimization_experiment", "comparison_rpt"],
  global_props_but_not_search_params: [], // ["searchParams", "setSearchParams"],
  // ignore: ["sstorage"],
  serialize: ["newCset", "hierarchySettings"],
};

const SearchParamsContext = createContext(null);

export function SearchParamsProvider({children}) {
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
      setSearchParams(csp);
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

  function changeCodesetIds(codeset_id, how) {
    let sp = searchParamsToObj(searchParams);

    // how = add | remove | toggle
    if (how === "set" && Array.isArray(codeset_id)) {
      updateSearchParams({ /* ...sp, haven't tested removing this, but should be ok */
        addProps: { codeset_ids: codeset_id }, searchParams, setSearchParams, });
      return;
    }
    const included = codeset_ids.includes(codeset_id);
    let action = how;
    if (how === "add" && included) return;
    if (how === "remove" && !included) return;
    if (how === "toggle") {
      action = included ? "remove" : "add";
    }
    if (action === "add") {
      updateSearchParams({ ...sp, addProps: { codeset_ids: [...codeset_ids, codeset_id] },
                            searchParams, setSearchParams, });
    } else if (action === "remove") {
      if (!included) return;
      updateSearchParams({ ...sp, addProps: { codeset_ids: codeset_ids.filter((d) => d !== codeset_id) },
                            searchParams, setSearchParams, });
    } else {
      throw new Error(
          "unrecognized action in changeCodesetIds: " +
          JSON.stringify({ how, codeset_id })
      );
    }
  }

  if (!sp.codeset_ids) {
    sp.codeset_ids = [];
  }
  const value = { sp, updateSp: updateSearchParams, changeCodesetIds, getItem, setItem, removeItem, clear, dontStringifySetItem: true, };
  return (
      <SearchParamsContext.Provider value={value} >
        {children}
      </SearchParamsContext.Provider>
  );
}

export function useSearchParamsState() {
  return useContext(SearchParamsContext);
}