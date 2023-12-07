import React, { useState, useEffect, } from "react";
import DataTable, { createTheme } from "react-data-table-component";

import {useDataGetter} from "../state/DataGetter";
import {useSearchParamsState} from "../state/SearchParamsProvider";
import {fmt, saveCsv, useWindowSize} from "./utils";
import {TextH2} from "./AboutPage";
import Button from "@mui/material/Button";
import {Link} from "react-router-dom";

export const N3CRecommended = () => {
  const [data, setData] = useState(null);
  const dataGetter = useDataGetter();
  const {sp} = useSearchParamsState();

  if (sp.comparison) {
    return <N3CComparisonRpt />;
  }

  const filename = 'n3c-recommended-report';

  useEffect(() => {
    (async () => {
      if (data) {
        return;
      }
      try {
        // const response = await axios.get("https://api.example.com/data");
        const rows = await dataGetter.axiosCall(`${filename}?as_json=true`, {sendAlert: false, });
        const columns = Object.keys(rows[0]);
        setData(rows);
        saveCsv(rows, columns, filename);
        // let csv = json2csv(rows);
      } catch (error) {
        console.error("Error fetching data:", error);
      }
    })();
  });

  let columns;
  if (data) {
    columns = Object.keys(data[0]).map(col => ({
      name: col,
      selector: row => (row[col] ?? '').toString(),
    }));
  }

  console.log({columns, data});
  return (
    <div>
      <TextH2>
        Downloading N3C recommended concept sets to <samp style={{backgroundColor: '#CCC'}}>{filename}.csv</samp> in your downloads folder.
      </TextH2>
      <DataTable
          data={data || []}
          columns={columns}
          // noHeader={false}
          dense
          direction="auto"
          // fixedHeader
          // fixedHeaderScrollHeight="300px"
          responsive
          // sortFunction={customSort}
      />
      {/*<pre>{JSON.stringify(data, null, 2)}</pre>*/}
    </div>
  );
};

/*  can't recall what this was for,
    it was being called in the useEffect above, but the result
    was never used. so, commenting out now
function json2csv(items) {
  const replacer = (key, value) => value === null ? '' : value // specify how you want to handle null values here
  const header = Object.keys(items[0])
  const csv = [
    header.join(','), // header row first
    ...items.map(row => header.map(fieldName => JSON.stringify(row[fieldName], replacer)).join(','))
  ].join('\r\n')
  return csv;
}
 */

export const N3CComparisonRpt = () => {
  const [data, setData] = useState(null);
  const dataGetter = useDataGetter();

  useEffect(() => {
    (async () => {
      if (data) {
        return;
      }
      try {
        const rows = await dataGetter.axiosCall('n3c-comparison-rpt', {sendAlert: false, });
        setData(rows);
      } catch (error) {
        console.error("Error fetching data:", error);
      }
    })();
  });

  if (!data) {
    return <div>Loading...</div>;
  }
  let columns;
  /*
  if (data) {
    columns = Object.keys(data[0]).map(col => ({
      name: col,
      selector: row => (row[col] ?? '').toString(),
      // width: "fit-content",
    }));
  }
  */
  columns = [
    {grow: 4, sortable: true, name: "Name", selector: row => row.name},
    {grow: 2, sortable: true, name: "Author", selector: row => row.author},
    {grow: 3, sortable: true, name: "Orig", selector: row => row.cset_1, wrap: true},
    {grow: 3, sortable: true, name: "New", selector: row => row.cset_2, wrap: true},
    {grow: 2, name: "Compare", selector: row => (
          <Button
              to={`/cset-comparison?codeset_ids=${row.cset_1_codeset_id}&codeset_ids=${row.cset_2_codeset_id}`}
              component={Link}
              style={{margin: '7px', textTransform: 'none'}}
          >
            {row.diffs.filter(d => d.startsWith('removed')).length} removed
            , {row.diffs.filter(d => d.startsWith('added')).length} added
            {/*orig {String.fromCodePoint(0x2192)} new*/}
          </Button>

      )},
      /*
    {grow: 2, name: "Orig", selector: row => (
        <span>
          {row.orig_codeset_id} v{row.orig_version} {' '}
          {}
        </span>
      )},
    {grow: 2, name: "New", selector: row => (
      )},
       */
  ]

  /*
   */

  console.log({columns, data});
  return (
      <div>
        <DataTable
            data={data || []}
            columns={columns}
            expandableRows
            expandableRowsComponent={DiffList}
            defaultSortFieldId={1}

            // noHeader={false}
            dense
            direction="auto"
            fixedHeader
            // fixedHeaderScrollHeight="300px"
            responsive
            // sortFunction={customSort}
        />
        {/*<pre>{JSON.stringify(data, null, 2)}</pre>*/}
      </div>
  );
}
function DiffList({data}) {
  console.log({data});
  return (
      <div style={{margin: 10,}}>
        <p>
          <b>Differences:</b><br/>
          {
            data.diffs.map((diff,i) => (
               <span key={i}>{diff}<br/></span>
            ))
          }
        </p>
      </div>
  );
}
