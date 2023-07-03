import React from "react";
// import useCombinedReducers from 'use-combined-reducers';
import axios from "axios";
import {API_ROOT} from "../env";
import CircularProgress from "@mui/material/CircularProgress";
import Box from "@mui/material/Box";
import {useQuery} from "@tanstack/react-query";
import {createSearchParams, useSearchParams} from "react-router-dom";
import {flatten, isEmpty, keyBy, uniq} from "lodash";
import {pct_fmt} from "../components/utils";
import WarningRoundedIcon from '@mui/icons-material/WarningRounded';
import {CheckCircleRounded} from "@mui/icons-material";
import {Inspector} from 'react-inspector'; // https://github.com/storybookjs/react-inspector
import {formatEdges} from '../components/ConceptGraph';
import {FlexibleContainer} from "../components/FlexibleContainer";
import {searchParamsToObj} from "./urlState";
import {useAppState, useStateSlice} from "./AppState";
import {dataCache} from "./DataCache";

window.axios = axios

const stateDoc = `
    URL query string
    handled by QueryStringStateMgr updateSearchParams(props) and searchParamsToObj(searchParams)
      codeset_ids
      editCodesetId
      csetEditState
      sort_json
      use_example

    reducers and context
    handled by useAppState, AppStateProvider, useStateSlice(slice)
      really using:
        hierarchySettings
      WIP, not using:
        codeset_ids
        concept_ids
        editCset

    DataCache
        all_csets
        edges
        cset_members_items
        selected_csets
        researchers
        related_csets
        concepts

    local to components, useState, etc.

    Goals:
      Manage all/
`;

