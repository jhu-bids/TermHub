import React, {useState, useEffect} from 'react';
import DataTable, {createTheme} from "react-data-table-component";
import {styles} from "./CsetComparisonPage";

import {useDataGetter, DataGetter} from "../state/DataGetter";
import {sum} from "lodash";
import {setColDefDimensions} from "./dataTableUtils";
import {useWindowSize} from "./utils";

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
    name: "Concept name",
    selector: (row) => row.concept_name,
    sortable: true,
  },
  {
    selector: row => row.domain_id,
    name: "Domain",
    sortable: true,
    maxWidth: 100,
  },
  {
    selector: row => row.vocabulary_id,
    name: "Vocabulary",
    sortable: true,
    maxWidth: 100,
  },
  {
    selector: row => row.concept_class_id,
    name: "Class",
    sortable: true,
    maxWidth: 160,
  },
  {
    selector: row => row.standard_concept,
    name: "Std",
    sortable: true,
    width: 30,
  },
  {
    selector: row => row.total_cnt,
    format: row => row.total_cnt.toLocaleString(),
    name: "Record count",
    sortable: true,
    right: true,
    width: 100,
  },
  {
    selector: row => row.distinct_person_cnt,
    format: row => (parseInt(row.distinct_person_cnt) || row.distinct_person_cnt).toLocaleString(),
    name: "Distinct person count",
    sortable: true,
    right: true,
    width: 100,
  },
];
function getColDefs(windowSize) {
  let coldefs = columns.map(d => ({...d}));
  const totalWidthOfOthers = sum(coldefs.map(d => d.width || d.maxWidth));
  coldefs[0].width = // Math.min(totalWidthOfOthers * 1.5,
      windowSize[0] - totalWidthOfOthers - 30; // not sure why it's different from CsetComparisonPage.js where it's -3
// coldefs.forEach(d => {delete d.width; d.flexGrow=1;})
// coldefs[0].grow = 5;
// delete coldefs[0].width;
  coldefs = setColDefDimensions({coldefs, windowSize});
  return coldefs;
}

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
  const windowSize = useWindowSize();

  // this effect will be fired every time searchText changes
  React.useEffect(() => {
    (async () => {
      // setting min lenght for searchText
      if (searchText.length >= 3) {
        // updating the ref variable with the current searchText
        lastRequest.current = searchText;
        const r = await dataGetter.fetchAndCacheItems(dataGetter.apiCalls.concept_search, searchText)
        if (lastRequest.current === searchText) {
          // console.log("response is valid!", r);
          setConceptIds(r);
        } else {
          // console.log("discarding api response", searchText, lastRequest.current);
        }
      }
    })();
  }, [searchText]);

  const paddingLeft = 100, paddingRight = 100;
  const padding = paddingLeft + paddingRight;
  const divWidth = Math.min(windowSize[0], 1300) - padding;
  return (
    <div style={{paddingLeft, paddingRight, width: divWidth}}>
      <h1>Concept Search</h1>
      <input style={{width: 350}} type="text" placeholder="match characters in concept name"
             onChange={(e) => setSearchText(e.target.value)}
             value={searchText}
             autoFocus={true}
      />{'\u00A0'}{'\u00A0'}{'\u00A0'}{concept_ids.length ? concept_ids.length.toLocaleString() + ' concept_ids' : ""}
      <hr/>
      <ConceptTable concept_ids={concept_ids} divWidth={divWidth}/>
    </div>
  );
}

function ConceptTable(props) {
  let {concept_ids, divWidth} = props;
  const dataGetter = useDataGetter();
  const [concepts, setConcepts] = useState([]);
  const [loading, setLoading] = useState(false);
  const totalRows = concept_ids.length;
  const [perPage, setPerPage] = useState(30);
  let customStyles = styles(1);
  customStyles.cells.style.padding= '0px 5px 0px 5px';

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
  console.log(customStyles);
  return <DataTable
            customStyles={customStyles}
            // title="Users"
            columns={getColDefs([divWidth, 1234])} // need an array here but don't need the height
            data={concepts}
            progressPending={loading}
            pagination
            paginationServer
            paginationTotalRows={totalRows}
            onChangeRowsPerPage={handlePerRowsChange}
            onChangePage={handlePageChange}
            dense
            className="comparison-data-table"
            // theme="light"

            />;
}