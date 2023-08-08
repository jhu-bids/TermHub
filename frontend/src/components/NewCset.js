// misnamed file (was misnamed when it was editCset.js also) because
//  it includes a bunch of stuff used for cell contents when not editing
//  new cset also

import BlockIcon from "@mui/icons-material/Block";
import {Add} from "@mui/icons-material";
// import {SvgIcon} from "@mui/material";
import Box from "@mui/material/Box";
// import Paper from "@mui/material/Paper";
// import TextareaAutosize from "@mui/base/TextareaAutosize";
// import CardContent from '@mui/material/CardContent';
import {get, isEmpty} from "lodash"; // set, map, omit, pick, uniq, reduce, cloneDeepWith, isEqual, uniqWith, groupBy,
import IconButton from "@mui/material/IconButton";
import {Tooltip} from "./Tooltip";
import {howToSaveStagedChanges} from "./CsetComparisonPage";
import {newCsetAtlasJson} from "../state/AppState";
import Button from "@mui/material/Button";
import React from "react";

const checkmark = <span>{"\u2713"}</span>;

export function getCodesetEditActionFunc({ newCset, newCsetDispatch, csmi }) {
  return (props) => {
    // this function will be called editAction and passed around as needed
    const {
      evt,
      // csmi,  // not sure if this should come from closure or props sent to the generated function
      clickAction,
      flag,
      cset_col: { codeset_id },
      row: { concept_id },
      no_action = false,
    } = props;
    const { definitions = {}, } = newCset;
    let definition = getItem({
      codeset_id,
      concept_id,
      newCset,
      clickAction,
      csmi,
    });
    if (clickAction === "Update") {
      definition[flag] = !definition[flag];
    }
    if (clickAction.startsWith("Cancel")) {
      // delete csidState[concept_id];
      newCsetDispatch({type: 'deleteDefinition', concept_id});
    } else {
      // csidState[concept_id] = definition;
      newCsetDispatch({type: 'addDefinition', definition});
    }
    evt.stopPropagation();
  };
}

export function saveChangesInstructions(props) {
  const { newCset, } = props;
  const params = { newCset, };
  return howToSaveStagedChanges(params);
}

