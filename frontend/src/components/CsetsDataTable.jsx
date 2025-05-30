import React, { useState, useCallback, useEffect } from "react";
import { throttle } from "lodash";
import DataTable, { createTheme } from "react-data-table-component";
import { fmt, pct_fmt } from "../utils";
import { Tooltip } from "./Tooltip";
import { StatsMessage, useCodesetIds, useCids } from '../state/AppState';
// import Checkbox from '@material-ui/core/Checkbox';
// import ArrowDownward from '@material-ui/icons/ArrowDownward';
// const sortIcon = <ArrowDownward />;
// const selectProps = { indeterminate: isIndeterminate => isIndeterminate };

// https://react-data-table-component.netlify.app/?path=/docs/api-custom-styles--page
//  Internally, customStyles will deep merges your customStyles with the default styling.

function getCsetSelectionHandler(tooltipId) {
  const tt = document.getElementById(tooltipId);

  const handleRowMouseEnter = throttle((row, event) => {
    tt.style.left = `${event.clientX}px`;
    tt.style.top = `${event.clientY}px`;
    tt.style.display = 'block';
    console.log("Enter");
    setTimeout(() => {
      tt.style.display = 'none';
    }, 1500)
  }, 100);

  const handleRowMouseLeave = throttle((row, event) => {
    tt.style.display = 'none';
    console.log("Leave");
  }, 0);

  return [handleRowMouseEnter, handleRowMouseLeave];
}

/* TODO: review function for appropriate state management */
export function CsetsDataTable(props) {
  const { show_selected, selected_csets, clickable, showTitle, } = props;
  // const {codeset_ids, codesetIdsDispatch} = props;
  const [codeset_ids, codesetIdsDispatch] = useCodesetIds();
  const [cids, ] = useCids();
  // const spState = useSearchParamsState();
  // const codeset_ids = show_selected ? null : props.codeset_ids;
  const relatedCsets = show_selected ? null : props.relatedCsets;
  const all_csets = show_selected ? null : props.all_csets;
  const concept_ids = show_selected ? null : props.concept_ids;

  let coldefs = getColdefs();
  /* const conditionalRowStyles = [{ when: row => row.selected,
        style: { backgroundColor: 'rgba(63, 195, 128, 0.9)', color: 'white',
                '&:hover': { cursor: 'pointer', }, } }]; */

  let customStyles = getCustomStyles();

  const handleRowClick = useCallback(
    row => codesetIdsDispatch({
      type: show_selected ? 'delete_codeset_id' : 'add_codeset_id',
      codeset_id: row.codeset_id,
    })
    // (row) => spState[ show_selected ? 'removeFromArray' : 'addToArray']('codeset_ids',  row.codeset_id)
  );
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
  const subHeader = show_selected ? null : <StatsMessage
      {...{ codeset_ids, all_csets, relatedCsets,
        concept_ids, selected_csets, cids, } } />;
  // const [handleRowMouseEnter, handleRowMouseLeave] =
  //     getCsetSelectionHandler(show_selected ? 'select-to-remove' : 'select-to-add');

  const rowSelectCritera = (row) => row.selected;
  // todo: p -> data table: data table has a property for showing some sort of paragraph text
  // TODO: y concepts -> get the number
  return (
    <div
        className="csets-data-table"
        id={show_selected ? "selected-csets-table" : "related-csets-table"}
    >
      <DataTable
        data={show_selected? selected_csets : relatedCsets}
        // selectableRows
        selectableRowsHighlight
        selectableRowSelected={rowSelectCritera}
        // onSelectedRowsChange={handleSelectionChange}
        onRowClicked={clickable ? handleRowClick : (() => {})}
        // onRowMouseEnter={handleRowMouseEnter}
        // onRowMouseLeave={handleRowMouseLeave}
        customStyles={customStyles}
        noHeader={false}
        title={showTitle ? ((show_selected ? "Selected" : "Related") +
          ` concept sets. Click row to ${show_selected ? 'deselect' : 'add to selection'}`)
          : null}
        subHeader={!show_selected}
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
  /*
    const descending = (rows, selector, direction) => {
        return orderBy(rows, selector, ['desc']);
    };
     */
  let coldefs = [
    // { name: 'level', selector: row => row.level, },
    {
      name: "Version ID",
      // selector: row => `${row.concept_set_name} (v${row.version})`,
      selector: (row) => row.codeset_id,
      compact: true,
      sortable: true,
      width: "90px",
    },
    {
      name: "Concept set name",
      selector: (row) => row.concept_set_version_title || `${row.alias} (v${row.version})`,
      wrap: true,
      compact: true,
      sortable: true,
    },
    {
      name: (
        <Tooltip label="Number of definition items in this concept set.">
          <span>Definition concepts</span>
        </Tooltip>
      ),
      selector: (row) => (row.counts || {})['Expression items'] ?? 0,
      compact: true,
      width: "73px",
      center: true,
      sortable: true,
    },
    {
      name: (
          <Tooltip label="Number of members in this concept set, that is, concepts included after expanding definition concepts.">
            <span>Expansion concepts</span>
          </Tooltip>
      ),
      selector: (row) => (row.counts || {})['Members'] ?? 0,
      compact: true,
      width: "72px",
      center: true,
      sortable: true,
    },
    {
      name: (
          <Tooltip label="Number of concepts in this set overlapping with all the concepts selected.">
            <span>Common</span>
          </Tooltip>
      ),
      selector: (row) => row.intersecting_concepts,
      compact: true,
      width: "66px",
      center: true,
      sortable: true,
    },
    {
      name: 'Vocabularies',
      selector: (row) => row.vocabs,
      compact: true,
      width: "200px",
      sortable: true,
      wrap: true,
    },
    {
      name: (
        <Tooltip label="Approximate distinct person count. Small counts rounded up to 20.">
          <span>Patients</span>
        </Tooltip>
      ),
      // selector: row => row.approx_distinct_person_count.toLocaleString(),
      selector: (row) => parseInt(row.distinct_person_cnt),
      format: (row) => fmt(parseInt(row.distinct_person_cnt)),
      compact: true,
      width: "70px",
      center: true,
      sortable: true,
    },
    {
      name: (
        <Tooltip label="Record count. Small counts rounded up to 20.">
          <span>Records</span>
        </Tooltip>
      ),
      selector: (row) => {
        return (row.total_cnt ?? 0).toLocaleString();
      },
      compact: true,
      width: "78px",
      center: true,
      sortable: true,
    },
      /*
    {
      name: (
          <Tooltip label="Number of members in this concept set that can be hidden in the CSET COMPARISON page.">
            <span>Hidden Members</span>
          </Tooltip>
      ),
      selector: 0,
      compact: true,
      width: "70px",
      center: true,
      sortable: true,
    },
     */
  ];

  return coldefs;
}

function getCustomStyles() {
  return {
    table: {
      style: {
        padding: "20px",
        margin: "1%",
        width: "98%",
        // margin: '20px',
        // height: '20vh',
        // maxWidth: '85%',
        // maxWidth: '400px', doesn't work ?
      },
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
/*
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
}, 'light');
*/