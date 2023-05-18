import React, { useState, useRef } from "react";
import { NavLink, useParams, useLocation } from "react-router-dom";
import List from "@mui/material/List";
import ListItem from "@mui/material/ListItem";
import ListItemButton from "@mui/material/ListItemButton";
import IconButton from "@mui/material/IconButton";
import CloseIcon from "@mui/icons-material/Close";
import Accordion from "@mui/material/Accordion";
import AccordionSummary from "@mui/material/AccordionSummary";
import AccordionDetails from "@mui/material/AccordionDetails";
import Typography from "@mui/material/Typography";
import ExpandMoreIcon from "@mui/icons-material/ExpandMore";
import Draggable from "react-draggable";
import Box from "@mui/material/Box";
import Switch from "@mui/material/Switch";
import Paper from "@mui/material/Paper";
import Collapse from "@mui/material/Collapse";
import FormControlLabel from "@mui/material/FormControlLabel";
import useMeasure from "react-use/lib/useMeasure";
import { cloneDeep } from "lodash";
import Button from "@mui/material/Button";

import { useAppState, useStateSlice } from "./State";
import { CsetSearch } from "./Csets";

let _pages = [
  { name: "Cset search", href: "/OMOPConceptSets" },
  { name: "Cset comparison", href: "/cset-comparison" },
  { name: "Example comparison", href: "/testing" },
  // { name: "Graph", href: "/graph" },
  // {name: 'Upload CSV', href: '/upload-csv', noSearch: true, },
  // TODO: re-add Download (CSets, bundles, json...) at some point
  //{name: 'Download CSet JSON', href: '/download-json', noSearch: true, },
  { name: "Help / About", href: "/about" },
];
if (window.location.host === 'localhost:3000') {
  _pages.push({ name: "Graph", href: "/graph" });
}
export function getPages(props) {
  let pages = cloneDeep(_pages);
  if (!props.codeset_ids.length) {
    let page = pages.find((d) => d.href == "/cset-comparison");
    page.disable = true;
    page.tt =
        "Select one or more concept sets in order to view, compare, or edit them.";
  }
  return pages;
}
const contentComponents = {
  DummyComponent: DummyComponent,
  CsetSearch: CsetSearch,
};
/* thoughts about where this is going: */
export const defaultContentItems = {
  dummy: {
    name: "dummy",
    show: false,
    componentName: "DummyComponent",
    props: { foo: "bar" },
  },
  search: {
    name: "search",
    componentName: "CsetSearch",
    requiredProps: {
      appStateSlices: ["codeset_ids"],
      dataStateSlices: ["all_csets"],
    },
    showInMenu: () => true, // always
    showAs: "flexible",
    defaultShowProps: {
      style: { position: "absolute" },
      place: {
        x: 20,
        y: 20,
        width: (windowSize) => windowSize.width * 0.9,
        height: 400,
      },
      shown: true, // turn off when comparison is turned on (maybe other rules)
      collapsed: false,
      collapseProps: {
        width: ({ name }) => name.length + 2 + "em",
        height: "2em",
      },
    },
    currentShowProps: {},
  },
  csetsDataTable: {
    name: "csetsDataTable",
    componentName: "CsetsDataTable",
    requiredProps: {
      appStateSlices: ["codeset_ids"],
      dataStateSlices: ["selected_csets", "related_csets"],
    },
    showInMenu:
      () =>
      ({ codeset_ids }) =>
        codeset_ids > 0,
    showAs: "panel",
    defaultShowProps: {
      style: { position: "absolute" }, // should be same size and below search
      place: {
        x: 20,
        y: 20,
        width: (windowSize) => windowSize.width * 0.9,
        height: 400,
      },
      shown: true, // after codeset_ids (or selected_csets) changes
      collapsed: false,
      collapseProps: {
        width: ({ name }) => name.length + 2 + "em",
        height: "2em",
      },
    },
    currentShowProps: {},
  },
  // conceptNavigation: { }, // doesn't exist yet (but may include search, tabular, graphical, ...)
  comparison: {
    name: "csetComparison",
    componentName: "CsetComparisonPage", // OR:
    subComponents: "", // CsetComparisonTable + options and controls, legend
    // name: 'editCset', // does this remain an option on comparison, or become (optionally) independent
  },
};
export function contentItemsReducer(state = {}, action) {
  /* For use with ContentMenuItems and ContentItems, but not currently using it.
   */
  console.log({ state, action });
  if (!action.type) return state;
  if (["show", "hide", "toggle"].includes(action.type)) {
    // this is for state being an array; but it's an obj now:
    //    const idx = state.findIndex(o => o.name === action.name);
    //    let option = {...state[idx]};
    let option = { ...state[action.name] };
    switch (action.type) {
      case "show":
        option.show = true;
        break;
      case "hide":
        option.show = false;
        break;
      case "toggle":
        option.show = !option.show;
    }
    // state[idx] = option;
    return { ...state, [action.name]: option };
  }
  if (action.type === "new") {
    // return [...state, action.payload];
    return { ...state, [action.name]: action.payload };
  }
  throw new Error(`invalid action.type: ${action}`);
}
export function DummyComponent({ foo }) {
  return <h3>dummy component: {foo}</h3>;
}
function popupWindow(props) {
  const { url, windowName } = props;
  const windowFeatures = "left=100,top=100,width=320,height=620";
  const handle = window.open(url, windowName, windowFeatures);
  if (!handle) {
    // The window wasn't allowed to open
    // This is likely caused by built-in popup blockers.
    throw new Error(`couldn't open popup ${windowName}`);
  }
}
export function AssembleComponent({ id, title, Component, componentProps }) {
  /* this takes an object or props with a componentName (or Component?)
      and props. To be used with other containers, so the other containers
      can focus on their containing features (drag, collapse, etc.) and
      accept this as a child
   */
  <Component {...componentProps} />;
}
export function FlexibleContainer({ title, children }) {
  /* TODO: dragging triggers click action; not great. solutions to try here:
      https://github.com/react-grid-layout/react-draggable/issues/531
      Also, I stretched the IconButton to 100% width because the x on the
      right can end up off the screen, but it makes it a wide flat oval
      on hover
   */
  const [display, setCollapsed] = useState("collapsed");
  const draggableRef = useRef(null);
  const setDisplay = (_display) => {
    setCollapsed(() => _display);
  };
  // console.log({title, Component, componentProps})

  const position = { x: 0, y: 0 };
  let displayedContent;
  let style = {
    cursor: "move",
    display: "inline-block",
  };
  if (display === "collapsed") {
    displayedContent = (
      <Button
        sx={{ ...style, marginRight: "4px" }}
        variant="contained"
        color="primary"
        onClick={() => setDisplay("show")}
      >
        Show {title}
      </Button>
    );
    return displayedContent; // maybe better if the buttons aren't draggable
  } else if (display === "show") {
    const closeFunc = () => setDisplay("collapsed");
    style = {
      ...style,
      zIndex: 10,
      position: "absolute",
      backgroundColor: "#EEE",
      border: "2px solid green",
      minWidth: "200px",
      minHeight: "200px",
    };
    displayedContent = (
      <>
        <IconButton onClick={closeFunc} sx={{ position: "absolute", right: 0 }}>
          <CloseIcon />
        </IconButton>
        {children}
      </>
    );
  }
  return (
    <Draggable nodeRef={draggableRef} defaultPosition={position}>
      <Box
        ref={draggableRef}
        closeFunc={() => setDisplay("collapsed")}
        sx={style}
      >
        {displayedContent}
      </Box>
    </Draggable>
  );
}

