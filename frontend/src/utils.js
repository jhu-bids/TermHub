import React, {} from 'react';
import axios from "axios";
import {API_ROOT} from "./env";
import CircularProgress from '@mui/material/CircularProgress';
import Box from '@mui/material/Box';
import { useQuery } from '@tanstack/react-query'
import { createSearchParams, } from "react-router-dom";
import { QUERYSTRING_SCALARS, INCLUDE_IN_GLOB_PROPS_BUT_NOT_QUERYSTRING, } from './App';

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

function axiosGet(path, backend=true) {
  let url = backend ? backend_url(path) : path;
  console.log('axiosGet url: ', url);
  return axios.get(url).then((res) => res.data);
}

function axiosPut(path, data, backend=true) {
  let url = backend ? backend_url(path) : path;
  console.log('axiosPut url: ', url);
  return axios.post(url, data);
}

const pct_fmt = num => Number(num).toLocaleString(undefined,{style: 'percent', minimumFractionDigits:2});
const fmt = num => Number(num).toLocaleString();
// cfmt = conditional format -- as number if number, otherwise no change
const cfmt = v => (parseInt(v) === v || parseFloat(v) === v) ? Number(v).toLocaleString() : v;

function StatsMessage(props) {
  const {codeset_ids=[], all_csets=[], cset_data={}} = props;
  const {related_csets=[], concepts } = cset_data;

  return <p style={{margin:0, fontSize: 'small',}}>The <strong>{codeset_ids.length} concept sets </strong>
    selected contain <strong>{(concepts||[]).length} distinct concepts</strong>.
    The following <strong>{related_csets.length} concept sets </strong>
    ({ pct_fmt(related_csets.length / all_csets.length) })
    have 1 or more concepts in common with the selected sets. Select from
    below if you want to add to the above list.</p>
}

function searchParamsToObj(searchParams) {
  const qsKeys = Array.from(new Set(searchParams.keys()));
  let searchParamsAsObject = {};
  console.log({QUERYSTRING_SCALARS});
  qsKeys.forEach(key => {
    let vals = searchParams.getAll(key);
    searchParamsAsObject[key] = vals.map(v => parseInt(v) == v ? parseInt(v) : v).sort(); // eslint-disable-line
    if (QUERYSTRING_SCALARS.includes(key)) {
      if (searchParamsAsObject[key].length !== 1) {
        throw new Error("Didn't expect that!");
      }
      searchParamsAsObject[key] = searchParamsAsObject[key][0];
    }
  });
  console.log({searchParamsAsObject});
  return searchParamsAsObject;
}
function updateSearchParams(props) {
    const {addProps={}, delProps=[], searchParams, setSearchParams, } = props;
    let sp = searchParamsToObj(searchParams);
    INCLUDE_IN_GLOB_PROPS_BUT_NOT_QUERYSTRING.forEach( p => { delete sp[p]; } );
    delProps.forEach( p => { delete sp[p]; } );
    sp = {...sp, ...addProps};
    setSearchParams(createSearchParams(sp));
}

function getEditCodesetFunc({searchParams, setSearchParams}) {
  return (evt) => {
    let ec = parseInt(evt.target.getAttribute('codeset_id'));
    let sp = searchParamsToObj(searchParams);
    if (sp.editCodesetId === ec) {
      updateSearchParams({delProps: ['editCodesetId']});
    } else {
      updateSearchParams({addProps: {editCodesetId: ec}});
    }
  }
}

function getCodesetEditActionFunc({searchParams, setSearchParams}) {
  return (props) => {
    const {/*codeset_id, */ concept_id, state} = props;
    const sp = searchParamsToObj(searchParams);
    let {csetEditState={}, } = sp;
    if (concept_id in csetEditState) {
      delete csetEditState[concept_id];
    } else {
      csetEditState[concept_id] = state;
    }
    return setSearchParams(createSearchParams({...sp, csetEditState}));
  }
}

// from https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/Set#implementing_basic_set_operations
function isSuperset(set, subset) {
  for (const elem of subset) {
    if (!set.has(elem)) {
      return false;
    }
  }
  return true;
}

function union(setA, setB) {
  const _union = new Set(setA);
  for (const elem of setB) {
    _union.add(elem);
  }
  return _union;
}

function intersection(setA, setB) {
  const _intersection = new Set();
  for (const elem of setB) {
    if (setA.has(elem)) {
      _intersection.add(elem);
    }
  }
  return _intersection;
}

function symmetricDifference(setA, setB) {
  const _difference = new Set(setA);
  for (const elem of setB) {
    if (_difference.has(elem)) {
      _difference.delete(elem);
    } else {
      _difference.add(elem);
    }
  }
  return _difference;
}

function difference(setA, setB) {
  const _difference = new Set(setA);
  for (const elem of setB) {
    _difference.delete(elem);
  }
  return _difference;
}

export {
  pct_fmt, fmt, cfmt, StatsMessage, searchParamsToObj, backend_url, axiosGet, axiosPut, useDataWidget,
  getCodesetEditActionFunc, getEditCodesetFunc, isSuperset, union, intersection, symmetricDifference, difference,
  updateSearchParams,
};
