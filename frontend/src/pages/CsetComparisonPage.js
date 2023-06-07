import React, {
  useRef,
  useState,
  useCallback,
  useEffect /* useMemo, useReducer, */,
} from "react";
import * as d3dag from "d3-dag";
// import { createSearchParams, useSearchParams, } from "react-router-dom";
import DataTable, { createTheme } from "react-data-table-component";
import { AddCircle, RemoveCircleOutline } from "@mui/icons-material";
import { Box, Slider, Button, Typography, Switch } from "@mui/material";
import Draggable from "react-draggable";
// import {Checkbox} from "@mui/material";
import { isEmpty, get, throttle, max } from "lodash"; // set, map, omit, pick, uniq, reduce, cloneDeepWith, isEqual, uniqWith, groupBy,
import {
  useStateSlice,
  hierarchyToFlatCids,
  makeHierarchyRows,
} from "../components/State";
import { fmt, useWindowSize } from "../components/utils";
import { setColDefDimensions } from "../components/dataTableUtils";
import { ConceptSetCard } from "../components/ConceptSetCard";
import { Tooltip } from "../components/Tooltip";
import {
  getEditCodesetFunc,
  getCodesetEditActionFunc,
  EditInfo,
  cellContents,
  cellStyle,
  Legend,
  saveChangesInstructions,
} from "../components/EditCset";
// import {EDGES} from '../components/ConceptGraph';
import { FlexibleContainer } from "../components/FlexibleContainer";
import _ from "../supergroup/supergroup";

// TODO: Find concepts w/ good overlap and save a good URL for that
// TODO: show table w/ hierarchical indent
// TODO: Color table: I guess would need to see if could pass extra values/props and see if table widget can use that
//  ...for coloration, since we want certain rows grouped together
function CsetComparisonPage(props) {
  const {
    all_csets = [],
    cset_data = {},
    searchParams,
    setSearchParams,
    editCodesetId,
    csetEditState,
  } = props;
  console.log("starting CsetComparisonPage");
  const { selected_csets = [], researchers, hierarchy, conceptLookup } = cset_data;
  const { state: hierarchySettings, dispatch} = useStateSlice("hierarchySettings");
  const hsDispatch = (...args) => {
    window.Pace.restart();
    setTimeout(() => dispatch(...args), 100);
  }
  // const [concepts, setConcepts] = useState([]);
  const windowSize = useWindowSize();
  const boxRef = useRef();
  const sizes = getSizes(/*squishTo*/ 1);
  const customStyles = styles(sizes);
  const {collapsed, nested, hideRxNormExtension, hideZeroCounts} = hierarchySettings;

  // console.log(EDGES);

  // TODO: component is rendering twice. why? not necessary? fix?
  let nestedData = getRowData({...props, hierarchySettings});
  let rowData;
  if (nested) {
    rowData = nestedData;
  } else {
    rowData = hierarchyToFlatCids(hierarchy).map(cid => conceptLookup[cid]);
  }

  const editAction = getCodesetEditActionFunc({
    searchParams,
    setSearchParams,
  });
  const editCodesetFunc = getEditCodesetFunc({ searchParams, setSearchParams });

  function toggleCollapse(row) {
    /* @amirmds:
      Since toggleCollapse is now using appState instead of local useState, this logic
      could be moved to the reducer and instead of passing this function and the collapsed
      state down to colConfig, colConfig could pick those out of appState itself.
     */
    let _collapsed = collapsed;
    _collapsed = {
      ..._collapsed,
      [row.pathToRoot]: !get(_collapsed, row.pathToRoot.join(",")),
    };
    hsDispatch({ type: "collapseDescendants", collapsed: _collapsed });
  }

  if (!all_csets.length || isEmpty(selected_csets)) {
    return <p>Downloading...</p>;
  }
  let columns = colConfig({
    ...props,
    selected_csets,
    editAction,
    editCodesetFunc,
    sizes,
    hierarchySettings, // collapsed, nested, hideZeroCounts, hideRxNormExtension
    hsDispatch,
    toggleCollapse,
    windowSize,
  });

  let infoPanels = [
    <Button key="distinct"
            disabled={!nested}
            onClick={() => hsDispatch({type:'nested', nested: false})}
            sx={{ marginRight: '4px' }}
    >
      {cset_data.concepts.length} distinct concepts
    </Button>,
    <Button key="nested"
            disabled={nested}
            onClick={() => hsDispatch({type:'nested', nested: true})}
            sx={{ marginRight: '4px' }}
    >
      {nestedData.length} in hierarchy
    </Button>,
    <FlexibleContainer key="legend" title="Legend">
      <Legend />
    </FlexibleContainer>
  ];
  if (editCodesetId) {
    infoPanels.push(
        <FlexibleContainer key="cset" title="Concept set being edited">
          <ConceptSetCard
              cset={columns.find((d) => d.codeset_id === editCodesetId).cset_col}
              researchers={researchers}
              editing={true}
          />
        </FlexibleContainer>
    );
    if (csetEditState && csetEditState[editCodesetId]) {
      const csidState = csetEditState[editCodesetId];
      infoPanels.push(
          <FlexibleContainer key="changes"
              title={`${Object.keys(csidState).length} Staged changes`}
          >
            <EditInfo {...props} />
          </FlexibleContainer>,

          <FlexibleContainer key="instructions" title="Instructions to save changes">
            {saveChangesInstructions(props)}
          </FlexibleContainer>
      );
    }
  }

  let moreProps = { ...props, rowData, columns, selected_csets, customStyles };
  console.log(hierarchySettings);
  return (
    <div>
      <Box
          ref={boxRef}
          sx={{
            width: "96%",
            margin: "9px",
            display: "flex",
            flexDirection: "row",
          }}
      >
        {infoPanels}
        <Typography
            variant="h5"
            sx={{ marginLeft: "auto" }}
        >
          Click on concept set column heading to edit
        </Typography>
      </Box>
      <ComparisonDataTable /*squishTo={squishTo}*/ {...moreProps} />
    </div>
  );
}

