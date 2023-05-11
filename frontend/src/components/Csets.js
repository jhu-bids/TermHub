import React, { useState /* useReducer, useRef, */ } from "react";
import { CsetsDataTable } from "./CsetsDataTable";
// import {difference, symmetricDifference} from "./utils";
import ConceptSetCards from "./ConceptSetCard";
import TextField from "@mui/material/TextField";
import Autocomplete from "@mui/material/Autocomplete";
// import Chip from '@mui/material/Chip';
// import { Link, Outlet, useHref, useParams, useSearchParams, useLocation } from "react-router-dom";
import { every } from "lodash";
// import { get, isEmpty, throttle, pullAt } from "lodash";
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
export function CsetSearch(props) {
  const { codeset_ids, changeCodesetIds, all_csets = [] } = props;
  console.log(props);

  const [keyForRefreshingAutocomplete, setKeyForRefreshingAutocomplete] =
    useState(0);
  // necessary to change key for reset because of Autocomplete bug, according to https://stackoverflow.com/a/59845474/1368860

  if (!all_csets.length) {
    return <span />;
  }
  const opts = all_csets
    .filter((d) => !codeset_ids.includes(d.codeset_id))
    .map((d) => ({
      label:
        `${d.codeset_id} - ${d.concept_set_version_title} ` +
        `${d.archived ? "archived" : ""} (${d.items} expression items, ${d.members} members)`,
      id: d.codeset_id,
    }));
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
        let strings = state.inputValue.split(" ").filter((s) => s.length);
        if (!strings.length) {
          return options;
        }
        let match = strings.map((m) => new RegExp(m, "i"));
        return options.filter((o) => every(match.map((m) => o.label.match(m))));
      }}
      sx={{
        width: "80%",
        minWidth: "300px",
        maxWidth: "600px",
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
      onChange={(event, newValue) => {
        changeCodesetIds(newValue.id, "add");
        setKeyForRefreshingAutocomplete((k) => k + 1);
      }}
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
    <Tooltip content={tt} classes="help-card" placement="top-end">
      {autocomplete}
    </Tooltip>
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
  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
      }}
    >
      <CsetSearch {...props} />
      {<CsetsDataTable {...props} />}
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
