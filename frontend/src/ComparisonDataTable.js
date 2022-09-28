import React from 'react';
import DataTable, { createTheme } from 'react-data-table-component';

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


// import Checkbox from '@material-ui/core/Checkbox';
// import ArrowDownward from '@material-ui/icons/ArrowDownward';
// const sortIcon = <ArrowDownward />;
// const selectProps = { indeterminate: isIndeterminate => isIndeterminate };

// https://react-data-table-component.netlify.app/?path=/docs/api-custom-styles--page
//  Internally, customStyles will deep merges your customStyles with the default styling.

function ComparisonDataTable(props) {
    let {data} = props;
    let {csets_info, lines, related} = data;

    console.log(props);
    let cset_columns = Object.keys(csets_info).map(codeset_id => {
        let ci = csets_info[codeset_id]
        let def = {
            // id: ____?,
            name: ci.concept_set_version_title,
            selector: row => {
                return row.codeset_ids.includes(parseInt(codeset_id)) ? '\u2713' : '';
            },
            // sortable: true,
            compact: true,
            width: '50px',
            // maxWidth: 50,
            center: true,
        }
        return def;
    })
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
    const customStyles = {
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
                height: '152px',
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

    return (
        <DataTable

            theme="custom-theme"
            // theme="light"
            columns={columns}
            data={lines}
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