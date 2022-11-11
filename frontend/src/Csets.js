import React, {useState, useEffect, /* useReducer, useRef, */} from 'react';
import {ComparisonDataTable} from "./ComparisonDataTable";
import {CsetsDataTable, } from "./CsetsDataTable";
import {searchParamsToObj, StatsMessage} from "./utils";
import ConceptSetCards from "./ConceptSetCard";
import TextField from '@mui/material/TextField';
import Autocomplete from '@mui/material/Autocomplete';
import Button from '@mui/material/Button';
// import Chip from '@mui/material/Chip';
import { Link, Outlet, useHref, useParams, useSearchParams, useLocation } from "react-router-dom";
import { every, get, isEmpty, } from 'lodash';
// import {isEqual, pick, uniqWith, max, omit, uniq, } from 'lodash';

/* TODO: Solve
    react_devtools_backend.js:4026 MUI: The value provided to Autocomplete is invalid.
    None of the options match with `[{"label":"11-Beta Hydroxysteroid Dehydrogenase Inhibitor","codeset_id":584452082},{"label":"74235-3 (Blood type)","codeset_id":761463499}]`.
    You can use the `isOptionEqualToValue` prop to customize the equality test.
    @ SIggie: is this fixed?
*/
function CsetSearch(props) {
  const {codeset_ids, changeCodesetIds, all_csets=[], cset_data={}} = props;

  const [keyForRefreshingAutocomplete, setKeyForRefreshingAutocomplete] = useState(0);
  // necessary to change key for reset because of Autocomplete bug, according to https://stackoverflow.com/a/59845474/1368860

  if (! all_csets.length) {
    return <span/>;
  }
  const opts = (
      all_csets
          .filter(d => !codeset_ids.includes(d.codeset_id))
          .map(d => ({
            label: `${d.codeset_id} - ${d.concept_set_version_title} ` +
                `${d.archived ? 'archived' : ''} (${d.concepts} concepts)`,
            id: d.codeset_id,
          })));
  const autocomplete = (
      // https://mui.com/material-ui/react-autocomplete/
      <Autocomplete
          key={keyForRefreshingAutocomplete}
          disablePortal
          id="add-codeset-id"
          options={opts}
          blurOnSelect={true}
          clearOnBlur={true}
          filterOptions={(options, state) => {
            let strings = state.inputValue.split(' ').filter(s => s.length);
            if (!strings.length) {
              return options;
            }
            let match = strings.map(m => new RegExp(m, 'i'))
            return options.filter(o => every(match.map(m => o.label.match(m))))
          }}
          sx={{ width: '100%', }}
          renderInput={(params) => <TextField {...params} label="Add concept set" />}
          onChange={(event, newValue) => {
            changeCodesetIds(newValue.id, 'add');
            setKeyForRefreshingAutocomplete(k => k+1);
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
  const noSelectedCsets = ! get(props, 'cset_data.selected_csets', []).length;
  if (noSelectedCsets) {
    return <div style={{}}><CsetSearch {...props} /></div>;
  }
  return (
      <div style={{}}>
        <CsetSearch {...props} />
        { <CsetsDataTable {...props} /> }
        { <ConceptSetCards {...props} /> }
      </div>)
}

// TODO: Find concepts w/ good overlap and save a good URL for that
// TODO: show table w/ hierarchical indent
// TODO: Color table: I guess would need to see if could pass extra values/props and see if table widget can use that
//  ...for coloration, since we want certain rows grouped together
function CsetComparisonPage(props) {
  const {codeset_ids=[], all_csets=[], cset_data={}} = props;
  const {hierarchy={}, selected_csets=[], concepts=[], cset_members_items=[]} = cset_data;
  // let selected_csets = all_csets.filter(d => codeset_ids.includes(d.codeset_id));
  const [nested, setNested] = useState(true);
  const [rowData, setRowData] = useState([]);

  /* TODO: review function for appropriate state management */
  useEffect(() => {
    makeRowData();
  }, [codeset_ids.length, concepts.length]);

  if (!all_csets.length) {
    return <p>Downloading...</p>
  }
  let checkboxes = Object.fromEntries(selected_csets.map(d => [d.codeset_id, false]));
  // let allConcepts = uniqWith(concept_set_members_i.map(d => pick(d, ['concept_id','concept_name'])), isEqual);
  let allConcepts = Object.fromEntries(concepts.map(d => [d.concept_id, {...d, checkboxes: {...checkboxes}}]));
  cset_members_items.forEach(d => allConcepts[d.concept_id].checkboxes[d.codeset_id] = d);

  function makeRowData(collapsed={}) {
    if (isEmpty(allConcepts)) {
      return;
    }
    if (!nested) {
      setRowData(Object.values(allConcepts));
    }
    let _rowData = [];
    let traverse = (o, pathToRoot=[], level=0) => {
      Object.keys(o).forEach(k => {
        k = parseInt(k);
        let row = {...allConcepts[k], level, pathToRoot: [...pathToRoot, k]};
        _rowData.push(row);
        if (o[k] && typeof(o[k] === 'object')) {
          row.has_children = true;
          if (!collapsed[row.pathToRoot]) {
            traverse(o[k], row.pathToRoot, level+1);
          }
        }
      })
    }
    traverse(hierarchy)
    // console.log('just after traverse', {_rowData});
    setRowData(_rowData);
  }
  function toggleNested() {
    setNested(!nested);
    makeRowData({});
  }
  let moreProps = {...props, nested, makeRowData, rowData, selected_csets, };
  // console.log({moreProps});
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
        {/* <StatsMessage {...props} /> */}
        <ComparisonDataTable {...moreProps} />
      </div>)
}

export {ConceptSetsPage, CsetComparisonPage, };