const FLAGS = {
  // includeMapped: {component: TranslateIcon, sz:12, tt: 'Include Mapped'},
  // includeDescendants: {component: TreeIcon, sz:12, tt: 'Include descendants'},
  // isExcluded: {component: BlockIcon, sz:12, tt: 'Exclude'},
  includeDescendants: { symbol: "D", tt: "Include descendants" },
  includeMapped: { symbol: "M", tt: "Include Mapped" },
  isExcluded: { symbol: "X", tt: "Exclude" },
};
export function textCellForItem(item) {
  // for use in csv download
  let textPieces = [];
  let text = '';
  if (item.item) {
    text = 'In definition';
    textPieces.push('In definition')
    if (!isEmpty(item.item_flags)) {
      text += `: ${item.item_flags}`;
      textPieces.push(': ');
      textPieces.push(item.item_flags);
    }
  }
  /*
  for (let flag in FLAGS) {
    if (item[flag]) {
      textPieces.push(FLAGS[flag].symbol);
    }
  }
   */
  if (item.csm) {
    text += (text.length ? '; ' : '');
    text += 'In expansion';
    textPieces.push('In expansion');
    // textPieces.push("\u2713");
  }
  return text;
  //return textPieces.join('');
}
const ICONS = {
  block: {
    symbol: (
      <BlockIcon
        sx={{
          width: "12px",
          height: "12px",
          margin: 0,
          padding: 0,
          fontWeight: "bolder",
        }}
      />
    ),
    tt: "Cancel / Remove",
  },
  ...FLAGS,
};
function OptionIcon(props) {
  const {
    item,
    flag,
    editing,
    cset_col: { codeset_id },
    row: { concept_id },
    editCodesetId,
    editAction,
  } = props;
  const icon = ICONS[flag];
  if (flag == "block") {
    return <Tooltip label={icon.tt}>{icon.symbol}</Tooltip>;
  }
  const on = item[flag];
  // const icon = FLAGS[flag];
  // const OptIcon = icon.component;
  return (
    <Tooltip label={icon.tt + " =" + (on ? "True" : "False")}>
      <IconButton
        onClick={
          editing && !item.fakeItem
            ? (evt) => {
                editAction({evt, ...props, clickAction: "Update"})
              }
            : null
        }
        size="9px"
        // color={on ? 'primary' : 'secondary'}
        sx={{
          // width:icon.sz+'px', height:icon.sz+'px',
          cursor: editing ? "pointer" : "default",
          fontWeight: on ? "bolder" : "regular",
          fontSize: ".7rem",
          margin: 0,
          padding: 0,
          opacity: on ? 1 : 0.6,
          // backgroundColor: on ? 'lightblue' : '',
          // border: on ? '1px solid white' : '',
          // border: '2px solid white',
        }}
      >
        {icon.symbol}
      </IconButton>
    </Tooltip>
  );
}
export function getItem({
  fakeItem,
  codeset_id,
  concept_id,
  csmi,
  newCset,
  clickAction,
}) {
  /*  if no item for codeset_id,concept_id, return undefined;
      otherwise, return copy of item,
        1) from edit state if available there,
        2) from csmi (concept_set_members_items),
        3) new if clickAction === 'Add'
      set item.stagedAction if action parameter included   */
  let item = fakeItem;
  if (!item) {
    if (codeset_id === get(newCset, ['codeset_id'])) {
      item = newCset.definitions[concept_id];
    } else {
      item = get(csmi, [codeset_id, concept_id]);
    }
  }
  if (clickAction) {
    item = { ...item };
    if (clickAction.startsWith("Cancel")) {
      return item;
    }
    if (isEmpty(item)) {
      if (clickAction === "Add") {
        item = { codeset_id, concept_id, csm: false, item: true };
        Object.keys(FLAGS).forEach((flag) => {
          item[flag] = false;
        });
      } else {
        throw new Error("wasn't expecting no item except on Add");
      }
    } else {
      if (clickAction === "Add") {
        item.item = true;
        Object.keys(FLAGS).forEach((flag) => {
          item[flag] = false;
        });
      }
      if (item.stagedAction === "Add" && clickAction === "Update") {
        clickAction = "Add";
      }
      if (item.stagedAction && item.stagedAction !== clickAction) {
        throw new Error("wasn't expecting a different action");
      }
    }
    if (item) {
      item.stagedAction = clickAction;
    }
  }
  return item;
}
function cellInfo(props) {
  if ("fakeItem" in props) {
    return { editing: props.editing, item: props.fakeItem };
  }
  const {
    cset_col: { codeset_id },
    row: { concept_id },
    newCset,
    csmi,
  } = props;
  const item = getItem({
    csmi,
    codeset_id,
    concept_id,
    newCset,
  });
  const editing = codeset_id === get(newCset, ['codeset_id']);

  return { editing, item };
}
export const defaultCellStyle = {
  // https://stackoverflow.com/questions/19461521/how-to-center-an-element-horizontally-and-vertically
  padding: 0,
  display: "flex",
  alignItems: "center",
  justifyContent: "center",
};
export function cellStyle(props) {
  const { editing, item } = cellInfo(props);
  return _cellStyle(item, editing);
}
function _cellStyle(item, editing) {
  let style = { ...defaultCellStyle };
  if (!item) {
    return style; // no styling
  }
  if (item.csm && item.item) {
    style.backgroundColor = "orange";
  } else if (item.csm) {
    style.backgroundColor = "lightgray";
  } else if (item.item) {
    style.backgroundColor = "plum";
  }
  editing = editing ?? item.editing;
  if (editing) {
    if (item.stagedAction === "Add") {
      style.backgroundColor = "lightgreen";
    } else if (item.stagedAction === "Remove") {
      style.backgroundColor = "pink";
    } else if (item.stagedAction === "Update") {
      style.backgroundColor = "lightblue";
    }
  }
  return style;
}

/*
function iconset(subset) {
  let icons = ICONS;
  if (subset) {
    icons = pick(icons, subset);
  }
  return Object.entries(icons).map(([k,v]) => {
    return <OptionIcon key={k} {...fakeOptProps([], [k])} />;
    // return <OptionIcon {...props} {...{item, flag, editing}} key={flag} />
    return  <IconButton size='9px' key={k}
                        sx={{ alignItems: 'stretch', fontSize: '.7rem',
                          margin: '0px 2px 2px 2px', padding: '0px', }} >
      {v.symbol}
    </IconButton>
  });
}
 */
