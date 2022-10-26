import React, {useState, useEffect, useMemo, /* useReducer, useRef, */} from 'react';
import DataTable, { createTheme } from 'react-data-table-component';
import AddCircle from '@mui/icons-material/AddCircle';
import RemoveCircle from '@mui/icons-material/RemoveCircle';
import {get, map, omit, pick, uniq, reduce, cloneDeepWith, isEqual, uniqWith, groupBy, } from 'lodash';
// import Checkbox from '@mui/material/Checkbox';
// import {createSearchParams} from "react-router-dom";
// import Button from "@mui/material/Button";
// import axios from "axios";
// import {backend_url} from "./App";

function ComparisonDataTable(props) {
    const {codeset_ids=[], nested=true, makeRowData, rowData, selected_csets, } = props;
    const [columns, setColumns] = useState();
    const [collapsed, setCollapsed] = useState({});
    console.log(window.data = props);

    function toggleCollapse(row) {
        collapsed[row.path] = !get(collapsed, row.path);
        setCollapsed({...collapsed});
        makeRowData(collapsed);
    }

    useEffect(() => {
        if (!selected_csets.length) {
            return;
        }
        console.log('makeRowData because', {selected_csets});
        makeRowData({});
    }, [selected_csets.length, ]);
    useEffect(() => {
        console.log('selColumns because', {rowData});
        setColumns(colConfig(codeset_ids, nested, selected_csets, rowData, collapsed, toggleCollapse, ));
    }, [rowData, ]);

    const customStyles = styles();
    return (
        /* https://react-data-table-component.netlify.app/ */
        <DataTable
            className="comparison-data-table"
            theme="custom-theme"
            // theme="light"
            columns={columns}
            data={rowData}
            customStyles={customStyles}

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
function colConfig(codeset_ids, nested, selected_csets, rowData, collapsed, toggleCollapse, ) {
    console.log('setting coldefs');
    /*
    let checkboxChange = (codeset_id, concept_id) => (evt, state) => {
        console.log({codeset_id, concept_id, state});
        let url = backend_url(`modify-cset?codeset_id=${codeset_id}&concept_id=${concept_id}&state=${state}`);
        axios.get(url).then((res) => {
            console.log({url, res});
            return res.data
        })
    }
    */
    let cset_cols = selected_csets.map((cset_col, col_idx) => {
        let def = {
            name: cset_col.concept_set_version_title,
            selector: (row,idx) => {
                if (!row.checkboxes) {
                    console.log('problem!!!!', {idx, row, rowData})
                }
                let checked = row.checkboxes[cset_col.codeset_id];
                return checked ? '\u2713' : '';
                /*
                let checkbox_id = `${cset_col.codeset_id}:${row.concept_id}`;
                return <Checkbox checked={checked}
                                 onChange={checkboxChange(cset_col.codeset_id, row.concept_id)}/>

                 */
            },
            conditionalCellStyles: [
                { when: row => row.checkboxes[cset_col.codeset_id],
                    style: {backgroundColor: 'green'}
                }
            ],
            // sortable: true,
            compact: true,
            width: '20px',
            // maxWidth: 50,
            center: true,
        }
        return def;
    });
    let coldefs = [
        {
            name: 'Concept name',
            selector: row => row.concept_name,
            format: (row, idx) => {
                /*
                if (!(idx % 100)) {
                    console.log('showing row', idx);
                }
                */
                if (!row.checkboxes) {
                    console.log('problem!!!!', {idx, row, rowData})
                }
                let content = nested
                    ? row.has_children
                        ? collapsed[row.path]
                            ? <span className="toggle-collapse" onClick={() => toggleCollapse(row)}><AddCircle sx={{fontSize:'13px'}}/> {row.concept_name} {row.collapsed && 'collapsed'}</span>
                            : <span className="toggle-collapse" onClick={() => toggleCollapse(row)}><RemoveCircle sx={{fontSize:'13px'}}/> {row.concept_name} {row.collapsed && 'collapsed'}</span>
                        : <span><RemoveCircle sx={{fontSize:'13px', visibility:'hidden'}}/> {row.concept_name}</span>
                    : row.concept_name
                return content;
            },
            // sortable: true,
            // maxWidth: '300px',
            //  table: style: maxWidth is 85% and selected_csets are 50px, so fill
            //      the rest of the space with this column
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
            name: 'Patients',
            selector: row => row.distinct_person_count,
            width: '50px',
        },
        {
            name: 'Records',
            selector: row => row.total_count,
            width: '50px',
        },
        ...cset_cols
    ];
    if (!nested) {
        delete coldefs[0].conditionalCellStyles;
    }
    return coldefs;
    console.log('done setting coldefs');

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
    /*
    divider: {
        default: '#073642',
    },
    background: {
        default: '#002b36',
    },
    action: {
      button: 'rgba(0,0,0,.54)',
      hover: 'rgba(0,0,0,.08)',
      disabled: 'rgba(0,0,0,.12)',
    },
    */
}, 'light');

function styles() {
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
        headRow: {
            style: {
                // backgroundColor: theme.background.default,
                height: '182px',
                // borderBottomWidth: '1px',
                // borderBottomColor: theme.divider.default,
                borderBottomStyle: 'solid',
                padding: 0,
                verticalAlign: 'bottom',
                // border: '3px solid red',
                overflow: 'visible',
                textOverflow: 'unset',
                marginTop: 'auto',
            },
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
                // border: '3px solid green',
                padding: 0,
                // paddingLeft: '8px', // override the cell padding for head cells
                // paddingRight: '8px',
            },
        },
        rows: {
            style: {
                color: 'black',
                minHeight: '0px', // override the row height    -- doesn't work, can only seem to do it from css
                padding: '2px',
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
        /*
        */
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