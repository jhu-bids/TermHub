import React, {useState, useEffect} from 'react';
import DataTable, {createTheme} from "react-data-table-component";

import {useDataGetter, DataGetter} from "../state/DataGetter";

interface Concept {
  readonly concept_id: number;
  readonly concept_name: string;
  readonly domain_id: string;
  readonly vocabulary_id: string;
  readonly concept_class_id: string;
  readonly standard_concept: string;
  readonly concept_code: string;
  readonly invalid_reason: string;
  readonly domain_cnt: number;
  readonly domain: string;
  readonly total_cnt: number;
  readonly distinct_person_cnt: string;
}

const columns = [
  {
    name: "Concept Name",
    selector: (row) => row.concept_name,
    sortable: true,
    width: 200,
  },
  {
    selector: row => row.domain_id,
    name: "Domain",
    sortable: true,
    width: 200,
  },
  {
    selector: row => row.total_cnt,
    name: "Total Count",
    sortable: true,
    width: 100,
  },
  {
    selector: row => row.distinct_person_cnt,
    name: "Distinct Person Count",
    sortable: true,
    width: 100,
  },
];

export function AddConcepts() {
  return <ConceptStringSearch />;

}
// from https://stackoverflow.com/a/66167322/1368860
function ConceptStringSearch() {
  const dataGetter: DataGetter = useDataGetter();
  let concepts: Concept[] = [];
  const [searchText, setSearchText] = React.useState("");
  const [concept_ids, setConceptIds] = React.useState(concepts);
  const lastRequest = React.useRef(null);

  // this effect will be fired every time searchText changes
  React.useEffect(() => {
    (async () => {
      // setting min lenght for searchText
      if (searchText.length >= 3) {
        // updating the ref variable with the current searchText
        lastRequest.current = searchText;
        const r = await dataGetter.fetchAndCacheItems(dataGetter.apiCalls.concept_search, searchText)
        if (lastRequest.current === searchText) {
          console.log("response is valid!", r);
          setConceptIds(r);
        } else {
          console.log("discarding api response", searchText, lastRequest.current);
        }
      }
    })();
  }, [searchText]);

  return (
    <div className="App" style={{paddingLeft: 100}}>
      <h1>Concept Search</h1>
      <input style={{width: 300}} type="text" placeholder="match characters in concept name"
             onChange={(e) => setSearchText(e.target.value)}
             value={searchText}
             autoFocus={true}
      />{'\u00A0'}{'\u00A0'}{'\u00A0'}{concept_ids.length ? concept_ids.length.toLocaleString() + ' concept_ids' : ""}
      <ConceptTable concept_ids={concept_ids} />
    </div>
  );
}

function ConceptTable(props) {
  let {concept_ids} = props;
  const dataGetter = useDataGetter();
  const [concepts, setConcepts] = useState([]);
  const [loading, setLoading] = useState(false);
  const totalRows = concept_ids.length;
  const [perPage, setPerPage] = useState(10);

  const fetchConcepts = async page => {
    setLoading(true);
    let ids = concept_ids.slice(page - 1, perPage);
    let conceptLookup = await dataGetter.fetchAndCacheItems(dataGetter.apiCalls.concepts, ids);
    const _concepts = ids.map(id => conceptLookup[id]);
    setConcepts(_concepts);
    setLoading(false);
  };
  const handlePageChange = page => {
    fetchConcepts(page);
  };
  const handlePerRowsChange = async (newPerPage, page) => {
    setLoading(true);
    let ids = concept_ids.slice(page - 1, page - 1 + perPage);
    let conceptLookup = await dataGetter.fetchAndCacheItems(dataGetter.apiCalls.concepts, ids);
    const _concepts = ids.map(id => conceptLookup[id]);
    setConcepts(_concepts);
    setPerPage(newPerPage);
    setLoading(false);
  };
  useEffect(() => {
    fetchConcepts(1); // fetch page 1 of users
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [concept_ids]);
  console.log(concepts);
  return <DataTable
            title="Users"
            columns={columns}
            data={concepts}
            progressPending={loading}
            pagination
            paginationServer
            paginationTotalRows={totalRows}
            onChangeRowsPerPage={handlePerRowsChange}
            onChangePage={handlePageChange} />;
}