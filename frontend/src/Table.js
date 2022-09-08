import React, { useState, useRef, useEffect, useMemo, useCallback} from 'react';
import { render } from 'react-dom';
import { AgGridReact } from 'ag-grid-react'; // the AG Grid React Component

import 'ag-grid-community/styles/ag-grid.css'; // Core grid CSS, always needed
import 'ag-grid-community/styles/ag-theme-alpine.css';
// import {useParams} from "react-router-dom"; // Optional theme CSS

const Table = (props) => {
  const tableHeaderHeight = 100;
  const {rowData, rowCallback} = props;
  // let params = useParams();
  const gridRef = useRef(); // Optional - for accessing Grid's API
  // const [rowData, setRowData] = useState(); // Set rowData to Array of Objects, one Object per Row
 // Each Column Definition results in one Column.
  /*
   const [columnDefs, setColumnDefs] = useState([
     {field: 'make', filter: true},
     {field: 'model', filter: true},
     {field: 'price'}
   ]);
   */
  const [columnDefs, _setColumnDefs] = useState();
  function setColumnDefs(colNames) {
    let defs = colNames.map(n => ({field: n}) )
    _setColumnDefs(defs)
  }
  useEffect(() => {
    if (props.rowData && rowData.length) {
      setColumnDefs(Object.keys(rowData[0]))
    }
  }, [rowData, props]);
  //     [
  // DefaultColDef sets props common to all Columns
  const defaultColDef = useMemo( ()=> ({
     sortable: true
   }));

  // Example of consuming Grid Event
  const cellClickedListener = useCallback( event => {
    const callbackProps = {rowData: event.data, colClicked:event.colDef.field};
    console.log('rowCallback with ' + JSON.stringify(callbackProps, null, 2))
    rowCallback(callbackProps)
  }, [rowCallback]);

  /*
  // Example load data from sever
  useEffect(() => {
    // fetch('https://www.ag-grid.com/example-assets/row-data.json')
    // .then(result => result.json())
    // .then(rowData => setRowData(rowData))
    // fetch('http://localhost:8000/ontocall?path=objects/OMOPConceptSet')
    fetch(apiUrl)
    .then(result => result.json())
    .then(rowData => {
      let rd = rowData.json.data.map(r=>'properties' in r ? r.properties : r)
      // debugger
      setRowData(rd)
      setColumnDefs(Object.keys(rd[0]))
    })
  }, []);
  */

  // Example using Grid's API
  const buttonListener = useCallback( e => {
    gridRef.current.api.deselectAll();
  }, []);

  return (
    <div>

      {/* Example using Grid's API */}
      <button onClick={buttonListener}>Reset table</button>

      {/* On div wrapping Grid a) specify theme CSS Class and b) sets Grid size */}
      <div className="ag-theme-alpine"
            style={{
              width: '95%',
              height: rowData ? (tableHeaderHeight + rowData.length * 75) : tableHeaderHeight,
              //height: window.innerHeight * .8
            }}>

        <AgGridReact
            ref={gridRef} // Ref for accessing Grid's API

            rowData={rowData} // Row Data for Rows

            columnDefs={columnDefs} // Column Defs for Columns
            defaultColDef={defaultColDef} // Default Column Properties

            animateRows={true} // Optional - set to 'true' to have rows animate when sorted
            rowSelection='multiple' // Options - allows click selection of rows

            onCellClicked={cellClickedListener} // Optional - registering for Grid Event
            />
      </div>
    </div>
  );
};

export default Table;