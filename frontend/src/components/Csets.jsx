import React, { useState, useEffect, } from 'react';
import { CsetsDataTable } from './CsetsDataTable';
import {NO_BREAK_SPACE, pct_fmt} from '../utils';
import ConceptSetCards from './ConceptSetCard';
import Alert from '@mui/material/Alert';
import AlertTitle from '@mui/material/AlertTitle';
import {
  TextField,
  Autocomplete,
  Box,
  createFilterOptions,
  Chip,
} from '@mui/material';
// import { matchSorter } from 'match-sorter';
import { get, keyBy, orderBy, difference, isNumber, isEmpty, flatten } from 'lodash';
import Card from '@mui/material/Card';
import CardContent from '@mui/material/CardContent';
import Typography from '@mui/material/Typography';
import { BlankSearchIntro } from './AboutPage';
import { useDataGetter, getResearcherIdsFromCsets } from '../state/DataGetter';
import {useCids, useCodesetIds} from '../state/AppState';

/* TODO: Solve
    react_devtools_backend.js:4026 MUI: The value provided to Autocomplete is invalid.
    None of the options match with `[{"label":"11-Beta Hydroxysteroid Dehydrogenase Inhibitor","codeset_id":584452082},{"label":"74235-3 (Blood type)","codeset_id":761463499}]`.
    You can use the `isOptionEqualToValue` prop to customize the equality test.
    @ SIggie: is this fixed?
*/
function initialOpts (all_csets, codesetIds) { // option rows for autocomplete dropdown
  let opts = all_csets.filter(d => d.codeset_id)
    // .filter((d) => !codeset_ids.includes(d.codeset_id))
    .map((d) => ({
      label:
        // `${d.codeset_id} - ${d.alias}` +
        `${d.codeset_id} - ${d.concept_set_version_title}` +
        (isNumber(d.version) ? ` (v${d.version})` : '') + ' ' +
        `${d.archived ? 'archived' : ''}` +
        (d.counts ?
          get(d, ['counts', 'Expression items']).toLocaleString() +
          ' definitions (expression items), ' +
          get(d, ['counts', 'Members']).toLocaleString() +
          ' expansion concepts (members)'
          //`(${d.counts['Expression items'].toLocaleString()} expression items, ${d.counts.Members.toLocaleString()} members)`
          : '(Empty)'),
      value: d.codeset_id,
      id: `search-${d.codeset_id}`,
      // selected: codesetIds.includes(d.codeset_id),
    }));
  return opts;
}

