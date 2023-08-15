import React, {useState, useRef, useEffect, useCallback, /* useReducer, */} from "react";
import { CsetsDataTable, CsetsSelectedDataTable } from "./CsetsDataTable";
// import {difference, symmetricDifference} from "./utils";
import ConceptSetCards from "./ConceptSetCard";
import Alert from '@mui/material/Alert';
import AlertTitle from '@mui/material/AlertTitle';
import { TextField, Autocomplete, Box, } from "@mui/material";
import { matchSorter } from 'match-sorter';
import Button from "@mui/material/Button";
// import Chip from '@mui/material/Chip';
import {every, keyBy, union, orderBy, difference,} from "lodash";
import { get, isNumber, isEmpty, flatten, intersection, } from "lodash";
// import {isEqual, pick, uniqWith, max, omit, uniq, } from 'lodash';
// import Box from "@mui/material/Box";
import { Tooltip } from "./Tooltip";
import Card from "@mui/material/Card";
import CardContent from "@mui/material/CardContent";
import Typography from "@mui/material/Typography";
// import * as po from '../pages/Popover';
import { DOCS } from "./AboutPage";
import {useDataCache} from "../state/DataCache";
import {useDataGetter, getResearcherIdsFromCsets, } from "../state/DataGetter";
import {useCodesetIds} from "../state/AppState";