export function getRowData(props) {
  // when I put this provider up at the App level, it didn't update
  //    but at the CsetComparisonPage level it did. don't know why
  console.log("getting row data");
  const { cset_data, hierarchySettings } = props;
  const {collapsed, nested, hideZeroCounts, hideRxNormExtension} = hierarchySettings;
  const { edges = [], conceptLookup = {}, } = cset_data;

  /*
  const connect = d3dag.dagConnect();
  const dag = connect(edges);
  dag.depth();
  const nodes = dag.descendants('depth');
  let nodeLookup = {};
  for (let n of nodes) {
    nodeLookup[n.data.id] = 1;
  }
  const missingConcepts = concepts.filter(c => !nodeLookup[c.concept_id]);
   */

  const h = _.hierarchicalTableToTree(edges, 0, 1);
  const fakeRoot = h.asRootVal();
  const nodes = fakeRoot.descendants();

  let rows = nodes.map(n => {
    let row = {...conceptLookup[n.valueOf()]};
    row.level = n.value;
    row.hasChildren = n.children.length > 0;
    return row;
  })
  if (hideRxNormExtension) {
    rows = rows.filter(r => r.vocabulary_id !== 'RxNorm Extension');
  }
  if (hideZeroCounts) {
    rows = rows.filter(r => r.total_cnt > 0);
  }
  return rows;
}
function ComparisonDataTable(props) {
  const {
    columns,
    squishTo = 1,
    cset_data,
    csetEditState = {},
    customStyles,
    rowData,
  } = props;
  const boxRef = useRef();
  // console.log(derivedState);

  const conditionalRowStyles = [
    {
      when: () => true,
      style: (row) => ({
        backgroundColor: row.concept_id in csetEditState ? "#F662" : "#FFF",
      }),
    },
  ];
  console.log("drawing comparisondatatable");
  return (
    <DataTable
      customStyles={customStyles}
      conditionalRowStyles={conditionalRowStyles}
      className="comparison-data-table"
      theme="custom-theme" // theme="light"
      columns={columns}
      data={rowData}
      dense
      fixedHeader
      fixedHeaderScrollHeight={() => {
        // console.log(boxRef.current);
        const MuiAppBar = document.querySelector(".Mui-app-bar");
        let headerMenuHeight = 64;
        if (MuiAppBar) {
          headerMenuHeight = MuiAppBar.clientHeight;
        }
        const { offsetTop = 0, offsetHeight = 0 } = boxRef.current ?? {};
        return (
          window.innerHeight -
          (headerMenuHeight + offsetTop + offsetHeight) +
          "px"
        );
        // return "400px";
      }}
      /*
       */
      // highlightOnHover
      // responsive
      // subHeaderAlign="right"
      // subHeaderWrap
      //striped //pagination //selectableRowsComponent={Checkbox}
      //selectableRowsComponentProps={selectProps} //sortIcon={sortIcon}
      // expandOnRowClicked // expandableRows // {...props}
    />
  );
}
function getSizes(squishTo) {
  let sizes = {
    rowFontSize: 13 * squishTo + "px",
    // rowPadding:   ( 1 * squishTo) + 'px', // do these do anything?
    // rowPaddingTop:   ( 4 * squishTo) + 'px',
    // rowPaddingBottom:   ( 0 * squishTo) + 'px',
    collapseIcon: 13 * squishTo + "px",
    linkHeight: 20 * squishTo + "px",
    atlasHeight: 14 * squishTo + "px",
    athenaHeight: 12 * squishTo + "px",
  };
  return sizes;
}

