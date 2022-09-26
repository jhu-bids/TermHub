/*
TODO's
  1. todo: Page state refresh should not be 'on window focus', but on autocomplete widget selection
  2. todo: later: associated concepts: show them the concepts associated with the concept sets they've selected
  3. todo: later: intensionality: also show them concept version items (intensional). but once we've got more than one cset
      selected, start doing comparison stuff

*/
import React, {useState, useEffect, /* useReducer, useRef, */} from 'react';
import {useQuery} from "@tanstack/react-query";
import axios from "axios";
import {Table, ComparisonTable} from "./Table";
import {ComparisonDataTable} from "./ComparisonDataTable";
import {ReactQueryDevtools} from "@tanstack/react-query-devtools";
import List from "@mui/material/List";
import ListItem from "@mui/material/ListItem";
import TextField from '@mui/material/TextField';
import Autocomplete from '@mui/material/Autocomplete';
import Chip from '@mui/material/Chip';
import { Link, Outlet, useHref, useNavigate, useParams, useSearchParams, useLocation } from "react-router-dom";
import _ from 'lodash';
import {useGlobalState} from "./App";

const API_ROOT = 'http://127.0.0.1:8000'
const enclave_url = path => `${API_ROOT}/passthru?path=${path}`
const backend_url = path => `${API_ROOT}/${path}`


//TODO: How to get hierarchy data?
// - It's likely in one of the datasets we haven't downloaded yet. When we get it, we can do indents.
function ConceptSetCard(props) {
  let {cset} = props;
  return (
    // (isLoading && "Loading...") ||
    // (error && `An error has occurred: ${error.stack}`) ||
    // (isFetching && "Updating...") ||
    // (data && <div style={{
    (<div style={{
        padding: '1px 15px 1px 15px',
        margin: '5px 5px 5px 5px',
        border: '5px 5px 5px 5px',
        background: '#d3d3d3',
        borderRadius: '10px',
      }}>
        <h4>{cset.concept_set_name/*conceptSetNameOMOP*/} v{cset.version}</h4>
        <List>
          {Object.values(cset.concepts).map((concept, i) => {
            return <ListItem style={{
              margin: '3px 3px 3px 3px',
              background: '#dbdbdb',
              borderRadius: '5px',
              fontSize: '0.8em'
            }} key={i}>
              {concept.concept_id}: {concept.concept_name}
            </ListItem>
          })}
        </List>
      </div>)
  )
}

function ConceptList(props) {
  // http://127.0.0.1:8000/fields-from-objlist?objtype=OmopConceptSetVersionItem&filter=codeset_id:822173787|74555844
  // const [qsParams, setQsParams] = useGlobalState('qsParams');
  // let codeset_ids = qsParams && qsParams.codeset_id && qsParams.codeset_id.sort() || []
  const codeset_ids = props.codeset_ids || [];
  let enabled = !!codeset_ids.length

  let url = enabled ? backend_url('fields-from-objlist?') +
                      [
                        'objtype=OmopConceptSetVersionItem',
                        'filter=codeset_id:' + codeset_ids.join('|')
                      ].join('&')
                    : `invalid ConceptList url, no codeset_ids, enabled: ${enabled}`;

  const { isLoading, error, data, isFetching } = useQuery([url], () => {
    //if (codeset_ids.length) {
    //   console.log('fetching backend_url', url)
      return axios.get(url).then((res) => res.data)
      // console.log('enclave_url', enclave_url('objects/OMOPConceptSet'))
      // .then((res) => res.data.data.map(d => d.properties))
    //} else {
      //return {isLoading: false, error: null, data: [], isFetching: false}
    //}
  }, {enabled});
  // console.log('rowData', data)
  return  <div>
            <h4>Concepts:</h4>
            <Table rowData={data} />
          </div>
  /*
  let params = useParams();
  let {concept_id} = params;
  let path = `objects/OMOPConceptSet/${concept_id}/links/omopconcepts`;
  let url = enclave_url(path)
  const { isLoading, error, data, isFetching } = useQuery([path], () =>
      axios
          .get(url)
          .then((res) => res.data.data.map(d => d.properties)) )
  */
}

