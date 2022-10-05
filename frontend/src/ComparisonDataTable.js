import React, {useState, useEffect, /* useReducer, useRef, */} from 'react';
import DataTable, { createTheme } from 'react-data-table-component';
import {createSearchParams} from "react-router-dom";
import Button from "@mui/material/Button";
import {omit, uniq, } from 'lodash';

function ComparisonDataTable(props) {
    const {codeset_ids=[], cset_data={}} = props;
    const {flattened_concept_hierarchy=[], concept_set_members_i=[], all_csets=[], } = cset_data;
    const [nested, setNested] = useState(true);
    let nodups = flattened_concept_hierarchy.map(d => omit(d, ['level', ]))
    nodups = uniq(nodups.map(d => JSON.stringify(d))).map(d => JSON.parse(d))

    const customStyles = styles();
    const [columns, setColumns] = useState(colConfig(props));

    useEffect(() => {
        setColumns(colConfig(props));
    }, [nested]);  // maybe not necessary to have location in dependencies

    return (
        /* https://react-data-table-component.netlify.app/ */
        <div>
            <h5 style={{margin:20, }}>
                <Button onClick={() => setNested(true)}>
                    {flattened_concept_hierarchy.length} lines in nested list.
                </Button>
                <Button onClick={() => setNested(false)}>
                    {nodups.length} lines without nesting
                </Button>
            </h5>
            <ComparisonDataTable nodups={nodups} nested={nested} {...props} />
            <DataTable
                className="comparison-data-table"
                theme="custom-theme"
                // theme="light"
                columns={columns}
                data={nested ? flattened_concept_hierarchy : nodups}
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
        </div>
    );
}
function colConfig(props) {
    const {codeset_ids=[], cset_data={}, nested=true, nodups=[], } = props;
    const {flattened_concept_hierarchy=[], concept_set_members_i=[], all_csets=[], } = cset_data;

    let cset_columns = (all_csets
        .filter(d => codeset_ids.includes(d.codeset_id))
        .map(ci => {
            let def = {
                // id: ____?,
                name: ci.concept_set_version_title,
                // selector: row => row.selected ? '\u2713' : '',
                selector: row => {
                    return row.codeset_ids.includes(parseInt(ci.codeset_id)) ? '\u2713' : '';
                },
                // sortable: true,
                compact: true,
                width: '50px',
                // maxWidth: 50,
                center: true,
            }
            return def;
        }));
    let columns = [
        // { name: 'level', selector: row => row.level, },
        {
            name: 'Concept name',
            selector: row => row.concept_name,
            // sortable: true,
            // maxWidth: '300px',
            //  table: style: maxWidth is 85% and cset_columns are 50px, so fill
            //      the rest of the space with this column
            width: (window.innerWidth - cset_columns.length * 50) * .85,
            wrap: true,
            compact: true,
            conditionalCellStyles: [
                { when: row => true,
                    style: row => ({paddingLeft: 16 + row.level * 16 + 'px'})
                }
            ],
        },
        ...cset_columns
    ];
    if (!nested) {
        delete columns[0].conditionalCellStyles;
    }
    return columns;
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