function colConfig(props) {
  let {
    hierarchySettings,
    hsDispatch,
    selected_csets,
    cset_data,
    toggleCollapse,
    sizes,
    editAction,
    editCodesetFunc,
    windowSize,
  } = props;
  const {collapsed, nested, hideZeroCounts, hideRxNormExtension} = hierarchySettings;
  const {concepts} = cset_data;

  let coldefs = [
    {
      name: "Concept name",
      selector: (row) => row.concept_name,
      format: (row) => {
        let content = nested ? (
          row.hasChildren ? (
            collapsed[row.pathToRoot] ? (
              <span
                className="toggle-collapse concept-name-row"
                onClick={() => toggleCollapse(row)}
              >
                <AddCircle
                  sx={{
                    fontSize: sizes.collapseIcon,
                    display: "inline-flex",
                    marginRight: "0.15rem",
                    marginTop: "0.05rem",
                    verticalAlign: "top",
                  }}
                />
                {row.concept_name} {row.collapsed && "collapsed"}
              </span>
            ) : (
              <span
                className="toggle-collapse concept-name-row"
                onClick={() => toggleCollapse(row)}
              >
                <RemoveCircleOutline
                  sx={{
                    fontSize: sizes.collapseIcon,
                    display: "inline-flex",
                    marginRight: "0.15rem",
                    marginTop: "0.05rem",
                    verticalAlign: "top",
                  }}
                />
                {row.concept_name} {row.collapsed && "collapsed"}
              </span>
            )
          ) : (
            <span className="concept-name-row">
              <RemoveCircleOutline
                sx={{ fontSize: sizes.collapseIcon, visibility: "hidden" }}
              />
              {row.concept_name}
            </span>
          )
        ) : (
          row.concept_name
        );
        return content;
      },
      sortable: !nested,
      // minWidth: 100,
      // remainingPct: .60,
      // width: (window.innerWidth - selected_csets.length * 50) * .65,
      grow: 4,
      wrap: true,
      compact: true,
      conditionalCellStyles: [
        {
          when: (row) => true,
          style: (row) => ({ paddingLeft: 16 + row.level * 16 + "px" }),
        },
      ],
    },
    {
      // name: "Vocabulary",
      headerProps: {
        headerContent: (
            concepts.some(d => d.vocabulary_id === 'RxNorm Extension')
            ? <div style={{display: 'flex', flexDirection: 'column'}}>
                <div>Vocabulary</div>
                <Tooltip label="Toggle hiding of RxNorm Extension concepts">
                  <Switch sx={{margin: '-8px 0px'}} checked={!hideRxNormExtension}
                          onClick={() => hsDispatch({type:'hideRxNormExtension', hideRxNormExtension: !hideRxNormExtension})}
                  />
                </Tooltip>
              </div>
            : "Vocabulary"
        )
        // headerContentProps: { onClick: editCodesetFunc, codeset_id: cset_col.codeset_id, },
      },
      selector: (row) => row.vocabulary_id,
      // format: (row) => <Tooltip label={row.vocabulary_id} content={row.vocabulary_id} />,
      sortable: !nested,
      width: 100,
      style: { justifyContent: "center" },
    },
    {
      name: "Concept ID",
      selector: (row) => row.concept_id,
      sortable: !nested,
      width: 80,
      style: { justifyContent: "center" },
    },
    {
      name: "Links",
      selector: (row) => row.concept_id,
      headerProps: {
        tooltipContent: (
          <span>Click icons to open the concept in ATLAS or Athena</span>
        ),
      },
      // TODO: @fabiofdez: after widening this column so (i) icon would display, the cells should be centered. can you figure out how to do that?
      format: (row) => (
        <span
          style={{
            height: sizes.linkHeight,
            display: "flex",
            flex: 1,
            justifyContent: "space-between",
            alignItems: "center",
          }}
        >
          <a
            href={`https://atlas-demo.ohdsi.org/#/concept/${row.concept_id}`}
            target="_blank"
            rel="noreferrer"
            style={{
              display: "flex",
              aspectRatio: 1,
              alignItems: "center",
              padding: "3px",
            }}
          >
            <img
              height={sizes.atlasHeight}
              src="atlas.ico"
              alt="Link to this concept in ATLAS"
            />
          </a>
          &nbsp;
          <a
            href={`https://athena.ohdsi.org/search-terms/terms/${row.concept_id}`}
            target="_blank"
            rel="noreferrer"
            style={{
              display: "flex",
              aspectRatio: 1,
              alignItems: "center",
              padding: "3px",
            }}
          >
            <img
              height={sizes.athenaHeight}
              src="athena.ico"
              alt="Link to this concept in Athena"
            />
          </a>
        </span>
      ),
      sortable: !nested,
      width: 60,
      style: {
        backgroundColor: "lightgray",
        paddingRight: "0px",
        display: "flex",
        flex: 1,
        justifyContent: "center",
      },
    },
    // ...cset_cols,
    {
      // name: "Patients",
      headerProps: {
        headerContent: (
            <div style={{display: 'flex', flexDirection: 'column'}}>
              <Tooltip label="Approximate distinct person count. Small counts rounded up to 20."><div>Patients</div></Tooltip>
              <Tooltip label="Toggle hiding of concepts with 0 patients">
                <Switch sx={{margin: '-8px 0px'}} checked={!hideZeroCounts}
                  onClick={() => hsDispatch({type:'hideZeroCounts', hideZeroCounts: !hideZeroCounts})}
                />
              </Tooltip>
            </div>
        )
        // headerContentProps: { onClick: editCodesetFunc, codeset_id: cset_col.codeset_id, },
      },
      selector: (row) => {
        // can be comma=separated list if pt cnts in more than one domain
        const cnts = row.distinct_person_cnt.split(',').map(n => parseInt(n));
        return max(cnts);
      },
      format: (row) => {
        const cnts = row.distinct_person_cnt.split(',').map(n => parseInt(n));
        return fmt(max(cnts));
      },
      sortable: !nested,
      right: true,
      width: 80,
      // minWidth: 80,
      // remainingPct: .10,
      style: { justifyContent: "center" },
    },
    {
      name: "Records",
      headerProps: {
        tooltipContent: "Record count. Small counts rounded up to 20.",
      },
      /* name:   <Tooltip label="Record count. Small counts rounded up to 20.">
                <span>Records</span>
            </Tooltip>, */
      selector: (row) => row.total_cnt,
      format: (row) => {
        return fmt(row.total_cnt)
      },
      sortable: !nested,
      right: true,
      width: 80,
      // minWidth: 80,
      // remainingPct: .10,
      style: { justifyContent: "center" },
    },
  ];
  let cset_cols = selected_csets.map((cset_col) => {
    const { codeset_id } = cset_col;
    let def = {
      cset_col,
      codeset_id,
      headerProps: {
        //tooltipContent: "Click to create and edit new draft of this concept set",
        tooltipContent: `${cset_col.concept_set_version_title}. Click to edit new version.`,
        headerContent: cset_col.concept_set_name,
        headerContentProps: {
          onClick: editCodesetFunc,
          codeset_id: cset_col.codeset_id,
        },
      },
      selector: (row) => {
        return cellContents({
          ...props,
          row,
          cset_col,
          editAction,
        });
      },
      conditionalCellStyles: [
        {
          when: (row) => true, //csmiLookup[codeset_id][row.concept_id],
          // when: row => row.checkboxes && row.checkboxes[codeset_id],
          style: (row) => cellStyle({ ...props, cset_col, row }),
        },
      ],
      sortable: !nested,
      // compact: true,
      width: 70,
      // center: true,
    };
    return def;
  });
  coldefs = [...coldefs, ...cset_cols];
  // coldefs.forEach(d => {delete d.width; d.flexGrow=1;})
  // coldefs[0].grow = 5;
  // delete coldefs[0].width;
  coldefs = setColDefDimensions({ coldefs, windowSize });
  // console.log(coldefs);
  /*
  if (!nested) {
    delete coldefs[0].conditionalCellStyles;
  }
   */
  return coldefs;
}

