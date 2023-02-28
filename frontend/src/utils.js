import React, { useRef, useLayoutEffect, useState } from 'react';
import axios from "axios";
import {API_ROOT} from "./env";
import CircularProgress from '@mui/material/CircularProgress';
import Box from '@mui/material/Box';
import { useQuery } from '@tanstack/react-query'
import { createSearchParams, } from "react-router-dom";
import { isEmpty, sum, } from 'lodash';
import { SEARCH_PARAM_STATE_CONFIG, } from './App';
import {Tooltip} from './Tooltip';

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
  console.log({sp});
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
function toRadians (angle) {
  return angle * (Math.PI / 180);
}
function ColumnHeader(props) {
  let {tooltipContent, headerContent, headerContentProps, allottedWidth, coldef} = props;
  const targetRef = useRef();
  const [headerDims, setHeaderDims] = useState({ width:0, height: 0 });

  useLayoutEffect(() => {
    if (targetRef.current) {
      setHeaderDims({
                      width: targetRef.current.offsetWidth,
                      height: targetRef.current.offsetHeight
                    });
    }
  }, []);
  coldef.requiredWidth = headerDims.width;

  let header_style = {
    cursor: 'pointer',
    whiteSpace: 'nowrap',
  }
  const rotate_header_style = {
    overflow: 'visible',
    textOverflow: 'unset',
    justifyContent: 'left', /* fixes weird thing with rightmost col shifting left when rotated */
    marginRight: 'auto',
    transform: 'translate(20%,0px) rotate(-35deg)',
    // transform: 'rotate(-35deg)',
    transformOrigin: 'bottom left',
  }
  if (allottedWidth < headerDims.width) {
    header_style = {...header_style, ...rotate_header_style};
  }
  /*
      {
        height: 182px,
        //height: auto,
        borderBottomStyle: solid,
        padding: 0,
        verticalAlign: bottom,
        overflow: visible,
        textOverflow: unset,
        marginTop: auto,
      }

   */
  // console.log({headerContent, allottedWidth, contentWidth: headerDims.width})
  let header = <span className="cset-column-header" ref={targetRef}
            style={{...header_style}}
            {...headerContentProps}
  >{headerContent}</span>
  //: {allottedWidth}/{headerDims.width}</span>
  if (tooltipContent) {
    header =  <Tooltip content={tooltipContent}>
                {header}
              </Tooltip>
  }
  return header;

  return (
    <div ref={targetRef}>
      <p>{headerDims.width}</p>
      <p>{headerDims.height}</p>
    </div>
  );
}
function setColDefDimensions({coldefs, windowSize, margin=10, }) {
  /* expecting width OR minWidth and remainingPct */
  const [windowWidth, windowHeight] = windowSize;
  const fixedWidthSum = sum(coldefs.map(d => d.width || 0))
  const remainingWidth = windowWidth - fixedWidthSum - 2 * margin;
  let usedWidth = margin * 2 + fixedWidthSum;
  coldefs = coldefs.map(d => {
    if (d.remainingPct) {
      d.width = Math.max(d.minWidth, remainingWidth * d.remainingPct)
      usedWidth += d.width;
    }
    let h = setColDefHeader(d);
    return h;
  });
  console.log({windowSize, usedWidth, fixedWidthSum, remainingWidth, });
  return coldefs;
}
function setColDefHeader(coldef) {
  let {name, headerProps={}, width, } = coldef;
  let {headerContent, headerContentProps, tooltipContent, } = headerProps;
  if (headerContent) {
    if (name) {
      throw new Error("coldef included both name and headerContent; don't know which to use.")
    }
  } else {
    if (!name) {
      throw new Error("coldef included neither name and headerContent; need one.")
    }
    headerContent = name;
  }

  coldef.name = <ColumnHeader headerContent={headerContent} headerContentProps={headerContentProps}
                        tooltipContent={tooltipContent} allottedWidth={width}
                        coldef={coldef}/>
  coldef.width = coldef.width + 'px';
  return coldef;
}

function useWindowSize() {
  const [size, setSize] = useState([0, 0]);
  useLayoutEffect(() => {
    function updateSize() {
      setSize([window.innerWidth, window.innerHeight]);
    }
    window.addEventListener('resize', updateSize);
    updateSize();
    return () => window.removeEventListener('resize', updateSize);
  }, []);
  return size;
}

function ShowWindowDimensions(props) {
  const [width, height] = useWindowSize();
  return <span>Window size: {width} x {height}</span>;
}


export {
  pct_fmt, fmt, cfmt, StatsMessage, searchParamsToObj, backend_url, axiosGet, axiosPut, useDataWidget,
  isSuperset, union, intersection, symmetricDifference, difference, updateSearchParams, clearSearchParams,
  ColumnHeader, setColDefHeader, setColDefDimensions, useWindowSize,
};
