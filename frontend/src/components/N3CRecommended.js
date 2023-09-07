import React, { useState, useEffect, } from "react";
import DataTable, { createTheme } from "react-data-table-component";
import {useDataGetter} from "../state/DataGetter";
import {fmt, saveCsv, useWindowSize} from "./utils";
import {TextH2} from "./AboutPage";

export const N3CRecommended = () => {
  const [data, setData] = useState(null);
  const dataGetter = useDataGetter();
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
        let csv = json2csv(rows);
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
      <pre>{JSON.stringify(data, null, 2)}</pre>
    </div>
  );
};

function json2csv(items) {
  const replacer = (key, value) => value === null ? '' : value // specify how you want to handle null values here
  const header = Object.keys(items[0])
  const csv = [
    header.join(','), // header row first
    ...items.map(row => header.map(fieldName => JSON.stringify(row[fieldName], replacer)).join(','))
  ].join('\r\n')
  return csv;
}