/* CsetSEarch: Grabs stuff from disk*/
/* TODO: Solve:
    react_devtools_backend.js:4026 MUI: The value provided to Autocomplete is invalid.
    None of the options match with `[{"label":"11-Beta Hydroxysteroid Dehydrogenase Inhibitor","codeset_id":584452082},{"label":"74235-3 (Blood type)","codeset_id":761463499}]`.
    You can use the `isOptionEqualToValue` prop to customize the equality test.
    @ SIggie: is this fixed?
*/
function CsetSearch(props) {
  let {applyChangeCallback} = props;
  // const [qsParams, setQsParams] = useGlobalState('qsParams');
  // let codeset_ids = qsParams && qsParams.codeset_id && qsParams.codeset_id.sort() || []
  const codeset_ids = props.codeset_ids || [];

  let url = backend_url('cset-versions');

  const [value, setValue] = useState([]);
  const [inputValue, setInputValue] = useState('');
  const [searchParams, setSearchParams] = useSearchParams();

  const { isLoading, error, data, isFetching } = useQuery([url], () =>
    axios
      .get(url)
      .then((res) => {
        Object.keys(res.data).forEach(csetName => {
          // delete junk concept set names
          if (csetName === 'null'             || // no name
              csetName.match(/^\d*$/) || // name is all digits
              csetName.match(/^ /)       // name starts with space
          ) {
            delete res.data[csetName]
          }
        })
        // let data = Object.entries(res.data[0]).map(([csetName,v], i) => ({label: csetName, version: v[0].version, codeset_id: v[0].codeset_id}))
        let data = Object.entries(res.data).map(
          ([csetName,v], i) => {
            v = v.sort((a,b) => a.version - b.version)
            return {
              label: csetName + (v.length > 1 ? ` (${v.length} versions)` : ''),
              codeset_id: v.at(-1).codeset_id
              // versions: v.map(d=>d.version).join(', '),
              // v,
              // latest: v.at(-1),
            }
          })
        return data
      })
  );
  useEffect(() => {
    console.log('setting value of search box')
    if (!data || !data.length) return
    let selectedCids = value && value.map(d => d.codeset_id).sort() || []
    if (!_.isEqual(codeset_ids, selectedCids)) {
      //console.log(value)
      //console.log(urlCids)
      let selection = (data || []).filter(d => codeset_ids.includes(d.codeset_id))
      setValue(selection)
    }
  }, [codeset_ids, data]);
  if (isLoading) {
    return "Loading...";
  }
  if (error) {
    console.error(error.stack)
    return "An error has occurred: " + error.stack;
  }

  return (
    <div style={{padding:'9px', }}>
      {/* <pre>getting data from: {url}</pre> */}
      {/* https://mui.com/material-ui/react-autocomplete/ */}
      {/* New way: manual state control; gets values from URL */}
      <Autocomplete
        multiple
        size="small"
        fullWidth={true}
        //disablePortal

        value={value}
        isOptionEqualToValue={(option, value) => {
          return option.codeset_id === value.codeset_id
        }}
        onChange={(event, newValue) => {
          setValue(newValue);
          let ids = newValue.map(d=>d.codeset_id)
          setSearchParams({codeset_id: ids})
        }}
        inputValue={inputValue}
        onInputChange={(event, newInputValue) => {
          // I think this is for changes in the options
          setInputValue(newInputValue);
        }}

        id="combo-box-demo-new"
        /* options={top100Films} */
        options={data}
        sx={{ width: 300 }}
        renderInput={(params) => (
            <TextField {...params}
                size="medium"
                label="Concept sets" />)}
        renderTags={(value, getTagProps) =>
          value.map((option, index) => (
            <Chip
              variant="outlined"
              label={option.label}
              size="small"
              {...getTagProps({ index })}
            />
          ))
        }
      />
    </div>)
  /* want to group by cset name and then list version. use https://mui.com/material-ui/react-autocomplete/ Grouped
     and also use Multiple Values */
}

