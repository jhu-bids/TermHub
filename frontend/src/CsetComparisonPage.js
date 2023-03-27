import React, {useRef, useState, useCallback, useEffect, /* useMemo, useReducer, */} from 'react';
// import { createSearchParams, useSearchParams, } from "react-router-dom";
import DataTable, { createTheme } from 'react-data-table-component';
import { AddCircle, RemoveCircleOutline, Add, } from '@mui/icons-material';
import Box from '@mui/material/Box';
import Slider from '@mui/material/Slider';
import Button from '@mui/material/Button';
import Draggable from 'react-draggable';
// import {Checkbox} from "@mui/material";
import {isEmpty, get, throttle, pullAt } from 'lodash'; // set, map, omit, pick, uniq, reduce, cloneDeepWith, isEqual, uniqWith, groupBy,
import {useAppState, DerivedStateProvider, useDerivedState, } from "./State";
import {fmt, useWindowSize, } from "./utils";
import {setColDefDimensions, } from "./dataTableUtils";
import {ConceptSetCard} from "./ConceptSetCard";
import {Tooltip} from './Tooltip';
import { getEditCodesetFunc, getCodesetEditActionFunc, EditInfo,
    cellContents, cellStyle, } from './EditCset';
// import FlexibleContainer, { accordionPanels, accordionPanel, } from "./FlexibleContainer";
import {ContentItems} from "./FlexibleContainer";
// import AllowOverlap from "./gridLayout";
import {DOCS, howToSaveStagedChanges} from "./AboutPage";
// import {isEmpty} from "react-data-table-component/dist/src/DataTable/util"; // what was this for?
// import Button from '@mui/material/Button';

// TODO: Find concepts w/ good overlap and save a good URL for that
// TODO: show table w/ hierarchical indent
// TODO: Color table: I guess would need to see if could pass extra values/props and see if table widget can use that
//  ...for coloration, since we want certain rows grouped together
function CsetComparisonPage(props) {
    const {all_csets=[], cset_data={}, searchParams, setSearchParams, } = props;
    const {hierarchy={}, selected_csets=[], concepts=[], cset_members_items=[], } = cset_data;
    const [collapsed, setCollapsed] = useState({});
    const windowSize = useWindowSize();
    const sizes = getSizes(/*squishTo*/ 1);
    const customStyles = styles(sizes);

    const editAction = getCodesetEditActionFunc({searchParams, setSearchParams});
    const editCodesetFunc = getEditCodesetFunc({searchParams, setSearchParams});

    function toggleCollapse(row) {
        let _collapsed = {...collapsed, [row.pathToRoot]: !get(collapsed, row.pathToRoot.join(','))};
        setCollapsed(_collapsed);
    }

    if (!all_csets.length || isEmpty(selected_csets)) {
        return <p>Downloading...</p>
    }
    let columns = colConfig({...props, selected_csets, editAction, editCodesetFunc, sizes, /* displayObj: _displayObj, */
        collapsed, toggleCollapse, nested: true, windowSize, });

    let moreProps = {...props, columns, selected_csets, customStyles, };
    return (
        <div>
            <DerivedStateProvider {...props}>
                <ControlsAndInfo {...moreProps} />
                <ComparisonDataTable /*squishTo={squishTo}*/ {...moreProps}  />
            </DerivedStateProvider>
        </div>)
}

