import React, {useState, useEffect, useMemo, /* useReducer, useRef, */} from 'react';
import DataTable, { createTheme } from 'react-data-table-component';
import Checkbox from '@mui/material/Checkbox';
// import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
// import MoreVertIcon from '@mui/icons-material/MoreVert';
import {createSearchParams} from "react-router-dom";
import Button from "@mui/material/Button";
import {omit, uniq, reduce, cloneDeepWith, } from 'lodash';
import axios from "axios";
import {backend_url} from "./App";


function ComparisonDataTable(props) {
    const {codeset_ids=[], cset_data={}} = props;
    const {hierarchy={}, flattened_concept_hierarchy=[], concept_set_members_i=[], all_csets=[], } = cset_data;
    const [nested, setNested] = useState(true);
    let nodups;
    // const [coldefs, setColdefs] = useState([]);

    let selected_csets = all_csets.filter(d => codeset_ids.includes(d.codeset_id));

    let junk = cloneDeepWith(hierarchy, function(c) {
        return c;
    })


    const [rowData, setRowData] = useState();
    function tableDataUpdate(nested, flattened_concept_hierarchy, nodups, row, updateFunc) {
        let rowData = nested ? flattened_concept_hierarchy : nodups;
        if (row && updateFunc) {
            if (updateFunc === 'toggleCollapse') {
                row.collapsed = !row.collapsed
                if (row.collapsed) {
                    let rowsToHide = [];
                    function iter(parentsToHideChildrenOf, row, i, data) {
                        if (parentsToHideChildrenOf.length) {
                            let moreRowsToHide = rowData.filter(d => parentsToHideChildrenOf.includes(d.parent_line));
                            rowsToHide = rowsToHide.concat(moreRowsToHide);
                            return moreRowsToHide.filter(d => d.has_children).map(d => d.line_no)
                        }
                        return [];
                    }
                    reduce(rowData, iter, [row.line_no]);
                    console.log(rowsToHide);
                    rowData = rowData.filter(d => !rowsToHide.includes(d.line_no))
                }
            } else if (typeof(updateFunc) === 'function') {
                updateFunc(row);
            } else {
                throw `unrecognized updateFunc ${updateFunc}`
            }
            // row.concept_name = row.concept_name + ' x';
            rowData[row.line_no] = row;
        }
        //console.log(rowData);
        setRowData(rowData);
    }
    useEffect(() => {
        let nodups = flattened_concept_hierarchy.map(d => omit(d, ['level', ]));
        nodups = uniq(nodups.map(d => JSON.stringify(d))).map(d => JSON.parse(d));
        nodups.forEach((row,i) => {
            row.checkboxes = selected_csets.map(cset => row.codeset_ids.includes(cset.codeset_id));
            row.line_no = i;
        })
        flattened_concept_hierarchy.forEach((row,i) => {
            row.line_no = i;
            row.checkboxes = selected_csets.map(cset => row.codeset_ids.includes(cset.codeset_id));
        });
        tableDataUpdate(nested, flattened_concept_hierarchy, nodups);
    }, [selected_csets.length]);

    const columns = useMemo(() => {
        return plainColConfig(codeset_ids, nested, selected_csets, flattened_concept_hierarchy, nodups, tableDataUpdate);
    });

    const customStyles = styles();
    // const coldefs = useColConfig(codeset_ids, nested, selected_csets, flattened_concept_hierarchy, nodups, tableDataUpdate);

    // TODO: Datatable is getting cut off vertically, as if it's in an iframe, but it has no scroll bar.
    return (
        /* https://react-data-table-component.netlify.app/ */
        <DataTable
            className="comparison-data-table"
            theme="custom-theme"
            // theme="light"
            columns={columns}
            // data={props.nested ? flattened_concept_hierarchy : props.nodups}
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
function plainColConfig(codeset_ids, nested, selected_csets, flattened_concept_hierarchy, nodups, tableDataUpdate) {
    let checkboxChange = (codeset_id, concept_id) => (evt, state) => {
        console.log({codeset_id, concept_id, state});
        let url = backend_url(`modify-cset?codeset_id=${codeset_id}&concept_id=${concept_id}&state=${state}`);
        axios.get(url).then((res) => {
            console.log({url, res});
            return res.data
        })
    }
    let toggleExpand = (row) => {
        tableDataUpdate(nested,
                        flattened_concept_hierarchy,
                        nodups,
                        row,
                        'toggleCollapse'
                        // row => row.collapsed = !row.collapsed
        )
    }
    let cset_cols = selected_csets.map((cset_col, col_idx) => {
        let def = {
            // id: ____?,
            name: cset_col.concept_set_version_title,
            // selector: row => row.selected ? '\u2713' : '',
            selector: row => {
                // let checked = row.codeset_ids.includes(parseInt(cset_col.codeset_id));
                // let checked = cbStates[cset_col.codeset_id][row.concept_id];
                let checked = row.checkboxes[col_idx];
                // let toggle = <span
                return checked ? '\u2713' : '';
                let checkbox_id = `${cset_col.codeset_id}:${row.concept_id}`;
                return <Checkbox checked={checked}
                                 onChange={checkboxChange(cset_col.codeset_id, row.concept_id)}/>
            },
            // sortable: true,
            compact: true,
            width: '50px',
            // maxWidth: 50,
            center: true,
        }
        return def;
    });
    let coldefs = [
        // { name: 'level', selector: row => row.level, },
        {
            name: 'Concept name',
            selector: row => row.concept_name,
            format: row => {
                let content = row.has_children
                    ? row.collapsed
                        ? <span onClick={() => toggleExpand(row)}>{expandIcon}{row.concept_name} {row.collapsed && 'collapsed'}</span>
                        : <span onClick={() => toggleExpand(row)}>{collapseIcon}{row.concept_name} {row.collapsed && 'collapsed'}</span>
                    : <span>{blankIcon}{row.concept_name}</span>
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
        ...cset_cols
    ];
    if (!nested) {
        delete coldefs[0].conditionalCellStyles;
    }
    return coldefs;
}
function useColConfig(codeset_ids, nested, selected_csets, flattened_concept_hierarchy, nodups, tableDataUpdate) {

    // const [cbStates, setCbStates] = useState({});
    const [coldefs, setColdefs] = useState([]);
    // const [stateChanges, setStateChanges] = useState(0);
    // const [collapsedRows, setCollapsedRows] = useState([]);

    /*
    useEffect(() => {
        setCbStates(getCbStates(selected_csets, nodups));
    }, [selected_csets.length])
    console.log({nodups, cbStates, flattened_concept_hierarchy});
    */

    let checkboxChange = (codeset_id, concept_id) => (evt, state) => {
        console.log({codeset_id, concept_id, state});
        /*
        cbStates[codeset_id][concept_id] = state;
        setCbStates(cbStates);
        setStateChanges(stateChanges + 1);
        */
        let url = backend_url(`update-cset?codeset_id=${codeset_id}&concept_id=${concept_id}&state=${state}`);
        axios.get(url).then((res) => {
            console.log({url, res});
            return res.data
        })
    }
    let toggleExpand = (row) => {
        tableDataUpdate(nested,
                        flattened_concept_hierarchy,
                        nodups,
                        row,
                        row => row.collapsed = !row.collapsed)
        /*
        console.log('toggling', row, collapsedRows)
        collapsedRows[row.line_no] = !collapsedRows[row.line_no];
        setCollapsedRows(collapsedRows);
        row.collapsed = !row.collapsed;
        */
    }
    useEffect(() => {
        /*
        if (! Object.keys(cbStates).length) {
            return
        }
        */
        let cset_cols = selected_csets.map((cset_col, col_idx) => {
            let def = {
                // id: ____?,
                name: cset_col.concept_set_version_title,
                // selector: row => row.selected ? '\u2713' : '',
                selector: row => {
                    // let checked = row.codeset_ids.includes(parseInt(cset_col.codeset_id));
                    // let checked = cbStates[cset_col.codeset_id][row.concept_id];
                    let checked = row.checkboxes[col_idx];
                    // let toggle = <span
                    // return checked ? '\u2713' : '';
                    let checkbox_id = `${cset_col.codeset_id}:${row.concept_id}`;
                    return <Checkbox checked={checked}
                                     onChange={checkboxChange(cset_col.codeset_id, row.concept_id)}/>
                },
                // sortable: true,
                compact: true,
                width: '50px',
                // maxWidth: 50,
                center: true,
            }
            return def;
        });
        let coldefs = [
            // { name: 'level', selector: row => row.level, },
            {
                name: 'Concept name',
                selector: row => row.concept_name,
                format: row => row.has_children
                                    ? row.collapsed
                                        ? <span onClick={() => toggleExpand(row)}>{expandIcon}{row.concept_name} {row.collapsed && 'collapsed'}</span>
                                        : <span onClick={() => toggleExpand(row)}>{collapseIcon}{row.concept_name} {row.collapsed && 'collapsed'}</span>
                                    : <span>{blankIcon}{row.concept_name}</span>,
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
            ...cset_cols
        ];
        if (!nested) {
            delete coldefs[0].conditionalCellStyles;
        }
        setColdefs(coldefs);
    }, [selected_csets.length]); // [cbStates, stateChanges, collapsedRows])

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
                minHeight: '32px',
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
                minHeight: 'auto', // override the row height
                borderLeft: '0.5px solid #BBB',
            },
        },
        cells: {
            style: {
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
const expandIcon    = <svg fill="currentColor" height="20" viewBox="0 -6 24 24" width="24" xmlns="http://www.w3.org/2000/svg"><path d="M8.59 16.34l4.58-4.59-4.58-4.59L10 5.75l6 6-6 6z"></path><path d="M0-.25h24v24H0z" fill="none"></path></svg>
const collapseIcon  = <svg fill="currentColor" height="20" viewBox="0 -6 24 24" width="24" xmlns="http://www.w3.org/2000/svg"><path d="M7.41 7.84L12 12.42l4.59-4.58L18 9.25l-6 6-6-6z"></path><path d="M0-.75h24v24H0z" fill="none"></path></svg>
const blankIcon     = <svg fill="currentColor" height="20" viewBox="0 -6 24 24" width="24" xmlns="http://www.w3.org/2000/svg" />
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