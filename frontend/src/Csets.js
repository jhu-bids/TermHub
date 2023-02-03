import React, {useState, useEffect, useCallback, /* useReducer, useRef, */} from 'react';
import {ComparisonDataTable} from "./ComparisonDataTable";
import {CsetsDataTable, } from "./CsetsDataTable";
import {searchParamsToObj, StatsMessage} from "./utils";
import ConceptSetCards from "./ConceptSetCard";
import TextField from '@mui/material/TextField';
import Autocomplete from '@mui/material/Autocomplete';
import Button from '@mui/material/Button';
// import Chip from '@mui/material/Chip';
import { Link, Outlet, useHref, useParams, useSearchParams, useLocation } from "react-router-dom";
import { every, get, set, isEmpty, throttle, pullAt, } from 'lodash';
// import {isEqual, pick, uniqWith, max, omit, uniq, } from 'lodash';
import Box from '@mui/material/Box';
import Slider from '@mui/material/Slider';

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

function traverseHierarchy({hierarchy, concepts, collapsed, }) {
  let rowData = [];
  let blanks = [];
  let traverse = (o, pathToRoot=[], level=0) => {
    // console.log({o, pathToRoot, level});
    Object.keys(o).forEach(k => {
      k = parseInt(k);
      let row = {...concepts[k], level, pathToRoot: [...pathToRoot, k]};
      if (!concepts[k]) {
        blanks.push(rowData.length);
      }
      rowData.push(row);
      if (o[k] && typeof(o[k] === 'object')) {
        row.has_children = true;
        if (!collapsed[row.pathToRoot]) {
          traverse(o[k], row.pathToRoot, level+1);
        }
      }
    })
  }
  traverse(hierarchy);
  pullAt(rowData, blanks);
  return rowData;
}
// TODO: Find concepts w/ good overlap and save a good URL for that
// TODO: show table w/ hierarchical indent
// TODO: Color table: I guess would need to see if could pass extra values/props and see if table widget can use that
//  ...for coloration, since we want certain rows grouped together
function CsetComparisonPage(props) {
  const {codeset_ids=[], all_csets=[], cset_data={}} = props;
  const {hierarchy={}, selected_csets=[], concepts=[],
          cset_members_items=[], orphans=[], conceptLookup={},
    } = cset_data;
  // let selected_csets = all_csets.filter(d => codeset_ids.includes(d.codeset_id));
  const [squishTo, setSquishTo] = useState(1);
  const [displayOptions, setDisplayOptions] = useState({});
  const [displayOption, setDisplayOption] = useState('fullHierarchy');
  const [displayData, setDisplayData] = useState({});

  const tsquish = throttle(
      val => {
        // console.log(`squish: ${squishTo} -> ${val}`);
        setSquishTo(val);
      }, 200);
  const squishChange = useCallback(tsquish);

  if (!all_csets.length) {
    return <p>Downloading...</p>
  }
  function makeRowData(collapsed={}) {
    if (isEmpty(concepts) || isEmpty(selected_csets) || isEmpty(cset_members_items)) {
      return;
    }

    // make obj containing a checkbox for each cset, initialized to false, like:
    //  {codeset_id_1: false, codeset_id_2: false, ...}
    const checkboxes = Object.fromEntries(selected_csets.map(d => [d.codeset_id, false]));

    // add copy of checkboxes to (copy of) every concept (and make obj of concepts keyed by concept_id)
    const conceptsPlus = Object.fromEntries(concepts.map(d => [d.concept_id, {...d, checkboxes: {...checkboxes}}]));

    /* for each cset_members_item (codeset has concept as expression item and/or member), replace false in checkbox
    obj with cset_members_item. example: { "codeset_id": 400614256, "concept_id": 4191479, "csm": true,
                                           "item": true, "item_flags": "includeDescendants,includeMapped" },
    This modifies appropriate checkbox in every conceptsPlus record. Its return value (csetConcepts) also
    excludes concepts that appear in hierarchy but don't appear in at least one of the selected csets. */
    const csetConcepts = Object.fromEntries(
        cset_members_items.map(d => {
          conceptsPlus[d.concept_id].checkboxes[d.codeset_id] = d;
          return conceptsPlus[d.concept_id];
        }).map(d => [d.concept_id, d]));

    let _displayOptions = {
      fullHierarchy: {
        rowData: traverseHierarchy({hierarchy, concepts: conceptsPlus, collapsed, }),
        nested: true,
        msg: ' lines in hierarchy',
      },
      csetConcepts: {
        rowData: traverseHierarchy({hierarchy, concepts: csetConcepts, collapsed, }),
        nested: true,
        msg: ' concepts in selected csets',
      },
    }

    for (let k in _displayOptions) {
      let opt = _displayOptions[k];
      opt.msg = opt.rowData.length + opt.msg;
    }
    _displayOptions.flat = {..._displayOptions.csetConcepts};
    _displayOptions.flat.nested = false;
    _displayOptions.flat.msg = 'flat';
    setDisplayOptions(_displayOptions);
    // window.dopts = _displayOptions;
  }
  function changeDisplayOption(option) {
    setDisplayOption(option);
  }
  let moreProps = {...props, makeRowData, displayData: displayOptions[displayOption], selected_csets, squishTo};
  // console.log({moreProps});
  return (
      <div>
        <h5 style={{margin:20, }}>
          {
            Object.entries(displayOptions).map(([name, opt]) =>
              <Button key={name} variant={name === displayOption ? "contained" : "outlined" } onClick={()=>changeDisplayOption(name)}>
                {opt.msg}
              </Button>)
          }
        </h5>
        {/* <StatsMessage {...props} /> */}
        <ComparisonDataTable squishTo={squishTo} {...moreProps} />
        <div style={{}} ><SquishSlider setSquish={squishChange}/> </div>
      </div>)
}

function SquishSlider({setSquish}) {
  // not refreshing... work on later
  function preventHorizontalKeyboardNavigation(event) {
    if (event.key === 'ArrowLeft' || event.key === 'ArrowRight') {
      event.preventDefault();
    }
  }
  function onChange(e, val) {
    // console.log('val: ', val);
    setSquish(val);
  }

  return (
      <Box sx={{ height: 300 }}>
        <Slider
            // key={`slider-${squish}`}
            sx={{
              width: '60%',
              marginLeft: '15%',
              marginTop: '15px',
              // '& input[type="range"]': { WebkitAppearance: 'slider-vertical', },
            }}
            onChange={onChange}
            // onChangeCommitted={onChange}
            // orientation="vertical"
            min={0.01}
            max={2}
            step={.1}
            // value={squish}
            defaultValue={1}
            aria-label="Squish factor"
            valueLabelDisplay="auto"
            onKeyDown={preventHorizontalKeyboardNavigation}
        />
      </Box>
  );
}

export {ConceptSetsPage, CsetComparisonPage, };
