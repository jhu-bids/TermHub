import React from 'react';
import DataTable from 'react-data-table-component';
// import Checkbox from '@material-ui/core/Checkbox';
// import ArrowDownward from '@material-ui/icons/ArrowDownward';
// const sortIcon = <ArrowDownward />;
// const selectProps = { indeterminate: isIndeterminate => isIndeterminate };

function ComparisonDataTable(props) {
    let data = props.rowData;

    console.log(props);
    const columns = [
        {
            name: 'Concept name',
            selector: row => row.ConceptID,
            sortable: true,
        },
        {
            name: 'Asthma wide',
            selector: row => row.asthma_wide,
        },
    ];

    return (
        <DataTable

            columns={columns}
            data={data}

            dense
            fixedHeader
            fixedHeaderScrollHeight="500px"
            highlightOnHover
            responsive
            striped
            subHeaderAlign="right"
            subHeaderWrap
            //pagination
            //selectableRowsComponent={Checkbox}
            //selectableRowsComponentProps={selectProps}
            //sortIcon={sortIcon}
            {...props}
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