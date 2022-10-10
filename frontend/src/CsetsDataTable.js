import React from 'react';
import {isEqual, orderBy, } from 'lodash';
import DataTable, { createTheme } from 'react-data-table-component';
import {useSearchParams} from "react-router-dom";

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

function CsetsDataTable(props) {
    const {codeset_ids=[], cset_data={}} = props;
    const {flattened_concept_hierarchy=[], concept_set_members_i=[], all_csets=[], } = cset_data;

    let related_csets = all_csets.filter(d => d.related);

    console.log('CsetsDataTable props: ', props);
    const [selectedRows, setSelectedRows] = React.useState(false);
    const [searchParams, setSearchParams] = useSearchParams();
    // const [toggledClearRows, setToggleClearRows] = React.useState(false);
    /*  example row
    {
        "codeset_id": 826535586,
        "concept_set_name": "UVA Equity Asthma",
        "version": "1",
        "concepts": 619,
        "selected": true
    }
    */
    let coldefs = getColdefs();
    /*
    const conditionalRowStyles = [{
        when: row => row.selected,
        style: {
            backgroundColor: 'rgba(63, 195, 128, 0.9)',
            color: 'white',
            '&:hover': {
                cursor: 'pointer',
            },
        }
    }];
    */

    let customStyles = getCustomStyles();
    const handleSelectionChange = React.useCallback(state => {
        const {selectedRows} = state;
        let ids = selectedRows.map(d => d.codeset_id).sort()
        if (!isEqual(codeset_ids, ids)) {
            setSearchParams({codeset_id: ids});
        }
        // setSelectedRows(selectedRows);
    }, [])

    const related_ids = new Set(flattened_concept_hierarchy.map(d => d.concept_id));
    const all_concept_ids = new Set(concept_set_members_i.map(d => d.concept_id));
    let stats = {
        csets_chosen: codeset_ids.length,
        hierarchy_concepts: related_ids.size,
        nested_list_lines: flattened_concept_hierarchy.length,
        total_concepts: all_concept_ids.size,
        related_csets: related_csets.length,
    }
    let not_in_list = [...concept_set_members_i].filter(d => !related_ids.has(d.concept_id))
    console.log(not_in_list);

    const subHeader = <div>
        <p style={{margin:0, fontSize: 'small',}}>The <strong>{stats.csets_chosen} concept sets </strong>
            selected contain a total of <strong>{stats.total_concepts} distinct concepts </strong>
            of which <strong>only {stats.hierarchy_concepts}</strong> (why? not sure yet) appear
            in the <strong>{stats.nested_list_lines} lines</strong> of the nested hierarchy on the
            comparison page.</p>
        <p> The following <strong>{stats.related_csets} concept sets</strong> have 1 or more concepts
            in common with the selected sets. Select from below if you want to add to the above list.</p>
    </div>;

    const rowSelectCritera = row => row.selected;
    // todo: p -> data table: data table has a property for showing some sort of paragraph text
    // TODO: y concepts -> get the number
    return (
        <div className="csets-data-table" >
            <DataTable
                noHeader={false}
                title="Related concept sets"
                subHeader
                subHeaderComponent={subHeader}
                // theme="custom-theme"
                // theme="light"
                columns={coldefs}
                defaultSortFieldId={4}
                defaultSortAsc={false}
                data={related_csets}

                //customStyles={customStyles}   PUT THIS BACK

                // conditionalRowStyles={conditionalRowStyles}
                height="300px"
                //striped
                //pagination
                //selectableRowsComponent={Checkbox}
                //selectableRowsComponentProps={selectProps}
                //sortIcon={sortIcon}
                // {...props}

                dense
                direction="auto"
                // expandOnRowClicked
                // expandableRows
                fixedHeader
                fixedHeaderScrollHeight="300px"
                highlightOnHover
                pointerOnHover
                responsive
                selectableRows
                selectableRowsHighlight
                selectableRowSelected={rowSelectCritera}
                onSelectedRowsChange={handleSelectionChange}
                subHeaderAlign="left"
                subHeaderWrap
                // sortFunction={customSort}
            />
        </div>
    );
}
function getColdefs() {
    const pct_fmt = num => Number(num/100).toLocaleString(undefined,{style: 'percent', minimumFractionDigits:2});
    const descending = (rows, selector, direction) => {
        return orderBy(rows, selector, ['desc']);
    };
    return [
        // { name: 'level', selector: row => row.level, },
        {
            name: 'Concept set name',
            // selector: row => `${row.concept_set_name} (v${row.version})`,
            selector: row => row.concept_set_version_title,
            wrap: true,
            compact: true,
            sortable: true,
        },
        {
            name: 'Concepts',
            selector: row => row.concepts,
            compact: true,
            width: '70px',
            center: true,
            sortable: true,
        },
        {
            name: 'Shared concepts',
            selector: row => row.intersecting_concepts,
            compact: true,
            width: '70px',
            center: true,
            sortable: true,
        },
        {
            name: 'Precision',
            selector: row => row.precision,
            format: row => pct_fmt(row.precision),
            desc: true,
            compact: true,
            width: '70px',
            center: true,
            sortable: true,
            // sortFunction: descending,
        },
        {
            name: 'Recall',
            selector: row => pct_fmt(row.recall),
            compact: true,
            width: '70px',
            center: true,
            sortable: true,
        },
        {
            name: 'Archived',
            selector: row => row.archived ? '\u2713' : '',
            compact: true,
            width: '70px',
            center: true,
            sortable: true,
        },
    ];
}

function getCustomStyles() {
    return {
        table: {
            style: {
                padding: '20px',
                width: '100%',
                // margin: '20px',
                // height: '20vh',
                // maxWidth: '85%',
                // maxWidth: '400px', doesn't work ?
            }
        },
        /*
        tableWrapper: {
            style: {
                display: 'table',
            },
        },
        denseStyle: {
            minHeight: '32px',
        },
        headRow: {
            style: {
                // backgroundColor: theme.background.default,
                // height: '152px',
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
                marginLeft: '20px',
                padding: '20px',
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
    */
    };
}

export {CsetsDataTable};