function ConceptSetsPage(props) {
  // return <CsetSearch />;
  let navigate = useNavigate();
  //const [filteredData, setFilteredData] = useState([]);
  // const [qsParams, setQsParams] = useGlobalState('qsParams');
  // let codeset_ids = qsParams && qsParams.codeset_id && qsParams.codeset_id.sort() || []
  const codeset_ids = props.codeset_ids || [];
  let enabled = !!codeset_ids.length

  // pre-2022/09/07 url (for temporary reference):
  // let url = backend_url('fields-from-objlist?') +
  //     [
  //       'objtype=OMOPConceptSet',
  //       'filter=codeset_id:' + codeset_ids.join('|')
  //     ].join('&')
  let url = backend_url('concept-sets-with-concepts?concept_field_filter=concept_id&concept_field_filter=concept_name&codeset_id=' + codeset_ids.join('|'))

  const { isLoading, error, data, isFetching } = useQuery([url], () => {
    //if (codeset_ids.length) {
      console.log('fetching backend_url', url)
      console.log(enabled)  // TODO: remove these when done debugging
      console.log(codeset_ids)
      return axios.get(url).then((res) => res.data)
      // console.log('enclave_url', enclave_url('objects/OMOPConceptSet'))
      // .then((res) => res.data.data.map(d => d.properties))
    //} else {
      //return {isLoading: false, error: null, data: [], isFetching: false}
    //}
  }, {enabled});
  async function csetCallback(props) {
    let {rowData, colClicked} = props
    navigate(`/OMOPConceptSet/${rowData.codeset_id}`)
  }


  //function applySearchFilter(filteredData, setFilteredData) { }

  let link = <a href={url}>{url}</a>;
  let msg = enabled
              ? (isLoading && <p>Loading from {link}...</p>) ||
                (error && <p>An error has occurred with {link}: {error.stack}</p>) ||
                (isFetching && <p>Updating from {link}...</p>)
              : "Choose one or more concept sets";
  return (
      <div>
        <CsetSearch {...props} />
        {
          !enabled ? msg :
          (data && (<div>
            Concepts:
            <ConceptList />
            {/*Concept sets: */}
            {/*<Table rowData={data} rowCallback={csetCallback}/>*/}
          </div>))
          //<ReactQueryDevtools initialIsOpen />
        }
        {
          // todo: Create component: <ConceptSetsPanels>
          (codeset_ids.length > 0) && data && (
            <div style={{
              display: 'flex',
              // todo: I don't remember how to get it to take up the whole window in this case.  these are working
              // width: '100%',
              // 'flex-shrink': 0,
              // flex: '0 0 100%',
            }}>
              {data.map(cset => {
                return <ConceptSetCard key={cset.codeset_id} cset={cset} />
              })}
            </div>)
        }
        {/*<p>I am supposed to be the results of <a href={url}>{url}</a></p>*/}
      </div>)
}

// TODO: Find concepts w/ good overlap and save a good URL for that
// TODO: show table w/ hierarchical indent
// TODO: Color table: I guess would need to see if could pass extra values/props and see if table widget can use that
//  ...for coloration, since we want certain rows grouped together
function CsetComparisonPage(props) {
  // const [qsParams, setQsParams] = useGlobalState('qsParams');
  // let codeset_ids = (qsParams && qsParams.codeset_id && qsParams.codeset_id.sort()) || []
  const codeset_ids = props.codeset_ids || [];
  let enabled = !!codeset_ids.length
  // Table Variations
  // 1. this url is for simple X/O table with no hierarchy:
  // let url = enabled ? backend_url('concept-sets-with-concepts?concept_field_filter=concept_id&concept_field_filter=concept_name&codeset_id=' + codeset_ids.join('|'))
  // 2. this url is for simple hierarchy using ancestor table and no direct relationshps:
  // let url = enabled ? backend_url('cr-hierarchy?codeset_id=' + codeset_ids.join('|'))
  // todo: 3. this url uses direct relationships:
  // TODO: use cr hierarchy
  //let url = enabled ? backend_url('cr-hierarchy?format=xo&codeset_id=' + codeset_ids.join('|'))
  let url = backend_url('cr-hierarchy?format=flat&codeset_id=' + codeset_ids.join('|'))

  const { isLoading, error, data, isFetching } = useQuery([url], () => {
    return axios.get(url).then((res) => {return res.data})
  }, {enabled});
  let msg = enabled
      ? (isLoading && <p>Loading from {url}...</p>) ||
      (error && <p>An error has occurred with {url}: {error.stack}</p>) ||
      (isFetching && <p>Updating from {url}...</p>)
      : "Choose one or more concept sets";

  return (
      <div>
        <CsetSearch {...props} />
        {
          !enabled ? msg :
          (data && (<div>
            <ComparisonDataTable
                data={data}
            />
            {/*
            <ComparisonTable
              rowData={data}
              firstColName={'ConceptID'}
            />
            */}
          </div>))
        }
      </div>)
}


export {ConceptSetsPage, CsetComparisonPage, ConceptSetCard};