export function CsetSearch (props = {}) {
  const { all_csets } = props;
  // const storage = useSearchParamsState();
  // const {sp} = storage;
  // const {codeset_ids, cids,} = sp;
  const [codeset_ids, codesetIdsDispatch] = useCodesetIds();
  // console.log('about to useState with:', codeset_ids);
  const [codesetIdsSelected, setCodesetIdsSelected] = useState(codeset_ids);

  /*
  const filterOptions = createFilterOptions((options, { inputValue }) => {
    // from https://github.com/kentcdodds/match-sorter#keys-string
    // having lag problems. see #540 and https://github.com/kentcdodds/match-sorter/issues/131
    let matches = matchSorter(options, inputValue, { keys: [ 'label' ] , /* threshold: matchSorter.rankings.EQUAL * / });
    // console.log({options, inputValue, matches});
    return matches;
  });
  */

  if (isEmpty(all_csets)) {
    return <p>Downloading...</p>;
  }
  const opts = initialOpts(all_csets, codeset_ids);

  let largeCsets = [];
  const unloadedCodesetIds = difference(codesetIdsSelected, codeset_ids);
  if (unloadedCodesetIds.length) {
    const unloadedCsets = all_csets.filter(
      cset => unloadedCodesetIds.includes(cset.codeset_id));
    largeCsets = unloadedCsets.filter(
      cset => get(cset, ['counts', 'Members']) > 9999);
    // console.log(unloadedCsets, largeCsets);
  }
  const largeCsetWarning = largeCsets.length ? (
    <Alert severity="error">
      <AlertTitle>VS-Hub can behave unreliably when loading large concept
        sets</AlertTitle>
    </Alert>
  ) : null;

  let invalidCodesetIds = codesetIdsSelected.filter(
    d => !opts.find(o => o.value == d));
  if (invalidCodesetIds.length) {
    throw new Error(`Invalid codeset ids: ${invalidCodesetIds.join(', ')}`);
  }
  let ctr = 0;
  let optsseen = {};
  const autocomplete = (
    <Autocomplete // https://mui.com/material-ui/react-autocomplete/
      id="add-codeset-id"
      data-testid="add-codeset-id"
      options={opts} /* opt values look like:
                      { "label": "1036505 - N3C Paroxetine (v1) 1 definitions (expression items), 2,331 expansion concepts (members)",
                        "value": 1036505, "id": "search-1036505" } */

      onChange={(event, newValue) => {
        // console.log(newValue);
        if (newValue) {
          codesetIdsDispatch({
            type: 'add_codeset_id',
            codeset_id: newValue.value,
          });
        }
      }}

      sx={{
        width: '80%',
        minWidth: '70%',
        maxWidth: '1000px',
        margin: '0 auto',
        marginTop: '10px',
        marginBottom: '10px',
      }}
      renderInput={(params) => (
        <TextField
          {...params}
          label="Select concept set"
          variant="outlined"
          style={{
            width: '100%',
            lineHeight: 50,
          }}
        />
      )}

      /*  changing it into single select just for adding
      filterOptions={filterOptions}
      multiple
      value={codesetIdsSelected}
      onChange={(event, newValue) => {
        // console.log(ctr++, newValue);
        setCodesetIdsSelected(newValue.map(option => option.value || option));
        // dataGetter.prefetch({itemType: 'everything', codeset_ids: newValue});
      }}
      renderTags={(tagValue, getTagProps) => {
        return tagValue.map((option, index) => (
          <Chip {...getTagProps({ index })} key={option} label={
            typeof(option) === 'number'? opts.find(item => item.value === option)?.label : option.label
          } />
        ))
      }}
      disablePortal
       */

      /*
      isOptionEqualToValue={(opt, value) => {
        // console.log('isOptionEqualToValue', ctr++, opt, value);
        return opt.value === value;
      }}
      getOptionLabel={(option) => {
        if (typeof option === 'number') {
          return opts.find(item => item.value === option)?.label;
        } else {
          return option.label;
        }
      }}

      // fixing impossible to track down bug with stackoverflow: https://stackoverflow.com/a/75968316/1368860
      // no idea why the bug suddenly started happening
      renderOption={(props, option) => {
        // console.log(option);
        optsseen[option.value] = true;
        if (!option.value) {
        }
        return (
          <li {...props} key={option.value}>
            {option.label}
          </li>
        )
      }}
      */

      // blurOnSelect={true}
      // clearOnBlur={true}
    />
  );
  const tt = (
    <Card variant="elevation" sx={{ border: '1px solid steelblue' }}>
      <CardContent sx={{ background: 'aliceblue' }}>
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
    <Box data-testid="csetsearch"
         sx={{ display: 'flex', flexDirection: 'row', width: '95%' }}>
      {/*<Tooltip content={tt} classes="help-card" placement="top-end">*/}
      {autocomplete}
      {tt}
      {/*</Tooltip>*/}
      {largeCsetWarning}
      {/*<Button data-testid="load-concept-sets" onClick={() => {*/}
      {/*  codesetIdsDispatch({type: "set_all", codeset_ids: codesetIdsSelected});*/}
      {/*  // changeCodesetIds(value, "set");*/}
      {/*  // setKeyForRefreshingAutocomplete((k) => k + 1);*/}
      {/*}}>*/}
      {/*  Load concept sets*/}
      {/*</Button>*/}
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

export function ConceptSetsPage () {
  const [codeset_ids, ] = useCodesetIds();
  const [cids, ] = useCids();
  const dataGetter = useDataGetter();
  const [data, setData] = useState({});
  const {
    all_csets = [], concept_ids = [], selected_csets = [],
    allRelatedCsets = {}, relatedCsets = [], researchers = {},
  } = data;

  useEffect(() => {
    (async () => {
      // dataCache.
      let all_csets = dataGetter.fetchAndCacheItems(
        dataGetter.apiCalls.all_csets, undefined);

      await dataGetter.getApiCallGroupId();

      let selected_csets = dataGetter.fetchAndCacheItems(
        dataGetter.apiCalls.csets, codeset_ids);

      let csmi = await dataGetter.fetchAndCacheItems(dataGetter.apiCalls.cset_members_items, codeset_ids);

      let concept_ids = flatten(Object.values(csmi).map(d => Object.values(d))).map(d => d.concept_id);
      concept_ids = concept_ids.concat(cids);

      all_csets = await all_csets;

      let relatedCsetConceptCounts = await dataGetter.axiosCall(
          'related-cset-concept-counts',
          {sendAlert: false, skipApiGroup: true, data: concept_ids, protocols: ['post']});

      let relatedCodesetIds = Object.keys(relatedCsetConceptCounts);

      let allCsetsObj = keyBy(all_csets, 'codeset_id');

      selected_csets = await selected_csets;

      let _allRelatedCsetsArray = relatedCodesetIds.map(
          codeset_id => {
            let cset = selected_csets[codeset_id] || {...allCsetsObj[codeset_id]};
            let counts = Object.entries(relatedCsetConceptCounts[codeset_id]);
            counts = orderBy(counts, d => d[0]);
            let vocabs = [];
            counts.forEach(([key, val]) => {
              if (key === 'concepts') {
                cset['intersecting_concepts'] = val;
              } else {
                val = Number(val).toLocaleString(undefined, {style:'percent', maximumFractionDigits: 2});
                vocabs.push(`${val}${NO_BREAK_SPACE}${key}`);
              }
            });
            cset['vocabs'] = vocabs.join(', ');
            return cset;
          });

      let allRelatedCsets = keyBy(_allRelatedCsetsArray, 'codeset_id');

      selected_csets = codeset_ids.map(d => selected_csets[d]);
      // setData(current => ({...current, selected_csets}));

      const researcherIds = getResearcherIdsFromCsets(selected_csets);
      let researchers = dataGetter.fetchAndCacheItems(
        dataGetter.apiCalls.researchers, researcherIds);

      selected_csets = selected_csets.map(cset => {
        cset = { ...cset };
        cset.selected = true;
        allRelatedCsets[cset.codeset_id] = cset;
        return cset;
      });
      // setData(current => ({...current, allRelatedCsets}));

      let relatedCsets = Object.values(allRelatedCsets).
        filter(cset => !cset.selected);
      relatedCsets = orderBy(relatedCsets, ['selected', 'intersecting_concepts'], ['desc', 'desc']);
      // This is here for making screenshots for paper. TODO:  Might want to make a user control
      // for this.
      // relatedCsets = relatedCsets.filter(d => d.precision < 1 || (d.counts||{}).Members > 10);
      // setData(current => ({...current, relatedCsets}));

      researchers = await researchers;
      // setData(current => ({...current, researchers}));
      // console.log("currentData", data);
      setData(current => ({
        ...current, concept_ids, all_csets, selected_csets,
        allRelatedCsets, relatedCsets, researchers,
      }));
    })();
  }, [codeset_ids.join('|')]);

  if ((codeset_ids.length || cids.length) && isEmpty(allRelatedCsets)) {
    return <p>Downloading...</p>;
  }

  let props = {
    codeset_ids, all_csets, relatedCsets, selected_csets,
    concept_ids, researchers, clickable: true, showTitle: true,
  };

  if (!codeset_ids.length && !cids.length) {
    // console.log("going to CsetSearch no codeset_ids and with props", props);
    return (
      <>
        <CsetSearch {...props} />
        <BlankSearchIntro/>
      </>
    );
  }
  // {<CsetsSelectedDataTable {...props} />} is added to separately show selected concept sets
  // console.log("going to CsetSearch with props", props);
  return (
    <div
      style={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
      }}
    >
      <CsetSearch {...props} />
      <CsetsDataTable {...props} show_selected={true}/>
      <CsetsDataTable {...props} show_selected={false}/>
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
