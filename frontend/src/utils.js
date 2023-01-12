import React from 'react';
import axios from "axios";
import {API_ROOT} from "./env";
import CircularProgress from '@mui/material/CircularProgress';
import Box from '@mui/material/Box';
import { useQuery } from '@tanstack/react-query'

function Progress(props) {
  return (
    <Box sx={{ display: 'flex' }}>
      <CircularProgress {...props} />
    </Box>
  );
}
function DataWidget(props) {
  const {axVars} = props;
  const { data, isLoading, error, isFetching } = axVars;
  if (isLoading || isFetching) {
    return <Progress/>;
  }
  if (error) {
    return (
        <Box sx={{ display: 'flex' }}>
          <h2>Error</h2>
          {error}
        </Box>
    );
  }
  return <Progress variant="determinate" value={100} />;
}

function useDataWidget(key, url, putData) {
  const ax = putData ? ()=>axiosPut(url, putData) : ()=>axiosGet(url)
  const axVars = useQuery([key], ax);
  const dw = <DataWidget axVars={axVars} />;
  return [dw, axVars.data];
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
const cfmt = v => (parseInt(v) == v || parseFloat(v) == v) ? Number(v).toLocaleString() : v;

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
  qsKeys.forEach(key => {
    let vals = searchParams.getAll(key);
    searchParamsAsObject[key] = vals.map(v => parseInt(v) == v ? parseInt(v) : v).sort();
  });
  searchParamsAsObject.codeset_ids = searchParamsAsObject.codeset_id;
  delete searchParamsAsObject.codeset_id;
  return searchParamsAsObject;
}
export {pct_fmt, fmt, cfmt, StatsMessage, searchParamsToObj, backend_url, axiosGet, axiosPut, useDataWidget};