/* TODO: Solve
    react_devtools_backend.js:4026 MUI: The value provided to Autocomplete is invalid.
    None of the options match with `[{"label":"11-Beta Hydroxysteroid Dehydrogenase Inhibitor","codeset_id":584452082},{"label":"74235-3 (Blood type)","codeset_id":761463499}]`.
    You can use the `isOptionEqualToValue` prop to customize the equality test.
    @ SIggie: is this fixed?
*/
function initialOpts(all_csets, codesetIds) {
  let opts = all_csets
      // .filter((d) => !codeset_ids.includes(d.codeset_id))
      .map((d) => ({
        label:
            `${d.codeset_id} - ${d.alias}` +
            (isNumber(d.version) ? ` (v${d.version})` : '') + ' ' +
            `${d.archived ? "archived" : ""}` +
            (d.counts ?
                get(d, ['counts', 'Expression items']).toLocaleString() + ' definitions (expression items), ' +
                get(d, ['counts', 'Members']).toLocaleString() + ' expansion concepts (members)'
                //`(${d.counts['Expression items'].toLocaleString()} expression items, ${d.counts.Members.toLocaleString()} members)`
                : '(Empty)'),
        value: d.codeset_id,
        // selected: codesetIds.includes(d.codeset_id),
      }));
  return opts;
}
export function CsetSearch(props) {
  const { all_csets, } = props;
  const [codeset_ids, codesetIdsDispatch] = useCodesetIds();
  const [value, setValue] = useState(codeset_ids);

  useEffect(() => {
    setValue(codeset_ids);
  }, [codeset_ids.join('|')]);

  // from https://github.com/kentcdodds/match-sorter#keys-string
  const filterOptions = (options, { inputValue }) => matchSorter(options, inputValue, { keys: [ 'label' ]});
  /*    couldn't figure out how to intercept it and see how it works, but it seems to work fine out of the box
  const filterOptions = (options, { inputValue }) => (options, inputValue) => {
    const m = matchSorter(options, inputValue);
    return m;
  } */

  if (isEmpty(all_csets)) {
    return <p>Downloading...</p>;
  }
  const opts = initialOpts(all_csets, codeset_ids);

  let largeCsets = [];
  const unloadedCodesetIds = difference(value, codeset_ids);
  if (unloadedCodesetIds.length) {
    const unloadedCsets = all_csets.filter(cset => unloadedCodesetIds.includes(cset.codeset_id));
    largeCsets = unloadedCsets.filter(cset => get(cset, ['counts', 'Members']) > 9999);
    console.log(unloadedCsets, largeCsets);
  }
  const largeCsetWarning = largeCsets.length ? (
      <Alert severity="error" >
        <AlertTitle>TermHub can behave unreliably when loading large concept sets</AlertTitle>
      </Alert>
  ) : null;

  const autocomplete = (
    // https://mui.com/material-ui/react-autocomplete/
    // https://stackoverflow.com/a/70193988/1368860
    <Autocomplete
      data-testid="autocomplete"
      multiple
      // key={keyForRefreshingAutocomplete}
      value={value}
      onChange={(event, newValue) => {
        setValue(newValue.map(option => option.value || option));
        // dataGetter.prefetch({itemType: 'everything', codeset_ids: newValue});
      }}
      isOptionEqualToValue={(opt, value) => {
        return opt.value === value;
      }}
      getOptionLabel={(option) => {
        if (typeof option === 'number') {
          return opts.find(item => item.value === option)?.label;
        } else {
          return option.label;
        }
      }}
      disablePortal
      id="add-codeset-id"
      options={opts}
      // blurOnSelect={true}
      // clearOnBlur={true}
      filterOptions={filterOptions}
      sx={{
        width: "80%",
        minWidth: "70%",
        maxWidth: "1000px",
        margin: "0 auto",
        marginTop: "10px",
        marginBottom: "10px",
      }}
      renderInput={(params) => (
        <TextField
          {...params}
          label="Select concept set"
          variant="outlined"
          style={{
            width: "100%",
            lineHeight: 50,
          }}
        />
      )}
    />
  );
  const tt = (
    <Card variant="elevation" sx={{ border: "1px solid steelblue" }}>
      <CardContent sx={{background: "aliceblue"}}>
        <Typography variant="h6" color="text.primary" gutterBottom>
          Select concept sets to view, compare, and edit.
        </Typography>
        <ul>
          <li>Click dropdown for full list</li>
          <li>Type concept set name or version ID to filter</li>
        </ul>
      </CardContent>
    </Card>
  );
  return (
      <Box data-testid="csetsearch" sx={{display: 'flex', flexDirection: 'row', width: '95%'}}>
        <Tooltip content={tt} classes="help-card" placement="top-end">
          {autocomplete}
        </Tooltip>
        {largeCsetWarning}
        <Button onClick={() => {
          codesetIdsDispatch({type: "set_all", codeset_ids: value});
          // changeCodesetIds(value, "set");
          // setKeyForRefreshingAutocomplete((k) => k + 1);
        }}
        >
          Load concept sets
        </Button>
      </Box>
  );
  /*
  return (
    <div style={{padding:'9px', }}>
      <po.Popover>
        <po.PopoverTrigger>
          {autocomplete}
        </po.PopoverTrigger>
        <po.PopoverContent className="Popover">
          <po.PopoverHeading>
            Select concept sets to view, compare, and edit.
          </po.PopoverHeading>
          <po.PopoverDescription>My popover description</po.PopoverDescription>
          <po.PopoverClose>Close</po.PopoverClose>
        </po.PopoverContent>
      </po.Popover>
    </div>)
   */
  /* want to group by cset name and then list version. use https://mui.com/material-ui/react-autocomplete/ Grouped
     and also use Multiple Values */
}