/*
export function PopupContentItem(props) {
  const params = useParams();
  const {contentItemName, context} = params;
  const {state, dispatch} = useStateSlice('contentItems');
  const item = state[contentItemName];
  if (context === 'popup') {
    console.log(window.opener);
  }
  const Component = contentComponents[item.componentName];
  return <Component {...props}/>;

  return (
      <div>
        <h4>content item</h4>
        <pre>{JSON.stringify({params}, null, 2)}</pre>
      </div>
  );
}
export function ContentMenuItems(props) {
  /* Displays a (menu) list of currently closed but openable content items
      as tracked in AppState.contentItems. Got it sort of working, but not
      using at the moment. May return to it.
   * /
  const location = useLocation();
  const {search: searchParams} = location;
  const appState = useAppState();
  const [contentItems, contentItemsDispatch] = appState.getSlice('contentItems');
  const buttons = Object.values(contentItems).filter(item => (item.showInMenu||(()=>false))()).map(
      item => {
        const {name, showAs, noSearchParamsOnLink, content, componentName, props} = item;
        let buttonProps = {};
        if (showAs === 'popup') {
          const url = `/contentItem/popup/${name}${noSearchParamsOnLink ? '' : searchParams}`;
          buttonProps.onClick = () => popupWindow({url, windowName: name});
          // component={NavLink} // NavLink is supposed to show different if it's active; doesn't seem to be working
          // to={`/contentItem/${name}${noSearchParamsOnLink ? '' : searchParams}`}
          // variant={page.href === window.location.pathname ? 'contained' : 'text'} // so, this instead
          // onClick={handleCloseNavMenu}
          // sx={{ my: 2, color: 'white', display: 'block' }}
        }
        else if (showAs === 'flexible') {
          // const Component = contentComponents[item.componentName];
          buttonProps.onClick = () => contentItemsDispatch({type: 'show', name: item.name})
          /*
          dialogs.push(
              <dialog key={name} id={`dialog-${name}`} ref={dialogRef}
                  style={{position: 'absolute', width:'90%', height:'400px'}}>
                <h5>{item.name}</h5>
                <Component {...props} />
              </dialog>
          );
           * /
        }
        return (
            <ListItem key={name} disablePadding>
              <ListItemButton {...buttonProps} >
                Show {name}
              </ListItemButton>
            </ListItem>);
      }
  );
  return (
      <List>
        {buttons}
      </List>
  ) // <pre>{JSON.stringify({contentItems}, null, 2)}</pre>
}
export function ContentItems(props) {
  /* Displays currently open items as tracked in AppState.contentItems.
     Haven't gotten it working reasonably as yet. Putting on hold. May
     return to it.
   * /
  const location = useLocation();
  const {search: searchParams} = location;
  const appState = useAppState();
  const [contentItems, contentItemsDispatch] = appState.getSlice('contentItems');
  const items = Object.values(contentItems).filter(item => item.show).map(
      item => {
        const {name, showAs, noSearchParamsOnLink, content, componentName, } = item;
        if (showAs === 'popup') {
          // should already be showing in window somewhere
        }
        else if (showAs === 'flexible') {
          /*
            Trying to get CsetSearch working in a
            Flexible container. A couple problems: container gets hidden behind left
            menu drawer and is not opaque, so main content shows through it; and
            props aren't being passed correctly -- but shouldn't fix that because
            CsetSearch should extract what it needs from Context instead of props
            (as should everything eventually)
           * /
          // if (content) return content;
          const Component = contentComponents[componentName];
          return <FlexibleContainer key={name} title={name} Component={Component} componentProps={props} />;
        }
      }
  );
  return (
      <>
        {items}
      </>
  );
}
function usePaperContainer({children}) {
// const [ref, { x, y, width, height, top, right, bottom, left }] = useMeasure();
const [ref, measures ] = useMeasure();
return { ref, measures, contents: (
      <Paper ref={ref} sx={{ m: 1 }} elevation={4} /*measures={measures}* />
          {children}
        </Paper>
    )};
}
function CollapsibleContainerWithSwitch({id, title, children}) {
  // from https://mui.com/material-ui/transitions/
  const [checked, setChecked] = useState(false);
  const { measures, contents } = usePaperContainer({children});

  const handleChange = () => {
    setChecked((prev) => !prev);
  };
  console.log(measures, contents);
  const {width, height} = measures;
  return (
      <Box sx={{ }}>
        <FormControlLabel
            control={<Switch checked={checked} onChange={handleChange} />}
            label="Show"
        />
        <Box
            sx={{
              '& > :not(style)': {
                display: 'inline-block',
                justifyContent: 'space-around',
                // width, height,
              },
            }}
        >
        <Collapse in={checked} collapsedSize={40}>
          {contents}
          {/*
            <p>Width: {width}, Height: {height}</p>
            <div style={{border: '4px solid purple', display: 'inline-block'}}>
              {contents}
            </div>
          * /}
        </Collapse>
          {/*
          <div>
            <Collapse in={checked}>{icon}</Collapse>
            <Collapse in={checked} collapsedSize={40}>
              {icon}
            </Collapse>
          </div>
          <div>
            <Box sx={{ width: '50%' }}>
              <Collapse orientation="horizontal" in={checked}>
                {icon}
              </Collapse>
            </Box>
            <Box sx={{ width: '50%' }}>
              <Collapse orientation="horizontal" in={checked} collapsedSize={40}>
                {icon}
              </Collapse>
            </Box>
          </div>
          * /}
        </Box>
      </Box>
  );
}
function accordionPanels({panels=[]}) {
  console.log(panels);
  const out = panels.map((p,i) => {
    const {title, content, id=`panel${i}`} = p;
    return accordionPanel({id, title, content});
  })
  return (
      <div>{out}</div>
  );
}
function accordionPanel({id, title, content}) {
  const panel = (
      <Draggable key={id} defaultPosition={{x: 0, y: 0}} >
        <Accordion>
          <AccordionSummary
              expandIcon={<ExpandMoreIcon />}
              aria-controls={id + '-content'}
              id={id + '-header'}
          >
            <Typography>{title}</Typography>
          </AccordionSummary>
          <AccordionDetails>
            {content}
          </AccordionDetails>
        </Accordion>
      </Draggable>
  );
  return panel;
}
function SimpleAccordion() {
  // from https://mui.com/material-ui/react-accordion/
  return (
      <div>
        <Accordion>
          <AccordionSummary
              expandIcon={<ExpandMoreIcon />}
              aria-controls="panel1a-content"
              id="panel1a-header"
          >
            <Typography>Accordion 1</Typography>
          </AccordionSummary>
          <AccordionDetails>
            <Typography>
              Lorem ipsum dolor sit amet, consectetur adipiscing elit. Suspendisse
              malesuada lacus ex, sit amet blandit leo lobortis eget.
            </Typography>
          </AccordionDetails>
        </Accordion>
        <Accordion>
          <AccordionSummary
              expandIcon={<ExpandMoreIcon />}
              aria-controls="panel2a-content"
              id="panel2a-header"
          >
            <Typography>Accordion 2</Typography>
          </AccordionSummary>
          <AccordionDetails>
            <Typography>
              Lorem ipsum dolor sit amet, consectetur adipiscing elit. Suspendisse
              malesuada lacus ex, sit amet blandit leo lobortis eget.
            </Typography>
          </AccordionDetails>
        </Accordion>
        <Accordion disabled>
          <AccordionSummary
              expandIcon={<ExpandMoreIcon />}
              aria-controls="panel3a-content"
              id="panel3a-header"
          >
            <Typography>Disabled Accordion</Typography>
          </AccordionSummary>
        </Accordion>
      </div>
  );
}
// export {FlexibleContainer, accordionPanels, accordionPanel, SimpleAccordion};
 */