export function prefetch(props) {
  const {itemType, codeset_ids} = props;
  switch(itemType) {
    case 'all_csets':
      fetchItems(itemType);
      break;
    default:
      throw new Error(`Don't know how to prefetch ${itemType}`);
  }
}
export async function fetchItems( itemType, paramList) {
  if (isEmpty(paramList)) {
    return [];
    throw new Error(`fetchItems for ${itemType} requires paramList`);
  }
  let url,
      data,
      cacheKey,
      api,
      apiGetParamName,
      useGetForSmallData;

  switch(itemType) {
    case 'concepts':
    case 'codeset_ids_by_concept_id':
    case 'researchers':
      apiGetParamName = 'id';
    case 'concept_ids_by_codeset_id':
      apiGetParamName = apiGetParamName || 'codeset_ids';
      useGetForSmallData = true;  // can use this for api endpoints that have both post and get versions
      api = itemType.replaceAll('_','-');
      url = backend_url(api);
      data = await oneToOneFetchAndCache(itemType, api, paramList, paramList, useGetForSmallData, apiGetParamName);
      data.forEach((group,i) => {
        dataCache.cachePut([itemType, paramList[i]], group);
      })
      return data;

    case 'csets':
      url = 'get-csets?codeset_ids=' + paramList.join('|');
      data = await oneToOneFetchAndCache(itemType, url, undefined, paramList);
      return data;

    case 'cset_members_items':
      data = await Promise.all(
          paramList.map(
              async codeset_id => {
                url = backend_url(`get-cset-members-items?codeset_ids=${codeset_id}`);
                data = await axiosCall(url);

                return data;
              }
          )
      );
      if (isEmpty(data)) {
        debugger;
      }
      data.forEach((group,i) => {
        dataCache.cachePut([itemType, paramList[i]], keyBy(group, 'concept_id'));
      })
      return data;

    case 'edges': // expects paramList of concept_ids
      // each unique set of concept_ids gets a unique set of edges
      // check cache first (because this request won't come from getItemsByKey)
      cacheKey = paramList.join('|');
      data = dataCache.cacheGet([itemType, cacheKey]);
      if (isEmpty(data)) {
        data = await axiosCall('subgraph', {backend:true, data: paramList, useGetForSmallData: true, apiGetParamName: 'id' });
        data = formatEdges(data);
        dataCache.cachePut([itemType, cacheKey], data);
      }
      return data;

    case 'related_csets': // expects paramList of codeset_ids
      // each unique set of codeset_ids gets a unique set of related_csets
      // this is the same pattern as edges above. make a single function for
      //  this pattern like oneToOneFetchAndCache --- oh, except the formatEdges part
      cacheKey = paramList.join('|');
      data = dataCache.cacheGet([itemType, cacheKey]);
      if (isEmpty(data)) {
        const url = backend_url('related-csets?codeset_ids=' + paramList.join('|'));
        data = await axiosCall(url);
        // data = formatEdges(data);
        dataCache.cachePut([itemType, cacheKey], data);
      }
      return data;
    /*
    case 'related_csets': // expects paramList of codeset_ids
      // each unique set of codeset_ids gets a unique set of related_csets
      // this is the same pattern as edges above. make a single function for
      //  this pattern like oneToOneFetchAndCache --- oh, except the formatEdges part
      cacheKey = paramList.join('|');
      data = dataCache.cacheGet([itemType, cacheKey]);
      if (isEmpty(data)) {
        const url = backend_url('related-csets?codeset_ids=' + paramList.join('|'));
        data = await axiosCall(url);
        // data = formatEdges(data);
        dataCache.cachePut([itemType, cacheKey], data);
      }
      return data;
     */

    case 'all_csets':
      data = dataCache.cacheGet([itemType]);
      if (isEmpty(data)) {
        url = backend_url('get-all-csets');
        data = await axiosCall(url);
        // data = keyBy(data, 'codeset_id');
        dataCache.cachePut([itemType], data);
      }
      return data;

    default:
      throw new Error(`Don't know how to fetch ${itemType}`);
  }
}
async function oneToOneFetchAndCache(itemType, api, postData, paramList, useGetForSmallData, apiGetParamName ) {
  // We expect a 1-to-1 relationship between paramList items (e.g., concept_ids)
  //  and retrieved items (e.g., concepts)
  let data = await axiosCall(api, {backend:true, data: postData, useGetForSmallData, apiGetParamName });

  if (!Array.isArray(data)) {
    data = Object.values(data);
  }
  if (data.length !== paramList.length) {
    throw new Error(`oneToOneFetchAndCache for ${itemType} requires matching result data and paramList lengths`);
  }
  data.forEach((item,i) => {
    dataCache.cachePut([itemType, paramList[i]], item);
  });
  return data;
}

export function getResearcherIdsFromCsets(csets) {
  return uniq(flatten(csets.map(cset => Object.keys(cset.researchers))));
}

export function AlertMessages(props) {
  const { state: alerts, dispatch: dispatch} = useStateSlice("alerts");

  let alertsArray = Object.values(alerts);
  if (alertsArray.length) {
    return (
        <FlexibleContainer title="Alerts" position={{x: window.innerWidth - 300, y: 300}}
                           startHidden={false} >
          <pre>
            {JSON.stringify(alertsArray, null, 4)}
          </pre>

        </FlexibleContainer>);
  }

}

function Progress(props) {
  return (
    <Box sx={{ display: "flex" }}>
      <CircularProgress {...props} size="35px" />
    </Box>
  );
}

