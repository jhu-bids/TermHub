import React, {useEffect, useState} from "react";
import {backend_url, useDataGetter} from "../state/DataGetter";
// import axios from "axios";
import {isEmpty, uniq, } from 'lodash';
import {fmt, saveCsv, mean, median} from "./utils";

export function UsageReport() {
    const dataGetter = useDataGetter();
    const [data, setData] = useState([]);
    useEffect(() => {
        (async () => {

            // let response = await axios(url);
            // await dataGetter.axiosCall(`usage`, {sendAlert: false, skipApiGroup: true});
            let url = backend_url('usage');
            let data = await dataGetter.fetchAndCacheItems(dataGetter.apiCalls.usage);
            console.log(data);
            setData(current => (data));
        })()
    }, []);
    if (!isEmpty(data)) {
        let csids_selections = data.map(d => d.codeset_ids).filter(d => !isEmpty(d));
        let csids_selections_uniq = uniq(csids_selections.map(d => d.join(',')));
        let csids_lengths = csids_selections.map(d => d.length);
        let tableRows = [
            { Measure: 'Log records', Value: data.length, Notes: ''},
            { Measure: 'Distinct IP addresses', Value: new Set(data.map(d => d.client)).size, Notes: ''},
            { Measure: 'Value set selections', Value: csids_selections.length, Notes: ''},
            { Measure: 'Unique value set selections', Value: csids_selections_uniq.length, Notes: ''},
            { Measure: 'Log records', Value: data.length,
                Notes: `backend server usage logs. Since we use caching to avoid redundant server
                        calls, these logs do not capture analysis of already-downloaded data. After
                        removing 3,600 log entries of testing or use by TermHub developers, the
                        remaining 9,400 records represent use by our target audiences`},
        ];
        // let csvRows = tableRows.map(row => ({ Statistic: row.stat, Value: row.value, }));
        let csvRows = tableRows.map(row => ({...row}));
        let csv = saveCsv(csvRows);
        return (
            <div>
                <pre>
                    {csv}
                </pre>

                <div className="table_component" role="region" tabIndex="0">
                    <table>
                        <thead>
                            <tr>
                                <th>Measure</th>
                                <th>Value</th>
                                <th>Notes</th>
                            </tr>
                        </thead>
                        <tbody>
                            {
                                tableRows.map((row, index) => {
                                    return (
                                        <tr key={index}>
                                            <td>{row.Measure}</td>
                                            <td>{fmt(row.Value)}</td>
                                            <td>{row.Notes}</td>
                                        </tr>
                                    );
                                })
                            }
                        </tbody>
                    </table>
                </div>

                <pre>{JSON.stringify(data.slice(0, 20), null, 2)}</pre>;
            </div>
        );
    }
    return <div>Usage Report</div>;
}