export function ConceptSetsPage(props) {
  const [codeset_ids, codesetIdsDispatch] = useCodesetIds();
  const dataGetter = useDataGetter();
  const dataCache = useDataCache();
  const [data, setData] = useState({});
  const { all_csets=[], concept_ids=[], selected_csets=[],
          allRelatedCsets={}, relatedCsets=[], researchers={}, } = data;

  // todo: Combine this with the useEffect in CsetComparisonPage.js
  useEffect(() => {
    (async () => {
      // dataCache.
      let all_csets = dataGetter.fetchAndCacheItems(dataGetter.apiCalls.all_csets, undefined);
      let selected_csets = dataGetter.fetchAndCacheItems(dataGetter.apiCalls.csets, codeset_ids);
            // returnFunc: results => [...Object.values(results)]; // isn't this the same as shape: 'array'?
      let concept_ids = dataGetter.fetchAndCacheItems(dataGetter.apiCalls.concept_ids_by_codeset_id, codeset_ids);
            // returnFunc: results => union(flatten(Object.values(results)))

      concept_ids = await concept_ids;
      concept_ids = union(flatten(Object.values(await concept_ids)));
      // setData(current => ({...current, concept_ids}));

      let relatedCodesetIdsByConceptId = dataGetter.fetchAndCacheItems(dataGetter.apiCalls.codeset_ids_by_concept_id, concept_ids);

      all_csets = await all_csets;
      // setData(current => ({...current, all_csets, }));

      const relatedCodesetIds = union(flatten(Object.values(await relatedCodesetIdsByConceptId)));

      let relatedCsetConceptIds = dataGetter.fetchAndCacheItems(dataGetter.apiCalls.concept_ids_by_codeset_id, relatedCodesetIds);
           // shape: 'obj'

      let allCsetsObj = keyBy(all_csets, 'codeset_id');

      let _allRelatedCsetsArray = relatedCodesetIds.map(csid => ({...allCsetsObj[csid]}));
      let allRelatedCsets = keyBy(_allRelatedCsetsArray, 'codeset_id');

      selected_csets = Object.values(await selected_csets);
      // setData(current => ({...current, selected_csets}));

      const researcherIds = getResearcherIdsFromCsets(selected_csets);
      let researchers = dataGetter.fetchAndCacheItems(dataGetter.apiCalls.researchers, researcherIds);

      selected_csets = selected_csets.map(cset => {
        cset = {...cset};
        cset.selected = true;
        allRelatedCsets[cset.codeset_id] = cset;
        return cset;
      });
      // setData(current => ({...current, allRelatedCsets}));

      relatedCsetConceptIds = await relatedCsetConceptIds;
      // setData(current => ({...current, relatedCsetConceptIds}));

      for (let csid in relatedCsetConceptIds) {
        let cset = allRelatedCsets[csid];
        if (!cset) {
          debugger;
          console.warn(`WHY IS csid ${csid} MISSING???`);
          continue;
        }
        let rcids = relatedCsetConceptIds[csid];
        let intersecting_concepts = intersection(concept_ids, rcids);
        cset['intersecting_concepts'] = intersecting_concepts.length;
        cset['recall'] = cset['intersecting_concepts'] / concept_ids.length;
        cset['precision'] = cset['intersecting_concepts'] / rcids.length;
        if (isNaN(cset['recall']) || isNaN(cset['precision'])) {
          debugger
        }
      }

      let relatedCsets = Object.values(allRelatedCsets).filter(cset => !cset.selected);
      relatedCsets = orderBy( relatedCsets, ["selected", "precision"], ["desc", "desc"] );
      // setData(current => ({...current, relatedCsets}));

      researchers = await researchers;
      // setData(current => ({...current, researchers}));
      setData(current => ({...current, concept_ids, all_csets, selected_csets,
        allRelatedCsets, relatedCsets, researchers, }));
    })()
  }, [codeset_ids.join('|')]);

  if (codeset_ids.length && isEmpty(allRelatedCsets)) {
    return <p>Downloading...</p>;
  }

  props = {...props, all_csets, relatedCsets, selected_csets,
      concept_ids, researchers, clickable: true, showTitle: true };

  if (!codeset_ids.length) {
    return (
      <>
        <CsetSearch {...props} />
        <div className="info-block">{DOCS.blank_search_intro}</div>
      </>
    );
  }
  // {<CsetsSelectedDataTable {...props} />} is added to separately show
  // selected concept sets
  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
      }}
    >
      <CsetSearch {...props} />
      <CsetsDataTable {...props} show_selected={true} />
      <CsetsDataTable {...props} show_selected={false} />
      <ConceptSetCards {...props} />
    </div>
  );
}

/*
function hierarchyToFlatCids(h) {
  function f(ac) {
    ac.keys = [...ac.keys, ...Object.keys(ac.remaining)];
    const r = Object.values(ac.remaining).filter(d => d);
    ac.remaining = {};
    r.forEach(o => ac.remaining = {...ac.remaining, ...o});
    return ac;
  }
  let ac = {keys: [], remaining: h};
  while(!isEmpty(ac.remaining)) {
    console.log(ac);
    ac = f(ac);
  }
  return uniq(ac.keys.map(k => parseInt(k)));
}
 */