/* TODO: This is a total disaster. do something with it */
function DataWidget(props) {
  const { isLoading, error, isFetching, ukey, url, putData, status } = props;
  // console.log(props);
  const callType = putData ? "Put" : "Get";
  let msg = {};
  // target="_blank" for opening in a new tab
  // rel="noreferrer" for security
  msg.call = (
    <p>
      <a
        href={url}
        target="_blank"
        rel="noreferrer">{url}</a> ({callType})
    </p>
  );
  msg.icon = <Progress variant="determinate" value={100} />;
  if (isLoading) {
    msg.status = "Loading";
    msg.icon = <Progress />;
  }
  if (isFetching) {
    msg.status = "Fetching";
    msg.icon = <Progress />;
  }
  if (error) {
    msg.status = `${error}`;
    msg.icon = <WarningRoundedIcon fontSize="large"/>;
  }
  if (!(isFetching || isLoading || error)) {
    msg.icon = <CheckCircleRounded fontSize="large"/>
  }
  return (
    <Box
      sx={{
        border: "2px solid",
        borderRadius: "10px",
        borderColor: error ? "lightcoral" : "dodgerblue",
        background: error ? "mistyrose" : "aliceblue",
        margin: "20px",
        padding: "20px",
        fontFamily: "sans-serif",
        color: error ? "darkred" : "unset",
        // display: 'flex',
      }}
    >
      <h2 style={{display: "flex", alignItems: "center", gap: 10}}>
        {msg.icon}
        {`${status}`.charAt(0).toUpperCase() + `${status}`.slice(1)}
      </h2>
      {msg.status} <br />
      {msg.call} <br />
    </Box>
  );
}

export const backend_url = (path) => `${API_ROOT}/${path}`;

export async function axiosCall(path, {
  backend = false, data, returnDataOnly=true, useGetForSmallData = false,
  apiGetParamName, verbose = true,  }={}) {
  let url = backend ? backend_url(path) : path;
  try {
    let results;
    if (typeof(data) === 'undefined') {
      verbose && console.log("axios.get url: ", url);
      results = await axios.get(url);
    } else {
      if (useGetForSmallData && data.length <= 1000 ) {
        let qs = createSearchParams({[apiGetParamName]: data});
        url = url + '?' + qs;
        verbose && console.log("axios.get url: ", url);
        results = await axios.get(url);
      } else {
        verbose && console.log("axios.post url: ", url, 'data', data);
        results = await axios.post(url, data);
      }
    }
    return returnDataOnly ? results.data : results;
  } catch(error) {
    console.log(error.toJSON());
  }
}

export function StatsMessage(props) {
  const { codeset_ids = [], all_csets = [], relatedCsets,
          concept_ids, selected_csets, } = props;

  const relcsetsCnt = relatedCsets.length;
  return (
    <p style={{ margin: 0, fontSize: "small" }}>
      The <strong>{codeset_ids.length} concept sets </strong>
      selected contain{" "}
      <strong>{(concept_ids || []).length.toLocaleString()} distinct concepts</strong>. The
      following <strong>{relcsetsCnt.toLocaleString()} concept sets </strong>(
      {pct_fmt(relcsetsCnt / all_csets.length)}) have 1 or more
      concepts in common with the selected sets. Click rows below to select or
      deselect concept sets.
    </p>
  );
}
export function pathToArray(path) {
  if (isEmpty(path)) {
    return [];
  }
  if (Array.isArray(path)) {
    return path;
  }
  if (typeof(path) === 'string') {
    return path.split('.');
  }
  throw new Error(`pathToArray expects either array of keys or period-delimited string of keys, not ${path}`);
}

export function useDataWidget(ukey, url, putData=false) {
  console.log("is this being used?")
  debugger;
  const ax = putData ? () => axiosCall(url, {data:putData}) : () => axiosCall(url);
  const axVars = useQuery([ukey], ax);
  let dwProps = { ...axVars, ukey, url, putData };
  const dw = <DataWidget {...dwProps} />;
  return [dw, dwProps]; // axVars.data];
}
export function ViewCurrentState(props) {
  const [searchParams, setSearchParams] = useSearchParams();
  const sp = searchParamsToObj(searchParams, setSearchParams);
  const appState = useAppState();
  return (<div style={{margin: 30, }}>
    <h1>Current state</h1>

    <h2>query string parameters</h2>
    <Inspector data={sp} />

    <h2>props</h2>
    <Inspector data={props} />

    <h2>app state (reducers)</h2>
    <Inspector data={appState.getState()} />

    <h2>dataCache</h2>
    <Inspector data={dataCache.getWholeCache()} />


    <h2>The different kinds of state</h2>
    <pre>{stateDoc}</pre>
  </div>);
}
