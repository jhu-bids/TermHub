import React, {createContext, useContext, } from "react";
import {createSearchParams, useSearchParams, useLocation, Navigate, } from "react-router-dom";
import {isEmpty} from "lodash";

const SEARCH_PARAM_STATE_CONFIG = {
  scalars: ["editCodesetId", "sort_json", "use_example"],
  global_props_but_not_search_params: [], // ["searchParams", "setSearchParams"],
  serialize: ["csetEditState"],
};

const SearchParamsContext = createContext(null);

export function SearchParamsProvider({children}) {
  const [searchParams, setSearchParams] = useSearchParams();
  const location = useLocation();
  // gets state (codeset_ids for now) from query string, passes down through props
  // const [codeset_ids, setCodeset_ids] = useState(sp.codeset_ids || []);
  let sp = searchParamsToObj(searchParams, setSearchParams);
  const { codeset_ids = [] } = sp;

  let globalProps = { ...sp, searchParams, setSearchParams };

  if (sp.fixSearchParams) {
    delete sp.fixSearchParams;
    const csp = createSearchParams(sp);
    return <Navigate to={location.pathname + "?" + csp.toString()} />;
  }
  /*
  useEffect(() => {
    if (sp.codeset_ids && !isEqual(codeset_ids, sp.codeset_ids)) {
      setCodeset_ids(sp.codeset_ids);
    }
  }, [searchParams, codeset_ids, sp.codeset_ids]);
   */

  function changeCodesetIds(codeset_id, how) {
    // how = add | remove | toggle
    if (how === "set" && Array.isArray(codeset_id)) {
      updateSearchParams({
                           ...globalProps,
                           addProps: { codeset_ids: codeset_id },
                         });
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
      updateSearchParams({
                           ...globalProps,
                           addProps: { codeset_ids: [...codeset_ids, codeset_id] },
                         });
    } else if (action === "remove") {
      if (!included) return;
      updateSearchParams({
                           ...globalProps,
                           addProps: { codeset_ids: codeset_ids.filter((d) => d !== codeset_id) },
                         });
    } else {
      throw new Error(
          "unrecognized action in changeCodesetIds: " +
          JSON.stringify({ how, codeset_id })
      );
    }
  }

  if (!globalProps.codeset_ids) {
    globalProps.codeset_ids = [];
  }
  const value = {sp: globalProps, updateSp: updateSearchParams, };
  return (
      <SearchParamsContext.Provider value={value} >
        {children}
      </SearchParamsContext.Provider>
  );
}

export function useSearchParamsState() {
  return useContext(SearchParamsContext);
}


export function searchParamsToObj(searchParams) {
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

  /* if the editState has changes for a cset no longer selected, it will cause an
      error. just get rid of those changes.
   */
  let fixSearchParams = {}; // don't need to do all this
  if (sp.editCodesetId) {
    if (!(sp.codeset_ids || []).includes(sp.editCodesetId)) {
      delete sp.editCodesetId;
      fixSearchParams.delProps = ["editCodesetId"];
    }
  }
  /*
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
  // console.log({sp});
  return sp;
}

export function updateSearchParams(props) {
  const {addProps = {}, delProps = [], searchParams, setSearchParams} = props;
  let sp = searchParamsToObj(searchParams);
  SEARCH_PARAM_STATE_CONFIG.global_props_but_not_search_params.forEach((p) => {
    delete sp[p];
  });
  delProps.forEach((p) => {
    delete sp[p];
  });
  sp = {...sp, ...addProps};
  SEARCH_PARAM_STATE_CONFIG.serialize.forEach((p) => {
    if (sp[p]) {
      sp[p] = JSON.stringify(sp[p]);
    }
  });
  const csp = createSearchParams(sp);
  setSearchParams(csp);
}