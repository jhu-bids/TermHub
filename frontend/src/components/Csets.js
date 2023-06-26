import React, {useState, useRef, useEffect /* useReducer, */} from "react";
import { CsetsDataTable, CsetsSelectedDataTable } from "./CsetsDataTable";
// import {difference, symmetricDifference} from "./utils";
import ConceptSetCards from "./ConceptSetCard";
import { TextField, Autocomplete, Box, } from "@mui/material";
import Button from "@mui/material/Button";
// import Chip from '@mui/material/Chip';
// import { Link, Outlet, useHref, useParams, useSearchParams, useLocation } from "react-router-dom";
import { every } from "lodash";
import { get, isNumber, isEmpty, throttle, pullAt } from "lodash";
// import {isEqual, pick, uniqWith, max, omit, uniq, } from 'lodash';
// import Box from "@mui/material/Box";
import { Tooltip } from "./Tooltip";
import Card from "@mui/material/Card";
import CardContent from "@mui/material/CardContent";
import Typography from "@mui/material/Typography";
// import * as po from '../pages/Popover';
import { DOCS } from "../pages/AboutPage";

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
  const { codeset_ids=[], changeCodesetIds, all_csets = [] } = props;
  const [opts, setOpts] = useState([]);
  const [value, setValue] = useState([]);

  // const [keyForRefreshingAutocomplete, setKeyForRefreshingAutocomplete] = useState(0);
  // necessary to change key for reset because of Autocomplete bug, according to https://stackoverflow.com/a/59845474/1368860
  useEffect(() => {
    if (!all_csets.length) {
      return;
    }
    const _opts = initialOpts(all_csets, codeset_ids);
    setOpts(_opts);
    // setValue(_opts.filter(d => codeset_ids.includes(d.value)));
    setValue(codeset_ids);
  }, [all_csets])

  if (!all_csets.length) {
    return <span />;
  }
  console.log(value);
  const autocomplete = (
    // https://mui.com/material-ui/react-autocomplete/
    // https://stackoverflow.com/a/70193988/1368860
    <Autocomplete
      multiple
      // key={keyForRefreshingAutocomplete}
      value={value}
      onChange={(event, newValue) => {
        setValue(newValue.map(option => option.value || option));
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
      filterOptions={(options, state) => {
        let strings = state.inputValue.split(" ").filter((s) => s.length);
        if (!strings.length) {
          return options;
        }
        let match = strings.map((m) => new RegExp(m, "i"));
        return options.filter((o) => every(match.map((m) => o.label.match(m))));
      }}
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
      <Box sx={{display: 'flex', flexDirection: 'row', width: '95%'}}>
        <Tooltip content={tt} classes="help-card" placement="top-end">
          {autocomplete}
        </Tooltip>
        <Button onClick={() => {
          changeCodesetIds(value, "set");
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

function ConceptSetsPage(props) {
  const { codeset_ids } = props;
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
      {<CsetsDataTable {...props} show_selected={true}/>}
      {<CsetsDataTable {...props} show_selected={false} />}
      {<ConceptSetCards {...props} />}
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

export { ConceptSetsPage };
