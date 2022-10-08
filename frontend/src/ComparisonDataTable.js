import React, {useState, useEffect, /* useReducer, useRef, */} from 'react';
import DataTable, { createTheme } from 'react-data-table-component';
import Checkbox from '@mui/material/Checkbox';
import {createSearchParams} from "react-router-dom";
import Button from "@mui/material/Button";
import {omit, uniq, } from 'lodash';
import axios from "axios";
import {backend_url} from "./App";


function ComparisonDataTable(props) {
    const {codeset_ids=[], cset_data={}} = props;
    const {flattened_concept_hierarchy=[], concept_set_members_i=[], all_csets=[], } = cset_data;
    const [nested, setNested] = useState(true);
    let nodups = flattened_concept_hierarchy.map(d => omit(d, ['level', ]))
    nodups = uniq(nodups.map(d => JSON.stringify(d))).map(d => JSON.parse(d))
    let rowData = nested ? flattened_concept_hierarchy : nodups;

    const customStyles = styles();
    const coldefs = useColConfig(codeset_ids, nested, all_csets, rowData, nodups);

    // TODO: Datatable is getting cut off vertically, as if it's in an iframe, but it has no scroll bar.
    return (
        /* https://react-data-table-component.netlify.app/ */
        <DataTable
            className="comparison-data-table"
            theme="custom-theme"
            // theme="light"
            columns={coldefs}
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
            // {...props}
        />
    );
}
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
function useColConfig(codeset_ids, nested, all_csets, rowData, nodups) {
    // const {codeset_ids=[], cset_data={}, nested=true, nodups=[], } = props;
    // const {flattened_concept_hierarchy=[], concept_set_members_i=[], all_csets=[], } = cset_data;
    let selected_csets = all_csets.filter(d => codeset_ids.includes(d.codeset_id));

    const [cbStates, setCbStates] = useState({});
    const [coldefs, setColdefs] = useState([]);
    const [stateChanges, setStateChanges] = useState(0);

    useEffect(() => {
        setCbStates(getCbStates(selected_csets, nodups));
    }, [selected_csets.length])
    console.log(cbStates);

    let checkboxChange = (codeset_id, concept_id) => (evt, state) => {
        console.log({codeset_id, concept_id, state});
        cbStates[codeset_id][concept_id] = state;
        setCbStates(cbStates);
        setStateChanges(stateChanges + 1);
        let url = backend_url(`modify-cset?codeset_id=${codeset_id}&concept_id=${concept_id}&state=${state}`);
        axios.get(url).then((res) => {
            console.log({url, res});
            return res.data
        })
    }
    useEffect(() => {
        if (! Object.keys(cbStates).length) {
            return
        }
        let cset_cols = selected_csets.map(cset_col => {
            let def = {
                // id: ____?,
                name: cset_col.concept_set_version_title,
                // selector: row => row.selected ? '\u2713' : '',
                selector: row => {
                    // let checked = row.codeset_ids.includes(parseInt(cset_col.codeset_id));
                    let checked = cbStates[cset_col.codeset_id][row.concept_id];
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
    }, [cbStates, stateChanges])

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