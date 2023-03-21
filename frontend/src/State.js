import React, { createContext, /* useRef, useLayoutEffect, useState */ } from 'react';
import axios from "axios";
import {API_ROOT} from "./env";
import CircularProgress from '@mui/material/CircularProgress';
import Box from '@mui/material/Box';
import { useQuery } from '@tanstack/react-query'
import { createSearchParams, } from "react-router-dom";
import { isEmpty, sum, } from 'lodash';
import { SEARCH_PARAM_STATE_CONFIG, } from './App';
import {pct_fmt, } from "./utils";

const DataContext = createContext(null);
const QSContext = createContext(null);

function searchParamsToObj(searchParams) {
  const qsKeys = Array.from(new Set(searchParams.keys()));
  let sp = {};
  qsKeys.forEach(key => {
    let vals = searchParams.getAll(key);
    sp[key] = vals.map(v => parseInt(v) == v ? parseInt(v) : v).sort(); // eslint-disable-line
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
      fixSearchParams.delProps = ['editCodesetId'];
    }
  }
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
        fixSearchParams.delProps = [...(fixSearchParams.delProps||[]), 'csetEditState'];
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
  // console.log({sp});
  return sp;
}
function updateSearchParams(props) {
  const {addProps={}, delProps=[], searchParams, setSearchParams, } = props;
  let sp = searchParamsToObj(searchParams);
  SEARCH_PARAM_STATE_CONFIG.global_props_but_not_search_params.forEach(
      p => { delete sp[p]; } );
  delProps.forEach( p => { delete sp[p]; } );
  sp = {...sp, ...addProps};
  SEARCH_PARAM_STATE_CONFIG.serialize.forEach( p => {
    if (sp[p]) {
      sp[p] = JSON.stringify(sp[p]);
    }
  })
  const csp = createSearchParams(sp);
  setSearchParams(csp);
}
function clearSearchParams(props) {
  const {searchParams, setSearchParams, } = props;
  const sp = searchParamsToObj(searchParams);
  if (! isEmpty(sp)) {
    setSearchParams(createSearchParams({}));
  }
}
function Progress(props) {
  return (
    <Box sx={{ display: 'flex' }}>
      <CircularProgress {...props} />
    </Box>
  );
}

/* TODO: This is a total disaster. do something with it */
function DataWidget(props) {
  const { isLoading, error, isFetching, ukey, url, putData, status } = props;
  console.log(props);
  const callType = putData ? 'Put' : 'Get';
  let msg = {}
  msg.call = <p><a href={url}>{ukey}</a> ({callType})</p>
  msg.icon = <Progress variant="determinate" value={100} />;
  if (isLoading) {
    msg.status = 'Loading';
    msg.icon = <Progress/>;
  }
  if (isFetching) {
    msg.status = 'Fetching';
    msg.icon = <Progress/>;
  }
  if (error) {
    msg.status = `Error: ${error}`;
    msg.icon = <p>(need error icon?)</p>;
  }
  return (
      <Box sx={{
        border: '2px solid blue', margin: '20px', padding: '20px',
        // display: 'flex',
      }} >
        <h2>{status}</h2>
      {msg.status} <br/>
        {msg.call} <br/>
        {msg.icon}
      </Box>
  );
}

function useDataWidget(ukey, url, putData) {
  const ax = putData ? ()=>axiosPut(url, putData) : ()=>axiosGet(url)
  const axVars = useQuery([ukey], ax);
  let dwProps = {...axVars, ukey, url, putData, };
  const dw = <DataWidget {...dwProps} />;
  return [dw, dwProps, ]; // axVars.data];
}

const backend_url = path => `${API_ROOT}/${path}`

function axiosGet(path, backend=false) {
  let url = backend ? backend_url(path) : path;
  console.log('axiosGet url: ', url);
  return axios.get(url).then((res) => res.data);
}

function axiosPut(path, data, backend=true) {
  let url = backend ? backend_url(path) : path;
  console.log('axiosPut url: ', url);
  return axios.post(url, data);
}

function StatsMessage(props) {
  const {codeset_ids=[], all_csets=[], cset_data={}} = props;
  const {related_csets=[], concepts } = cset_data;

  return <p style={{margin:0, fontSize: 'small',}}>The <strong>{codeset_ids.length} concept sets </strong>
    selected contain <strong>{(concepts||[]).length} distinct concepts</strong>.
    The following <strong>{related_csets.length} concept sets </strong>
    ({ pct_fmt(related_csets.length / all_csets.length) })
    have 1 or more concepts in common with the selected sets.
    Click rows below to select or deselect concept sets.</p>
}


export {
  StatsMessage, searchParamsToObj, backend_url, axiosGet, axiosPut, useDataWidget,
  updateSearchParams, clearSearchParams,
};