// createTheme creates a new theme named solarized that overrides the build in dark theme
// https://github.com/jbetancur/react-data-table-component/blob/master/src/DataTable/themes.ts
createTheme(
  "custom-theme",
  {
    text: {
      primary: "#268bd2",
      secondary: "#2aa198",
    },
    context: {
      background: "#cb4b16",
      text: "#FFFFFF",
    },
  },
  "light"
);

function styles(sizes) {
  return {
    /*
        	tableWrapper: {
            style: {
              display: 'table',
            },
          },
        denseStyle: {
            minHeight: '2px',
        },
        */
    table: {
      style: {
        // maxWidth: '85%',
        // marginLeft: '20px',
        // maxWidth: '400px', doesn't work ?
      },
    },
    headCells: {
      style: {
        // transform: 'translate(10px,-15px) rotate(-45deg)',
        // transform: 'translate(0px,30px)',
        // height: '100%',
        // position: 'absolute',
        fontSize: "120%",
        overflow: "visible",
        // verticalAlign: 'bottom !important', // doesn't work
        marginTop: "auto",
        /*
                zIndex: 200,
                webkitAlignItems: 'end !important',
                alignItems: 'end !important',
                alignItemsFlexStart: 'end !important',
                display: 'inline !important',
                // textAlign: 'left',
                 */
        // setting height in .rdt_TableHeadRow works, but setting height here
        //  makes the header content align vertically in the center which is terrible
        // height: '180px',        // TODO: FIX!!!!
        padding: 0,
        // border: '3px solid green',
        // paddingLeft: '8px', // override the cell padding for head cells
        // paddingRight: '8px',
      },
    },
    rows: {
      style: {
        color: "black",
        minHeight: "0px", // override the row height    -- doesn't work, can only seem to do it from css
        padding: sizes.rowPadding,
        fontSize: sizes.rowFontSize,
        // height: '2px',
        // fontSize: '2px',
        // height: '3px',
        borderBottom: "1px solid #BBB",
      },
    },
    cells: {
      style: {
        minHeight: "0px", // override the row height
        // paddingLeft: '8px', // override the cell padding for data cells
        // paddingRight: '8px',
        padding: 0, //'0px 5px 0px 5px',
        borderRight: "1px solid #BBB",
      },
    },
  };
}
// const expandIcon    = <svg fill="currentColor" height="20" viewBox="0 -6 24 24" width="24" xmlns="http://www.w3.org/2000/svg"><path d="M8.59 16.34l4.58-4.59-4.58-4.59L10 5.75l6 6-6 6z"></path><path d="M0-.25h24v24H0z" fill="none"></path></svg>
// const collapseIcon  = <svg fill="currentColor" height="20" viewBox="0 -6 24 24" width="24" xmlns="http://www.w3.org/2000/svg"><path d="M7.41 7.84L12 12.42l4.59-4.58L18 9.25l-6 6-6-6z"></path><path d="M0-.75h24v24H0z" fill="none"></path></svg>
// const blankIcon     = <svg fill="currentColor" height="20" viewBox="0 -6 24 24" width="24" xmlns="http://www.w3.org/2000/svg" />
function SquishStuff() {
  // not using right now. wasn't fully working
  const [squishTo, setSquishTo] = useState(1);
  const tsquish = throttle((val) => {
    // console.log(`squish: ${squishTo} -> ${val}`);
    setSquishTo(val);
  }, 200);
  const squishChange = useCallback(tsquish, [squishTo, tsquish]);
}
function SquishSlider({ setSquish }) {
  // not refreshing... work on later
  function preventHorizontalKeyboardNavigation(event) {
    if (event.key === "ArrowLeft" || event.key === "ArrowRight") {
      event.preventDefault();
    }
  }
  function onChange(e, val) {
    // console.log('val: ', val);
    setSquish(val);
  }

  return (
    <Box /* sx={{ height: 300 }} */>
      <Slider
        // key={`slider-${squish}`}
        sx={{
          width: "60%",
          marginLeft: "15%",
          marginTop: "15px",
          // '& input[type="range"]': { WebkitAppearance: 'slider-vertical', },
        }}
        onChange={onChange}
        // onChangeCommitted={onChange}
        // orientation="vertical"
        min={0.01}
        max={2}
        step={0.1}
        // value={squish}
        defaultValue={1}
        aria-label="Squish factor"
        valueLabelDisplay="auto"
        onKeyDown={preventHorizontalKeyboardNavigation}
      />
    </Box>
  );
}

export { CsetComparisonPage };