/*{
    Object.entries(displayOptions).map(([name, opt]) =>
                                           <Button key={name} variant={name === displayOption ? "contained" : "outlined" } onClick={()=>changeDisplayOption(name)}>
                                               {opt.msg}
                                           </Button>)
}*/
function ControlsAndInfo(props) {
    const { cset_data, columns,
        editCodesetId, csetEditState={}, searchParams, setSearchParams,
            children, } = props;
    // const {hierarchy={}, selected_csets=[], concepts=[], cset_members_items=[], researchers, } = cset_data;
    const appState = useAppState();
    // const derivedState = useDerivedState();
    // <pre>{JSON.stringify({derivedState}, null, 2)}</pre>

    // const [displayOptions, setDisplayOptions] = useState({});
    // const [displayOption, setDisplayOption] = useState('fullHierarchy');
    // const [displayObj, setDisplayObj] = useState(); // useComparisonTableRowData({});
    // const [collapsed, setCollapsed] = useState({});
    const boxRef = useRef();

    // useEffect(() => contentItemsState.dispatch({type: 'contentItems-show', name: 'dummy'}));
    console.log(appState.getState());

    // return <h4>Next step: context providers; then this component reads from QSState</h4>
    /*
    function changeDisplayOption(option) {
        setDisplayOption(option);
    }
     */
    const moreProps = {...props, /* displayObj, */ columns};

    /*
    const _displayObj = _displayOptions[displayOption];
    setDisplayOptions(_displayOptions);
    setDisplayObj(_displayObj);
    setColumns(_columns);
    // console.log({displayOption, displayOptions, displayObj, columns});
    const moreProps = {...props, displayObj, columns};

    let card, eInfo;
    if (editCodesetId && columns) {
      card = (
          <FlexibleContainer
              title="Concept set being edited"
              ComponentType={ConceptSetCard}
              componentProps={{
                cset: columns.find(d => d.codeset_id === editCodesetId).cset_col,
                researchers: researchers,
                editing: true
              }}

          >
          </FlexibleContainer>
      );
      const cardContentItem = {
        name: 'editingCsetCard',
        show: true,
        content: card,
      }
     */
    // contentItemsState.dispatch({type: 'contentItems-new', payload: cardContentItem});
    /*
    card = <ConceptSetCard cset={columns.find(d=>d.codeset_id===editCodesetId).cset_col}
                           researchers={researchers}
                           editing={true}
                           // width={window.innerWidth * 0.5}
                />;
  }
  if (! isEmpty(csetEditState)) {
    eInfo = <EditInfo {...props} />;
  }
     */
    /*
    const panelProps = [
        {id: 'card-panel', title: 'Concept set being edited', content: card},
        {id: 'changes-panel', title: 'Staged changes', content: eInfo},
        {id: 'instructions-panel', title: 'How to save changes', content: howToSaveStagedChanges({})},
    ];
    // const panels = accordionPanels({panels});
    // console.log(panels);
     */

    return (
        <div>
            [<ContentItems />]
            <pre>{JSON.stringify(appState.getState(), null, 2)}</pre>
            {/*
            {card}
            */}
            {/*<AllowOverlap />*/}
            <Box ref={boxRef} sx={{ width: '96%', margin: '9px', display: 'flex', flexDirection: 'row', }}>
                {/*
            {eInfo}
            <Draggable defaultPosition={{x: 0, y: 0}} >
                <div style={{padding:30, height: 70, border: '1px solid blue', cursor: 'move'}}>
                    hello
                </div>
            </Draggable>
            */}
                {/*{panels}*/}
                {/*<Box>*/}
                {/*    <HelpButton doc="legend"/>*/}
                {/*</Box>*/}
            </Box>
            {/*{children}*/}
            {/* <StatsMessage {...props} /> */}
            {/*<SquishSlider setSquish={squishChange}/>*/}
        </div>

    )
}

