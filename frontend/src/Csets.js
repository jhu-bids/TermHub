/*
TODO's
  1. todo: Page state refresh should not be 'on window focus', but on autocomplete widget selection
  2. todo: later: associated concepts: show them the concepts associated with the concept sets they've selected
  3. todo: later: intensionality: also show them concept version items (intensional). but once we've got more than one cset
      selected, start doing comparison stuff

*/
import React, {useState, useEffect, /* useReducer, useRef, */} from 'react';
import {useQuery} from "@tanstack/react-query";
import {Table, ComparisonTable} from "./Table";
import {ComparisonDataTable} from "./ComparisonDataTable";
import {CsetsDataTable, StatsMessage} from "./CsetsDataTable";
import ConceptSetCard from "./ConceptSetCard";
import {ReactQueryDevtools} from "@tanstack/react-query-devtools";
import TextField from '@mui/material/TextField';
import Autocomplete from '@mui/material/Autocomplete';
import Button from '@mui/material/Button';
import Chip from '@mui/material/Chip';
import { Link, Outlet, useHref, useNavigate, useParams, useSearchParams, useLocation } from "react-router-dom";
import {isEqual, pick, uniqWith, max, omit, uniq, } from 'lodash';

import {backend_url} from './App';
import Typography from "@mui/material/Typography";

//TODO: How to get hierarchy data?
// - It's likely in one of the datasets we haven't downloaded yet. When we get it, we can do indents.

/* CsetSEarch: Grabs stuff from disk*/
/* TODO: Solve:
    react_devtools_backend.js:4026 MUI: The value provided to Autocomplete is invalid.
    None of the options match with `[{"label":"11-Beta Hydroxysteroid Dehydrogenase Inhibitor","codeset_id":584452082},{"label":"74235-3 (Blood type)","codeset_id":761463499}]`.
    You can use the `isOptionEqualToValue` prop to customize the equality test.
    @ SIggie: is this fixed?
*/
function CsetSearch(props) {
  const {codeset_ids=[], all_csets=[], cset_data={}} = props;
  const {concept_set_members_i=[], } = cset_data;
  const [value, setValue] = useState('');
  const [inputValue, setInputValue] = useState('');
  const [searchParams, setSearchParams] = useSearchParams();

  // need to include codeset_id in label because there are sometimes two csets with same name
  //  and same version number, and label acts as key
  const opts = (
      all_csets
          .filter(d => !d.selected)
          .map(d => ({
            label: `${d.codeset_id} - ${d.concept_set_version_title} ` +
                   `${d.archived ? 'archived' : ''} (${d.concepts} concepts)`,
            id: d.codeset_id,
  })));
  console.log({opts});

  const autocomplete = (
      // https://mui.com/material-ui/react-autocomplete/
      <Autocomplete
          disablePortal
          id="add-codeset-id"
          options={opts}
          blurOnSelect={true}
          clearOnBlur={true}
          sx={{ width: '100%', }}
          renderInput={(params) => <TextField {...params} label="Add concept set" />}
          onChange={(event, newValue) => {
            setSearchParams({codeset_id: [...codeset_ids, newValue.id]})
          }}
      />);
  return (
    <div style={{padding:'9px', }}>
      {autocomplete}
    </div>)
  /* want to group by cset name and then list version. use https://mui.com/material-ui/react-autocomplete/ Grouped
     and also use Multiple Values */
}

function ConceptSetsPage(props) {
  const {codeset_ids=[], all_csets=[], cset_data={}} = props;
  const {concept_set_members_i=[], } = cset_data;
  let navigate = useNavigate();

  return (
      <div>
        <CsetSearch {...props} />
        {
           props.cset_data && <CsetsDataTable {...props} />
        }
        {
          // todo: Create component: <ConceptSetsPanels>
          (codeset_ids.length > 0 && all_csets.length) && (
            <div style={{ display: 'flex', flexWrap: 'wrap', flexDirection: 'row', margin: '20px',
              /* height: '90vh', alignItems: 'stretch', border: '1px solid green', width: '100%', 'flex-shrink': 0, flex: '0 0 100%', */
            }}>
              {
                (() => {
                  let cards = all_csets.length ? codeset_ids.map(codeset_id => {
                    let cset = all_csets.filter(d => d.codeset_id === codeset_id).pop();  // will replace cset and won't need concept-sets-with-concepts fetch
                    let concepts = concept_set_members_i.filter(d => d.codeset_id === codeset_id);
                    cset.concept_items = concepts;

                    let widestConceptName = max(Object.values(cset.concepts).map(d => d.concept_name.length))
                    let card = (all_csets.length && cset)
                        ? <ConceptSetCard  {...props}
                                           codeset_id={cset.codeset_id}
                                           key={cset.codeset_id}
                                           cset={cset}
                                           widestConceptName={widestConceptName}
                                           cols={Math.min(4, codeset_ids.length)}/>
                        : <p key={codeset_id}>waiting for card data</p>
                    return card;
                  }) : '';
                  return cards;
                })()
              }
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
  const {codeset_ids=[], all_csets=[], cset_data={}} = props;
  const {hierarchy={}, concept_set_members_i=[], concepts=[]} = cset_data;
  let selected_csets = all_csets.filter(d => codeset_ids.includes(d.codeset_id));
  const [nested, setNested] = useState(true);
  const [rowData, setRowData] = useState([]);

  useEffect(() => {
    makeRowData();
  }, [codeset_ids.length, concepts.length]);

  if (!all_csets.length) {
    return <p>Downloading...</p>
  }
  let checkboxes = Object.fromEntries(selected_csets.map(d => [d.codeset_id, false]));
  // let allConcepts = uniqWith(concept_set_members_i.map(d => pick(d, ['concept_id','concept_name'])), isEqual);
  let allConcepts = Object.fromEntries(concepts.map(d => [d.concept_id, {...d, checkboxes: {...checkboxes}}]));
  concept_set_members_i.forEach(d => allConcepts[d.concept_id].checkboxes[d.codeset_id] = true);

  function makeRowData(collapsed={}) {
    if (!nested) {
      setRowData(Object.values(allConcepts));
    }
    let rowData = [];
    let traverse = (o, path=[], level=0) => {
      Object.keys(o).forEach(k => {
        let row = {...allConcepts[k], level, path: [...path, k]};
        rowData.push(row);
        if (o[k] && typeof(o[k] === 'object')) {
          row.has_children = true;
          if (!collapsed[row.path]) {
            traverse(o[k], k, level+1);
          }
        }
      })
    }
    console.log('start traverse')
    traverse(hierarchy)
    console.log('just after traverse', {rowData});
    setRowData(rowData);
  }
  function toggleNested() {
    setNested(!nested);
    makeRowData({});
  }
  let moreProps = {...props, nested, makeRowData, rowData, selected_csets, };
  console.log({moreProps});
  return (
      <div>
        <h5 style={{margin:20, }}>
          <Button variant={nested ? "contained" : "outlined" } onClick={toggleNested}>
            {rowData.length} lines in nested list.
          </Button>
          <Button  variant={nested ? "outlined" : "contained"} sx={{marginLeft: '20px'}} onClick={toggleNested}>
            {Object.keys(allConcepts).length} distinct concepts
          </Button>
        </h5>
        <StatsMessage {...props} />
        <ComparisonDataTable {...moreProps} />
      </div>)
}

export {ConceptSetsPage, CsetComparisonPage, };