function fakeOptProps(itemProps = [], flag) {
  // so that we can use real (excessively complicated) logic to show different
  //  kinds of items in the Legend
  let item = { fakeItem: true };
  itemProps.forEach((f) => (item[f] = true));
  let props = { item, cset_col: {}, row: {}, flag };
  return props;
}
const FLAG_ABBREV = {
  D: "includeDescendants",
  M: "includeMapped",
  X: "isExcluded",
  c: "csm",
  i: "item",
};
function flagAbbrev(letter) {
  return FLAG_ABBREV[letter];
}
function fakeCell(props) {
  let { editing, stagedAction, flags = "DMX" } = props;
  let item = { fakeItem: true, stagedAction, item: !!stagedAction };
  flags.split("").forEach((f) => {
    item[flagAbbrev(f)] = true;
  });
  if (!(item.csm || item.item)) {
    item = null;
  }

  const style = _cellStyle(item, editing);
  let cellProps = {
    csmi: {},
    editing,
    fakeItem: item,
    cset_col: {},
    row: {},
  };
  // return <CellContents {...cellProps} />;
  let content = cellContents({ ...cellProps });
  return (
    <Box
      sx={{
        width: "100px",
        height: "100%",
        border: "1px solid gray",
        ...style,
      }}
    >
      {content}
    </Box>
  );
}
export function Legend({editing=false}) {
  let itemTypes = {
    "Color meanings": {},
    "Concept is in the definition but not the expansion": {
      content: fakeCell({editing: false, flags: "i"}),
    },
    "Concept is in the expansion but not the defintion": {
      content: fakeCell({editing: false, flags: "c"}),
    },
    "Concept is in the definition and the expansion": {
      content: fakeCell({editing: false, flags: "ci"}),
    },
    "Concept is not in this concept set at all": {
      content: fakeCell({editing: false, flags: ""}),
    },
    "Definition flags": {},
    "includeDescendants": {
      content: fakeCell({editing: false, flags: "ciD"}),
    },
    "includeMapped": {
      content: fakeCell({editing: false, flags: "ciM"}),
    },
    "isExcluded": {
      content: fakeCell({editing: false, flags: "iX"}),
    },
  }
  if (editing) {
    itemTypes = {
      ...itemTypes,
      // "Expression item but not member (only shows flags set to true)": { item: true, content: iconset(['includeDescendants', 'includeMapped', 'isExcluded']) },
      // "Both member and expression item": { csm: true, item: true, content: iconset(['includeDescendants', 'includeMapped', 'isExcluded']) },
      "Concept set being edited": {},
      "Click D, M, X to toggle definiton flags": {},
      "Add concept to concept set definition": {
        content: fakeCell({editing: true, flags: ""}),
      },
      "Add concept (already in expansion) to concept set definition": {
        content: fakeCell({editing: true, flags: "c"}),
      },
      /*
      "Click to toggle includeDescendants": {
        content: <div style={{textAlign: 'center', paddingTop: '3px'}}>D</div>
      },
      "Click to toggle includeMapped": {
        content: <div style={{textAlign: 'center', paddingTop: '3px'}}>M</div>
      },
      "Click to toggle isExcluded": {
        content: <div style={{textAlign: 'center', paddingTop: '3px'}}>X</div>
      },
       */
      "Concept added": {
        content: fakeCell({editing: true, flags: "i", stagedAction: "Add"}),
      },
      "Concept updated": {
        content: fakeCell({editing: true, flags: "i", stagedAction: "Update"}),
      },
      /*  no longer needed since starting from empty new cset
      "Concept removed": {
        content: fakeCell({editing: true, flags: "i", stagedAction: "Remove"}),
      },
       */
    }
  };
  const items = Object.entries(itemTypes).map(([k, v]) => {
    // const {content='\u00A0\u00A0\u00A0\u00A0'} = v;
    return LegendItem({ label: k, content: v.content });
  });
  return <div>{items}</div>;
}
function LegendItem({ label, content = null, style }) {
  return (
    <Box
      sx={{
        width: "550px",
        border: content ? "1px solid gray" : "",
        display: "flex",
        zIndex: 5000,
        margin: "4px",
        alignItems: "stretch",
        flexDirection: "row",
      }}
      key={label}
    >
      <Box
        sx={{
          width: "450px",
          display: "flex",
          alignItems: "center",
          padding: "3px",
          minHeight: "1.5rem",
          fontWeight: content ? "normal" : "bolder",
        }}
      >
        {label}{" "}
      </Box>
      {content ? (
        <Box sx={{ width: "100px", border: "1px solid gray", ...style }}>
          {content}
        </Box>
      ) : null}
    </Box>
  );
}
export function cellContents(props) {
  /*
      Populates cell with appropriate icons.
      If not editing, show (nothing is clickable):
        - Blank if concept is neither an item nor a member
        - Checkmark if item is member but not item
        - Flags that are true if it is an item
      If editing, show (everything is clickable):
        - Add icon if concept is neither an item nor a member
        - Add icon with lightgray background if member but not item (see cellStyle)
        - Four icons if item is existing concept_set_version_item with no staged edits:
          - Remove (to remove it as an item from the codeset)
          - Three flags (D, M, X), bold if true, light if not; clicking toggles
        - Four icons if staged for add or update:
          - Cancel (to unstage edits)
          - Three flags (D, M, X), bold if true, light if not; clicking toggles
        - If staged for deletion:
          - Just the word 'Deleted', clicking cancels deletion
   */
  const { editAction } = props;
  const { item, editing } = cellInfo(props);
  let removeIcon, clickAction, contents;
  let flags = Object.keys(FLAGS);
  if (!editing) {
    if (item && item.item) {
      flags = Object.keys(FLAGS).filter((key) => item[key]);
      contents = flags.map((flag) => {
        return (
          <OptionIcon {...props} {...{ item, flag, editing }} key={flag} />
        );
      });
    } else if (item && item.csm) {
      contents = checkmark;
    } else if (item) {
      throw new Error("Impossible: item has neither csm nor item set to true");
    } else {
      contents = "";
    }
  } else {
    // editing
    if (!item || !item.item) {
      clickAction = "Add";
      contents = (
        <Add
          style={{ cursor: "pointer" }}
          onClick={(evt) => editAction({ evt, ...props, clickAction })}
        />
      );
      // return contents;
    } else {
      // item is an item, either existing or staged for addition
      if (item.stagedAction) {
        // staged edits
        clickAction = `Cancel ${item.stagedAction}`;
        if (item.stagedAction === "Remove") {
          contents = (
            <Tooltip label={clickAction}>
              <span // style={{ cursor: 'pointer', width:'70px', ...centered}}
                onClick={(evt) => editAction({ evt, ...props, item, clickAction })}
              >
                Deleted
              </span>
            </Tooltip>
          );
          return contents;
        }
      } else {
        clickAction = "Remove";
      }
    }
    removeIcon = // if any staged edit, this icon cancels, otherwise icon removes existing item
      clickAction === "Add" ? null : (
        <Tooltip label={clickAction}>
          <BlockIcon
            onClick={(evt) => editAction({ evt, ...props, item, clickAction })}
            sx={{
              width: "12px",
              height: "12px",
              marginBottom: "1px",
              padding: 0,
            }}
          />
        </Tooltip>
      );
  }
  const cellStuff = (
    <div onClick={(evt) => { editAction({ evt, ...props, clickAction, no_action: true });}}
      style={{display: "flex", alignItems: "center", gap: "4px", marginTop: "1px"}}
    >
      {removeIcon}
      {contents || contents === ""
        ? contents
        : flags.map((flag) => {
            //Object.keys(ICONS).map((flag) => {}
            if (!item) {
              throw new Error("that's not expected");
            }
            // either contents already set, or ready to get flag icons
            return (
              <OptionIcon {...props} {...{ item, flag, editing }} key={flag} />
            );
          })}
    </div>
  );
  return cellStuff;
} /* was going to use tagged templates; see https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Template_literals
  but these docs are react chunks, so, should be easier
function processTemplate(strings, params={}) {
  const keys = Object.keys(params);
  if (strings.length !== keys.length + 1) {
    throw new Error("not supposed to happen, wrong number of params");
  }

}
function getDoc(docName, params={}) {
  const tmpl = DOCS[docName];
  return processTemplate(tmpl, params);
}
*/
export function newCsetAtlasWidget(newCset) {
  const atlasJson = newCsetAtlasJson(newCset);
  return <>
    <Button
        onClick={() => {
          navigator.clipboard.writeText(atlasJson);
        }}
    >
      Copy ATLAS JSON to clipboard
    </Button><br/>
    <textarea style={{width: 500, height:300, }} value={atlasJson} readOnly/>
  </>;
}