function ComparisonDataTable(props) {
    const {columns, squishTo=1, cset_data, csetEditState={}, customStyles, } = props;
    const derivedState = useDerivedState();
    console.log(derivedState);
    let rowData;
    if (derivedState) {
        rowData = derivedState.comparisonRowData;
    }

    const conditionalRowStyles = [
        {
            when: () => true,
            style: row => ({
                backgroundColor: row.concept_id in csetEditState ? '#F662' : '#FFF',
            }),
        },
    ]
    return (
        <DataTable
            customStyles={customStyles}
            conditionalRowStyles={conditionalRowStyles}
            className="comparison-data-table"
            theme="custom-theme" // theme="light"
            columns={columns}
            // data={displayObj.rowData}
            data={rowData}
            dense
            /*
            fixedHeader
            fixedHeaderScrollHeight={() => {
                // console.log(boxRef.current);
                const headerStuffHeight = 50; // maybe get a real number, but too hard for now
                const {offsetTop=0, offsetHeight=0} = boxRef.current ?? {};
                return (window.innerHeight - (headerStuffHeight +
                            offsetTop + offsetHeight)) + 'px';
                // return "400px";
            }}
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
        rowFontSize:  (13 * squishTo) + 'px',
        // rowPadding:   ( 1 * squishTo) + 'px', // do these do anything?
        // rowPaddingTop:   ( 4 * squishTo) + 'px',
        // rowPaddingBottom:   ( 0 * squishTo) + 'px',
        collapseIcon: (13 * squishTo) + 'px',
        linkHeight:   (20 * squishTo) + 'px',
        atlasHeight:  (12 * squishTo) + 'px',
        athenaHeight: (10 * squishTo) + 'px',
    }
    return sizes;
}

function colConfig(props) {
    let { /* displayObj, */ nested, selected_csets, cset_data, collapsed, toggleCollapse, sizes,
          editAction, editCodesetFunc, windowSize, } = props;
    const { csmiLookup, } = cset_data;

    /*
    if (!displayObj) {
        return;
    }
     */

    let coldefs = [
        {
            name: 'Concept name',
            selector: row => row.concept_name,
            format: (row, ) => {
                let content = nested
                    ? row.has_children
                        ? collapsed[row.pathToRoot]
                            ? <span className="toggle-collapse" onClick={() => toggleCollapse(row)}><AddCircle sx={{fontSize:sizes.collapseIcon}}/> {row.concept_name} {row.collapsed && 'collapsed'}</span>
                            : <span className="toggle-collapse" onClick={() => toggleCollapse(row)}><RemoveCircleOutline sx={{fontSize:sizes.collapseIcon}}/> {row.concept_name} {row.collapsed && 'collapsed'}</span>
                        : <span><RemoveCircleOutline sx={{fontSize:sizes.collapseIcon, visibility:'hidden'}}/> {row.concept_name}</span>
                    : row.concept_name
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
                { when: row => true,
                    style: row => ({paddingLeft: 16 + row.level * 16 + 'px'})
                }
            ],
        },
        {
            name: 'Concept ID',
            selector: row => row.concept_id,
            sortable: !nested,
            width: 80,
            style: { paddingRight: '8px', },
        },
        {
            name: 'Links',
            selector: row => row.concept_id,
            headerProps: {
                tooltipContent: <span>Click icons to open the concept in ATLAS or Athena</span>,
            },
            format: row => (
                <span style={{backgroundColor: 'lightgray', height: sizes.linkHeight}} >
                    <a href={`https://atlas-demo.ohdsi.org/#/concept/${row.concept_id}`} target="_blank" rel="noreferrer">
                        <img height={sizes.atlasHeight} src="atlas.ico" alt="Link to this concept in ATLAS"/>
                    </a>&nbsp;
                    <a href={`https://athena.ohdsi.org/search-terms/terms/${row.concept_id}`} target="_blank" rel="noreferrer">
                        <img height={sizes.athenaHeight} src="athena.ico" alt="Link to this concept in Athena"/>
                    </a>
                </span>),
            sortable: !nested,
            width: 35,
            style: { paddingRight: '0px', },
        },
        // ...cset_cols,
        {
            name: 'Patients',
            headerProps: {
                tooltipContent: "Approximate distinct person count. Small counts rounded up to 20.",
            },
            selector: row => parseInt(row.distinct_person_cnt),
            format: row => fmt(row.distinct_person_cnt),
            sortable: !nested,
            right: true,
            width: 80,
            // minWidth: 80,
            // remainingPct: .10,
            style: { paddingRight: '8px', },
        },
        {
            name: 'Records',
            headerProps: {
                tooltipContent: "Record count. Small counts rounded up to 20.",
            },
            /* name:   <Tooltip label="Record count. Small counts rounded up to 20.">
                <span>Records</span>
            </Tooltip>, */
            selector: row => row.total_cnt,
            format: row => fmt(row.total_cnt),
            sortable: !nested,
            right: true,
            width: 80,
            // minWidth: 80,
            // remainingPct: .10,
            style: { paddingRight: '8px', },
        },
    ];
    let cset_cols = selected_csets.map((cset_col) => {
        const {codeset_id} = cset_col;
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
                }
            },
            selector: (row) => {
                /*return <CellContents { ...props}
                                     {...{row, cset_col,
                                         rowData: displayObj.rowData,
                                         editAction}} />; */
                return cellContents({ ...props, row, cset_col,
                                        // rowData: displayObj.rowData, // DON'T NEED THIS ANYMORE, RIGHT?
                                        editAction});
            },
            conditionalCellStyles: [
                {
                    when: row => true, //csmiLookup[codeset_id][row.concept_id],
                    // when: row => row.checkboxes && row.checkboxes[codeset_id],
                    style: row => cellStyle({...props, cset_col, row, }),
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
    coldefs = setColDefDimensions({coldefs, windowSize});
    // console.log(coldefs);
    if (!nested) {
        delete coldefs[0].conditionalCellStyles;
    }
    return coldefs;
}

// createTheme creates a new theme named solarized that overrides the build in dark theme
// https://github.com/jbetancur/react-data-table-component/blob/master/src/DataTable/themes.ts
createTheme('custom-theme', {
    text: {
        primary: '#268bd2',
        secondary: '#2aa198',
    },
    context: {
        background: '#cb4b16',
        text: '#FFFFFF',
    },
}, 'light');

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
            }
        },
        headCells: {
            style: {
                // transform: 'translate(10px,-15px) rotate(-45deg)',
                // transform: 'translate(0px,30px)',
                // height: '100%',
                // position: 'absolute',
                fontSize: '120%',
                overflow: 'visible',
                // verticalAlign: 'bottom !important', // doesn't work
                marginTop: 'auto',
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
                color: 'black',
                minHeight: '0px', // override the row height    -- doesn't work, can only seem to do it from css
                padding: sizes.rowPadding,
                fontSize: sizes.rowFontSize,
                // height: '2px',
                // fontSize: '2px',
                // height: '3px',
                borderLeft: '0.5px solid #BBB',
            },
        },
        cells: {
            style: {
                minHeight: '0px', // override the row height
                // paddingLeft: '8px', // override the cell padding for data cells
                // paddingRight: '8px',
                padding: 0, //'0px 5px 0px 5px',
                borderRight: '0.5px solid #BBB',
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
    const tsquish = throttle(
        val => {
            // console.log(`squish: ${squishTo} -> ${val}`);
            setSquishTo(val);
        }, 200);
    const squishChange = useCallback(tsquish, [squishTo, tsquish]);
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
        <Box /* sx={{ height: 300 }} */>
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

export {CsetComparisonPage};