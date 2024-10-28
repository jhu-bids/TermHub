import React, { useState, useEffect, } from "react";
import DataTable, { createTheme } from "react-data-table-component";
import { flatten, uniq, sortBy, isEmpty } from "lodash";

import {backend_url, useDataGetter} from "../state/DataGetter";
import {useSearchParamsState} from "../state/StorageProvider";
import {fmt, saveCsv, useWindowSize} from "../utils";
import {TextH2, } from "./AboutPage";
import Button from "@mui/material/Button";
import {Link, useLocation} from "react-router-dom";
import {useCodesetIds, } from '../state/AppState';

export function BundleReport({bundle}) {
  // can get here from ViewBundleReportSelector
  if (!bundle) {
    const location = useLocation();
    const queryParams = new URLSearchParams(location.search);
    bundle = queryParams.get('bundle');
  }

  let [data, setData] = useState(null);
  const dataGetter = useDataGetter();

  const filename = `bundle-report-${bundle.replaceAll(' ', '_')}`;

  useEffect(() => {
    (async () => {
      if (data) {
        return;
      }
      try {
        // const response = await axios.get("https://api.example.com/data");
        const rows = await dataGetter.axiosCall(`bundle-report?bundle=${bundle}&as_json=true`, {sendAlert: false, });
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
      sortable: true,
    }));

    data = sortBy(data, row => row.concept_set_name);

    columns.push({
      name: 'link',
      selector: row => `/cset-comparison?codeset_ids=${row.codeset_id}`,
      format: row => <Link to={`/cset-comparison?codeset_ids=${row.codeset_id}`}>view</Link>,
    });
  }

  console.log({columns, data});
  return (
    <div>
      <TextH2>
        Downloading {bundle} concept sets to <samp style={{backgroundColor: '#CCC'}}>{filename}.csv</samp> in your downloads folder.
      </TextH2>
      <DataTable
          data={data || []}
          columns={columns}
          // defaultSortFieldId="concept_set_name" // not working. don't know why
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
}

export function N3CRecommended() {
  return <BundleReport bundle="N3C Recommended" />;
}

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
  const [codeset_ids, codesetIdsDispatch] = useCodesetIds();
  // const [compareOpt, compareOptDispatch] = useCompareOpt();

  useEffect(() => {
    (async () => {
      if (data) {
        return;
      }
      try {
        const rows = await dataGetter.fetchAndCacheItems(dataGetter.apiCalls.n3c_comparison_rpt);
        let concept_ids = uniq(flatten(rows.map(row => [...(row.added), ...(row.removed)])).map(d => d.concept_id));
        const concepts = await dataGetter.fetchAndCacheItems(dataGetter.apiCalls.concepts, concept_ids);
        setData({rows, concepts});
      } catch (error) {
        console.error("Error fetching data:", error);
      }
    })();
  });

  if (!data) {
    return <div>Loading...</div>;
  }
  let {rows, concepts} = data
  function tbl(tblConcepts) {
    return (
        <table id="n3ccompdiff"><tbody>{
          sortBy(tblConcepts, ['standard_concept', 'concept_name']).map((c,i) => {
            const pr = isEmpty(c.replacements) ? null : (
              <td>Poss replacements: {
                c.replacements.map(r => (
                    `${r.rels.join(
                        ',')}: ${r.concept_id} ${r.concept_name} ${r.standard_concept} ${r.vocabulary_id} ${r.concept_class_id}`
                )).join(', ')
              }</td>);
            return (
                <tr key={i}>
                  <td>{c.concept_id}</td>
                  <td>{c.name}</td>
                  <td><i>{c.std === 'S' ? 'Standard' : c.std === 'C'
                      ? 'Classification'
                      : 'Non-standard'}</i></td>
                  <td>{c.voc}</td>
                  <td>{c.cls}</td>
                  {pr}
                </tr>);
          })
        }</tbody>
        </table>
    )
  }

  function DiffList({data: row}) {
    console.log({row});
    const removed = isEmpty(row.removed) ? null : <span><b>Removed:</b>{tbl(
        row.removed)}</span>;
    const added = isEmpty(row.added) ? null : <span><b>Added:</b>{tbl(
        row.added)}</span>;
    return (
        <div style={{margin: 10,}}>
          {removed}
          {added}
        </div>
    );
  }

  let columns;
  columns = [
    {grow: 4, sortable: true, name: "Name", selector: row => row.name},
    {grow: 2, sortable: true, name: "Author", selector: row => row.author},
    {grow: 3, sortable: true, name: "Orig", selector: row => row.cset_1, wrap: true},
    {grow: 3, sortable: true, name: "New", selector: row => row.cset_2, wrap: true},
    {grow: 2, name: "Compare", selector: row => (
          <Button
              to={`/cset-comparison?codeset_ids=${row.codeset_id_1}&codeset_ids=${row.codeset_id_2}`}
              // + `&compare_opt=compare-precalculated`
              component={Link}
              style={{margin: '7px', textTransform: 'none'}}
          >
            {row.removed.length} removed, {row.added.length} added
            {/*orig {String.fromCodePoint(0x2192)} new*/}
          </Button>

      )},
  ]
  console.log({columns, data});
  return (
      <div>
        <DataTable
            data={rows || []}
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
