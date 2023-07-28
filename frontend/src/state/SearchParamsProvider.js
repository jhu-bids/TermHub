import React, {createContext, useContext, useState, useCallback, } from "react";
import {createSearchParams, useSearchParams, /* useLocation, Navigate, */ } from "react-router-dom";
// import {isEmpty} from "lodash";

const SEARCH_PARAM_STATE_CONFIG = {
  scalars: ["editCodesetId", "sort_json", "use_example"],
  global_props_but_not_search_params: [], // ["searchParams", "setSearchParams"],
  serialize: ["csetEditState", "hierarchySettings"],
};

const SearchParamsContext = createContext(null);

export function SearchParamsProvider({children}) {
  const [searchParams, setSearchParams] = useSearchParams();

  const searchParamsToObj = useCallback(searchParams => {
    const qsKeys = Array.from(new Set(searchParams.keys()));
    let sp = {};
    qsKeys.forEach((key) => {
      let vals = searchParams.getAll(key);
      sp[key] = vals.map((v) => (parseInt(v) == v ? parseInt(v) : v)).sort(); // eslint-disable-line
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
    console.log('returning sp', sp);
    return sp;
  }, [searchParams]);

  let sp = searchParamsToObj(searchParams);
  console.log('got sp', sp);

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
      console.log('setting searchParams', csp+'');
      setSearchParams(csp);
    }
  }

  // getItem and setItem are so SearchParams can be used with usePersistedReducer
  function getItem(key) {
    let sp = searchParamsToObj(searchParams);
    return sp[key] ?? null ;
  }

  function setItem(key, value) {
    /*
    if (typeof(value) === 'string') {
      value = JSON.stringify(value);
    }
     */
    updateSearchParams({addProps: {[key]: value}});
  /**/}

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
  const value = {
    sp, updateSp: updateSearchParams, changeCodesetIds,
    getItem, setItem, dontStringifySetItem: true, };
  return (
      <SearchParamsContext.Provider value={value} >
        {children}
      </SearchParamsContext.Provider>
  );
}

export function useSearchParamsState() {
  return useContext(SearchParamsContext);
}


  /*

  was near the top of SearchParamsProvider:
    const location = useLocation();
    if (sp.fixSearchParams) {
      debugger; // is this code still needed?
      delete sp.fixSearchParams;
      const csp = createSearchParams(sp);
      return <Navigate to={location.pathname + "?" + csp.toString()} />;
    }

  this was at the bottom of searchParamsToObj:
    if the editState has changes for a cset no longer selected, it will cause an
      error. just get rid of those changes.


    let fixSearchParams = {}; // don't need to do all this
    if (sp.editCodesetId) {
      if (!(sp.codeset_ids || []).includes(sp.editCodesetId)) {
        delete sp.editCodesetId;
        fixSearchParams.delProps = ["editCodesetId"];
      }
    }

  this was at the bottom of searchParamsToObj but commented out already:
    if (sp.csetEditState) {
      let editState = {...sp.csetEditState};
      let update = false;
      for (const cid in editState) {
        if (!(sp.codeset_ids || []).includes(parseInt(cid))) {
          delete editState[cid];
          update = true;
        }
      }
      if (update) {
        if (isEmpty(editState)) {
          delete sp.csetEditState;
          fixSearchParams.delProps = [
            ...(fixSearchParams.delProps || []),
            "csetEditState",
          ];
          // updateSearchParams({..._globalProps, delProps: ['csetEditState' ]});
        } else {
          sp.csetEditState = editState;
          fixSearchParams.addProps = {csetEditState: editState};
          // updateSearchParams({..._globalProps, addProps: {csetEditState: editState}});
        }
        //return;
      }
      if (!isEmpty(fixSearchParams)) {
        // didn't need to set up fixSearchParams, just need to know if it's needed
        sp.fixSearchParams = true;
      }
    }
 */