import React, {useState, useEffect, useMemo, /* useReducer, useRef, */} from 'react';
import DataTable, { createTheme } from 'react-data-table-component';
import AddCircle from '@mui/icons-material/AddCircle';
import RemoveCircle from '@mui/icons-material/RemoveCircle';
import {Checkbox} from "@mui/material";
import Box from '@mui/material/Box';
import Typography from '@mui/material/Typography';
import {get, isEmpty, set, map, omit, pick, uniq, reduce, cloneDeepWith, isEqual, uniqWith, groupBy, } from 'lodash';
import {fmt} from './utils';
import {ConceptSetCard} from "./ConceptSetCard";
import {Tooltip} from './Tooltip';
// import {isEmpty} from "react-data-table-component/dist/src/DataTable/util"; // what was this for?
// import Button from '@mui/material/Button';

/*
 */

function EditInfo(props) {
    const {editInfo={}, concepts_map} = props;
    return (
        <Box sx={{ p: 2, border: '1px dashed grey' }}>
            {Object.entries(editInfo).map(
                ([concept_id, state]) => {
                    return (
                        <Typography key={concept_id} >
                            { state ? 'Adding' : 'Removing' } {concepts_map[concept_id].concept_name}
                        </Typography>
                    )
                }
            )}
        </Box>
    );
}
function ComparisonDataTable(props) {
    const {codeset_ids=[], nested=true, makeRowData, rowData, selected_csets, squishTo, cset_data} = props;
    const {researchers, concepts_map} = cset_data;
    const [columns, setColumns] = useState();
    const [collapsed, setCollapsed] = useState({});
    const [editCol, setEditCol] = useState(null);
    const [editInfo, setEditInfo] = useState({});
    // console.log(window.data = props);

    function editAction(props) {
        const {codeset_id, concept_id, state} = props;
        setEditInfo(prev => {
            let ei = {...prev};
            if (concept_id in ei) {
                delete ei[concept_id];
            } else {
                ei[concept_id] = state;
            }
            return ei;
        });
    }
    function toggleCollapse(row) {
        collapsed[row.pathToRoot] = !get(collapsed, row.pathToRoot.join(','));
        setCollapsed({...collapsed});
        makeRowData(collapsed);
    }

    useEffect(() => {
        if (!selected_csets.length) {
            return;
        }
        makeRowData({});
    }, [selected_csets.length, ]);

    let sizes = {
        rowFontSize:  (13 * squishTo) + 'px',
        rowPadding:   ( 2 * squishTo) + 'px',
        collapseIcon: (13 * squishTo) + 'px',
        linkHeight:   (20 * squishTo) + 'px',
        atlasHeight:  (12 * squishTo) + 'px',
        athenaHeight: (10 * squishTo) + 'px',
    }
    function setupEditCol(evt) {
        let ec = parseInt(evt.target.getAttribute('colnum'));
        if (editCol == ec) {
            setEditCol(null);
        } else {
            setEditCol(ec);
        }
        console.log(`set editcol to ${ec}`)
    }
    useEffect(() => {
        // console.log('setColumns because', {rowData});
        if (isEmpty(rowData)) {
            return;
        }
        setColumns(colConfig({
                                 codeset_ids, nested, selected_csets,
                                 rowData, collapsed, toggleCollapse, sizes,
                                 editCol, editInfo, setupEditCol, editAction,
                             }));
    }, [rowData, squishTo, editCol, editInfo]);

    let card, eInfo;
    if (typeof(editCol) == "number") {
        card = <ConceptSetCard cset={columns[editCol].cset_col}
                               researchers={researchers}
                               editing={true}
                               width={window.innerWidth * 0.5}
                    />;
    }
    // console.log({editInfo});
    if (! isEmpty(editInfo)) {
        eInfo = <EditInfo editInfo={editInfo} concepts_map={concepts_map}/>;
    }
    const customStyles = styles(sizes);
    const conditionalRowStyles = [
        {
            when: () => true,
            style: row => ({
                backgroundColor: row.concept_id in editInfo ? '#F662' : '#FFF',
            }),
        },
    ]
    return (
        /* https://react-data-table-component.netlify.app/ */
        <div>
            <div style={{ display: 'flex', flexWrap: 'wrap',
                            flexDirection: 'row', margin: '20px', }}>
                { card } {eInfo}
            </div>
            <DataTable
                customStyles={customStyles}
                conditionalRowStyles={conditionalRowStyles}
                className="comparison-data-table"
                theme="custom-theme"
                // theme="light"
                columns={columns}
                data={rowData}

                dense
                fixedHeader
                fixedHeaderScrollHeight={(window.innerHeight - 275) + 'px'}
                highlightOnHover
                responsive
                //striped
                subHeaderAlign="right"
                subHeaderWrap
                //pagination
                //selectableRowsComponent={Checkbox}
                //selectableRowsComponentProps={selectProps}
                //sortIcon={sortIcon}
                // expandOnRowClicked
                // expandableRows
                // {...props}
            />
        </div>
    );
}
/*
function getCbStates(csets, nodups) {
    let grid = {};
    csets.forEach(cset => {
        let cbRow = {};
        nodups.forEach(row => {
            cbRow[row.concept_id] = row.codeset_ids.includes(cset.codeset_id);
        })
        grid[cset.codeset_id] = cbRow;
    })
    return grid
}
*/
function colConfig(props) {
    let { codeset_ids, nested, selected_csets, rowData,
          collapsed, toggleCollapse, sizes, editCol, editInfo, setupEditCol,
          editAction, } = props;
    // console.log('setting coldefs');
    let checkboxChange = (codeset_id, concept_id) => (evt, state) => {
        console.log({codeset_id, concept_id, state});
        editAction({codeset_id, concept_id, state});
        /* let url = backend_url(`modify-cset?codeset_id=${codeset_id}&concept_id=${concept_id}&state=${state}`); */
    }

    let coldefs = [
        {
            name: 'Concept name',
            selector: row => row.concept_name,
            format: (row, idx) => {
                if (!row.checkboxes) {
                    console.log('problem!!!!', {idx, row, rowData})
                } // else { // console.log('not a problem', {idx, row, rowData}) }
                let content = nested
                    ? row.has_children
                        ? collapsed[row.pathToRoot]
                            ? <span className="toggle-collapse" onClick={() => toggleCollapse(row)}><AddCircle sx={{fontSize:sizes.collapseIcon}}/> {row.concept_name} {row.collapsed && 'collapsed'}</span>
                            : <span className="toggle-collapse" onClick={() => toggleCollapse(row)}><RemoveCircle sx={{fontSize:sizes.collapseIcon}}/> {row.concept_name} {row.collapsed && 'collapsed'}</span>
                        : <span><RemoveCircle sx={{fontSize:sizes.collapseIcon, visibility:'hidden'}}/> {row.concept_name}</span>
                    : row.concept_name
                return content;
            },
            sortable: !nested,
            width: (window.innerWidth - selected_csets.length * 50) * .85,
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
            width: '80px',
            style: { paddingRight: '8px', },
        },
        {
            name: 'Concept links',
            selector: row => row.concept_id,
            format: row => (
                <span style={{backgroundColor: 'lightgray', height: sizes.linkHeight}} >
                    <a href={`https://atlas-demo.ohdsi.org/#/concept/${row.concept_id}`} target="_blank">
                        <img height={sizes.atlasHeight} src="atlas.ico" />
                    </a>&nbsp;
                    <a href={`https://athena.ohdsi.org/search-terms/terms/${row.concept_id}`} target="_blank"
                    >
                        <img height={sizes.athenaHeight} src="athena.ico" />
                    </a>
                </span>),
            sortable: !nested,
            width: '29px',
            style: { paddingRight: '0px', },
        },
        {
            name: 'Patients',
            selector: row => parseInt(row.distinct_person_cnt),
            format: row => fmt(row.distinct_person_cnt),
            sortable: !nested,
            right: true,
            width: '80px',
            style: { paddingRight: '8px', },
        },
        {
            name: 'Records',
            selector: row => row.total_cnt,
            format: row => fmt(row.total_cnt),
            sortable: !nested,
            right: true,
            width: '80px',
            style: { paddingRight: '8px', },
        },
    ];
    let cset_cols = selected_csets.map((cset_col, col_idx) => {
        const colnum = col_idx + coldefs.length;
        let def = {
            cset_col,
            name: <span className="cset-column"
                        onClick={setupEditCol}
                        colnum={colnum} >{cset_col.concept_set_version_title}</span>,
            //  name:   <Tooltip label="Click to edit." placement="bottom">
            //              <span>{cset_col.concept_set_version_title}</span>
            //          </Tooltip>,
            selector: (row,idx) => {
                return <CellCheckbox {...{row,idx, colnum, cset_col, rowData, editInfo, editCol, checkboxChange}} />;
            },
            conditionalCellStyles: [
                { when: row => row.checkboxes && row.checkboxes[cset_col.codeset_id],
                    style: row => {
                        let cb = row.checkboxes[cset_col.codeset_id];
                        let bg = 'purple';
                        if      (cb.csm && cb.item) { bg = 'orange' }
                        else if (cb.csm)             { bg = 'pink' }
                        else if (cb.item)            { bg = 'gray' }
                        return { backgroundColor: bg, };
                    }
                },
            ],
            sortable: !nested,
            compact: true,
            width: '30px',
            // maxWidth: 50,
            center: true,
        }
        return def;
    });
    coldefs = [...coldefs, ...cset_cols];
    if (!nested) {
        delete coldefs[0].conditionalCellStyles;
    }
    return coldefs;
    // console.log('done setting coldefs');

}
function CellCheckbox(props) {
    const {row, idx, colnum, cset_col, rowData, editInfo, editCol, checkboxChange} = props;
    if (!row.checkboxes) {
        console.log('problem!!!!', {idx, row, rowData})
    }
    let checked, contents;
    let checkboxValue = row.checkboxes[cset_col.codeset_id];
    checked = !! checkboxValue;

    if (typeof(editCol) == "number" && colnum == editCol) {
        if (row.concept_id in editInfo) {
            checked = ! checked;
        }
        contents = <Checkbox checked={checked} onChange={checkboxChange(cset_col.codeset_id, row.concept_id)}/>
    } else {
        contents = <span>{checked ? '\u2713' : ''}</span>;
    }
    if (checkboxValue) {
        return  <Tooltip label={<pre>{JSON.stringify(checkboxValue, null, 2)}</pre>} placement="bottom">{contents}</Tooltip>
    } else {
        return contents
    }
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
                maxWidth: '85%',
                marginLeft: '20px',
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
                verticalAlign: 'bottom', // doesn't work
                marginTop: 'auto',
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
export {ComparisonDataTable};


/*
from https://react-data-table-component.netlify.app/?path=/docs/getting-started-kitchen-sink--kitchen-sink
<KitchenSinkStory
  dense
  direction="auto"
  fixedHeader
  fixedHeaderScrollHeight="300px"
  highlightOnHover
  responsive
  striped
  subHeaderAlign="right"
  subHeaderWrap
/>
 */