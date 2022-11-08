import React, {useState, useCallback, useEffect, useMemo, } from 'react';
import {isEqual, orderBy, get, } from 'lodash';
import DataTable, { createTheme } from 'react-data-table-component';
import {pct_fmt, StatsMessage, } from './utils';
import {useSearchParams} from "react-router-dom";
import {Tooltip} from './Tooltip';
// import Checkbox from '@material-ui/core/Checkbox';
// import ArrowDownward from '@material-ui/icons/ArrowDownward';
// const sortIcon = <ArrowDownward />;
// const selectProps = { indeterminate: isIndeterminate => isIndeterminate };

// https://react-data-table-component.netlify.app/?path=/docs/api-custom-styles--page
//  Internally, customStyles will deep merges your customStyles with the default styling.

/* TODO: review function for appropriate state management */
function CsetsDataTable(props) {
    const {codeset_ids=[], all_csets=[], cset_data={}} = props;
    const {selected_csets, } = cset_data;
    const [relatedCsets, setRelatedCsets] = useState(cset_data.related_csets);
    const [searchParams, setSearchParams] = useSearchParams();

    useEffect(() => {
        // props.csetData.relatedCsets.forEach(rc => rc.selected = codeset_ids.includes(rc.codeset_id))
        const rcsets = orderBy(get(props, 'cset_data.related_csets', []), ['selected', 'precision'], ['desc', 'desc'])
        // console.log({props, rcsets});
        setRelatedCsets(rcsets);
    }, [codeset_ids.join(','), selected_csets.length])
    let coldefs = getColdefs();
    /* const conditionalRowStyles = [{ when: row => row.selected,
        style: { backgroundColor: 'rgba(63, 195, 128, 0.9)', color: 'white',
                '&:hover': { cursor: 'pointer', }, } }]; */

    let customStyles = getCustomStyles();
    const handleRowClick = useCallback(row => {
        if ((codeset_ids||[]).includes(row.codeset_id)) {
            const cids = codeset_ids.filter(cid => cid !== row.codeset_id);
            setSearchParams({codeset_id: cids, });
        } else {
            setSearchParams({codeset_id: [...codeset_ids, row.codeset_id], });
        }
    }, [codeset_ids]);
    /*
    const handleSelectionChange = useCallback(state => {
        const {selectedRows} = state;
        let ids = selectedRows.map(d => d.codeset_id).sort()
        if (!isEqual(props.codeset_ids, ids)) {
            // console.log(`try to change qs[codeset_id] from ${codeset_ids} to ${ids}`)
            setSearchParams({codeset_id: ids, });
        }
        // setSelectedRows(selectedRows);
    }, [codeset_ids]);
     */

    // const related_ids = new Set(f lattened_concept_hierarchy.map(d => d.concept_id));
    const subHeader = <StatsMessage {...props} />

    const rowSelectCritera = row => row.selected;
    // todo: p -> data table: data table has a property for showing some sort of paragraph text
    // TODO: y concepts -> get the number
    return (
        <div className="csets-data-table" >
            <DataTable
                data={relatedCsets}
                // selectableRows
                selectableRowsHighlight
                selectableRowSelected={rowSelectCritera}
                // onSelectedRowsChange={handleSelectionChange}
                onRowClicked={handleRowClick}

                customStyles={customStyles}
                noHeader={false}
                title="Related concept sets"
                subHeader
                subHeaderComponent={subHeader}
                // theme="custom-theme"
                // theme="light"
                columns={coldefs}
                // defaultSortFieldId={4}
                // defaultSortAsc={false}


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
                subHeaderAlign="left"
                subHeaderWrap
                // sortFunction={customSort}
            />
        </div>
    );
}
function getColdefs() {
    const descending = (rows, selector, direction) => {
        return orderBy(rows, selector, ['desc']);
    };
    return [
        // { name: 'level', selector: row => row.level, },
        {
            name: 'Version ID',
            // selector: row => `${row.concept_set_name} (v${row.version})`,
            selector: row => row.codeset_id,
            compact: true,
            sortable: true,
            width: '90px',
        },
        {
            name: 'Concept set name',
            // selector: row => `${row.concept_set_name} (v${row.version})`,
            selector: row => row.concept_set_version_title,
            wrap: true,
            compact: true,
            sortable: true,
        },
        {
            //name: 'Concepts',
            name:   <Tooltip label="Number of concepts in this concept set.">
                        <span>Concepts</span>
                    </Tooltip>,
            selector: row => row.concepts,
            compact: true,
            width: '70px',
            center: true,
            sortable: true,
        },
        {
            // name: 'Shared concepts',
            name:   <Tooltip label="Number of concepts in this set that also belong to the selected concept sets.">
                        <span>Shared</span>
                    </Tooltip>,
            selector: row => row.intersecting_concepts,
            compact: true,
            width: '70px',
            center: true,
            sortable: true,
        },
        {
            name:   <Tooltip label="Portion of the concepts in this set shared with the selected concept sets.">
                        <span>Precision</span>
                    </Tooltip>,
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
            // name: 'Recall',
            name:   <Tooltip label="Portion of concepts in the selected concept sets that belong to this set.">
                        <span>Recall</span>
                    </Tooltip>,
            selector: row => row.recall,
            format: row => pct_fmt(row.recall),
            desc: true,
            compact: true,
            width: '70px',
            center: true,
            sortable: true,
        },
        {
            name:   <Tooltip label="Approximate distinct person count. Small counts rounded up to 20.">
                        <span>Patients</span>
                    </Tooltip>,
            selector: row => row.approx_distinct_person_count.toLocaleString(),
            compact: true,
            width: '70px',
            center: true,
            sortable: true,
        },
        {
            name:   <Tooltip label="Record count. Small counts rounded up to 20.">
                        <span>Records</span>
                    </Tooltip>,
            selector: row => row.approx_total_record_count.toLocaleString(),
            compact: true,
            width: '78px',
            center: true,
            sortable: true,
        },
        /*
        {
            name:   <Tooltip label="Checked if this concept set is marked as archived in the enclave.">
                <span>Archived</span>
            </Tooltip>,
            selector: row => row.archived ? '\u2713' : '',
            compact: true,
            width: '70px',
            center: true,
            sortable: true,
        },
         */
    ];
}

function getCustomStyles() {
    return {
        table: {
            style: {
                padding: '20px',
                margin: '1%',
                width: '98%',
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

export {CsetsDataTable, };