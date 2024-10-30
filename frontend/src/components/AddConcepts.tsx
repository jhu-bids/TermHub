import React, { useState, useEffect, useCallback, useRef, useMemo, } from 'react';
import DataTable, { createTheme } from 'react-data-table-component';
import { styles } from './CsetComparisonPage';

import { useDataGetter, DataGetter } from '../state/DataGetter';
import { sum, set, uniq, flatten, debounce, isEmpty, union, difference, intersection, } from 'lodash';
import { setColDefDimensions } from './dataTableUtils';
import { useWindowSize } from '../utils';
import { useCids, useCodesetIds } from '../state/AppState';
import { setOp } from '../utils';
import Button from '@mui/material/Button';
import { TextField } from '@mui/material';

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
        name: 'Concept name',
        selector: (row) => row.concept_name,
        sortable: true,
    },
    {
        name: 'Concept ID',
        selector: (row) => row.concept_id,
        sortable: true,
        maxWidth: 75,
    },
    {
        selector: row => row.domain_id,
        name: 'Domain',
        sortable: true,
        maxWidth: 100,
    },
    {
        selector: row => row.vocabulary_id,
        name: 'Vocabulary',
        sortable: true,
        maxWidth: 100,
    },
    {
        selector: row => row.concept_class_id,
        name: 'Class',
        sortable: true,
        maxWidth: 160,
    },
    {
        selector: row => row.standard_concept,
        name: 'Std',
        sortable: true,
        width: 30,
    },
    {
        selector: row => row.total_cnt,
        format: row => row.total_cnt.toLocaleString(),
        name: 'Record count',
        sortable: true,
        right: true,
        width: 100,
    },
    {
        selector: row => row.distinct_person_cnt,
        format: row => (parseInt(row.distinct_person_cnt) || row.distinct_person_cnt).toLocaleString(),
        name: 'Distinct person count',
        sortable: true,
        right: true,
        width: 100,
    },
];

function getColDefs(windowSize) {
    let coldefs = columns.map(d => ({ ...d }));
    const totalWidthOfOthers = sum(coldefs.map(d => d.width || d.maxWidth));
    coldefs[0].width = // Math.min(totalWidthOfOthers * 1.5,
        windowSize[0] - totalWidthOfOthers - 100; // not sure why it's different from CsetComparisonPage.js where it's -3
// coldefs.forEach(d => {delete d.width; d.flexGrow=1;})
// coldefs[0].grow = 5;
// delete coldefs[0].width;
    coldefs = setColDefDimensions({ coldefs, windowSize });
    return coldefs;
}

export function AddConcepts() {
    return <ConceptStringSearch/>;

}

// Create debounced function outside component to avoid recreating it
const debouncedSearch = debounce(async (
  searchText,
  dataGetter,
  signal,
  onResult
) => {
  try {
    const r = await dataGetter.fetchAndCacheItems(
      dataGetter.apiCalls.concept_search,
      searchText,
      { signal }
    );
    onResult(r);
  } catch (err) {
    if (err.name === 'AbortError') return;
    throw err;
  }
}, 700);

function useSearch(searchText, dataGetter) {
  const [foundConceptIds, setFoundConceptIds] = useState([]);

  useEffect(() => {
    if (searchText.length < 3) return;

    const controller = new AbortController();

    debouncedSearch(
      searchText,
      dataGetter,
      controller.signal,
      setFoundConceptIds
    );

    return () => {
      controller.abort();
      debouncedSearch.cancel();
    };
  }, [searchText, dataGetter]);

  return foundConceptIds;
}

// from https://stackoverflow.com/a/66167322/1368860
function ConceptStringSearch() {
    const dataGetter: DataGetter = useDataGetter();
    const [codeset_ids] = useCodesetIds();
    const [cids, cidsDispatch] = useCids();
    const [searchText, setSearchText] = React.useState('');
    const c: number[] = [];
    const [have_concept_ids, setHaveConceptIds] = React.useState(c);
    // const [found_concept_ids, setFoundConceptIds] = React.useState(c);
    const lastRequest = React.useRef(null);
    const addCidsFieldRef = useRef(null);
    const windowSize = useWindowSize();

    const found_concept_ids = useSearch(searchText, dataGetter);
    // this effect will be fired every time searchText changes
    /* React.useEffect(() => {
        debounce(async () => {
            // setting min length for searchText
            // console.log(`processing search text: ${searchText}`);
            if (searchText.length >= 3) {
                // updating the ref variable with the current searchText
                lastRequest.current = searchText;
                const r = await dataGetter.fetchAndCacheItems(dataGetter.apiCalls.concept_search, searchText);
                if (lastRequest.current === searchText) {
                    setFoundConceptIds(r);
                } else {
                    // console.log("discarding api response", searchText, lastRequest.current);
                }
            }
        }, 700)();
    }, [searchText]); */

    React.useEffect(() => {
        (async () => {
            // csmi for these codeset_ids should already be cached
            const csmi: {
                [key: number]: Concept
            } = await dataGetter.fetchAndCacheItems(dataGetter.apiCalls.cset_members_items, codeset_ids);
            let h = uniq(flatten(Object.values(csmi).map(d => Object.values(d).map(d => d.concept_id))));
            // h = setOp('union', h, cids); // really slow with big set of concepts
            //  replicate: http://localhost:3000/add-concepts?codeset_ids=265005208&codeset_ids=246957665&codeset_ids=894796651&codeset_ids=588335259
            h = union(h, cids);
            setHaveConceptIds(h);
        })();
    }, [codeset_ids, cids]);

    const paddingLeft = 100, paddingRight = 100;
    const padding = paddingLeft + paddingRight;
    const divWidth = Math.min(windowSize[0], 1900) - padding;
    const displayConceptIds = difference(found_concept_ids, have_concept_ids);
    const hiddenMatches = intersection(found_concept_ids, have_concept_ids);
    return (
        <div style={{ paddingLeft, paddingRight, width: divWidth }}>
            <h1>Concept Search</h1>
            <input style={{ width: 350 }} type="text" placeholder="match characters in concept name"
                   onChange={(e) => setSearchText(e.target.value)}
                   value={searchText}
                   autoFocus={true}
            />
            {'\u00A0'}{'\u00A0'}{'\u00A0'}{found_concept_ids.length ? found_concept_ids.length.toLocaleString() + ` concepts match "${searchText}"` : ''}
            {'\u00A0'}{hiddenMatches.length ? hiddenMatches.length.toLocaleString() + ' already included and not listed' : ''}
            <TextField fullWidth multiline
                       style={{marginTop: 15, }}
                       label={"Enter concept_ids to add separated by spaces, commas, or newlines and click button below"}
                       inputRef={addCidsFieldRef}
                       // onChange={handleCidsTextChange}
                       // defaultValue={codeset_ids.join(', ')}
            >
            </TextField>
            <Button
                style={{margin: '7px', textTransform: 'none'}}
                variant={"contained"}
                onClick={(evt) => {
                    const cidsText = addCidsFieldRef.current.value;
                    const cids = cidsText.split(/[,\s]+/).filter(d=>d.length);
                    cidsDispatch({ type: 'add', cids: cids, });
                    addCidsFieldRef.current.value = '';
                    addCidsFieldRef.current.style.height = 'auto';
                    addCidsFieldRef.current.style.overflow = 'hidden';

                }}
            >
                Add concept_ids
            </Button>
            <hr/>
            <FoundConceptTable displayConceptIds={displayConceptIds} divWidth={divWidth}/>
            <AddedCidsConceptTable divWidth={divWidth}/>
        </div>
    );
}

function FoundConceptTable(props) {
    let { displayConceptIds, divWidth } = props;
    const [cids, cidsDispatch] = useCids();
    const dataGetter = useDataGetter();
    const c = [];
    const [concepts, setConcepts] = useState(c);
    const [loading, setLoading] = useState(false);
    const totalRows = displayConceptIds.length;
    const [perPage, setPerPage] = useState(30);

    let customStyles = styles(1);
    set(customStyles, 'cells.style.padding', '0px 5px 0px 5px');

    const fetchConcepts = async (page, rowsPerPage) => {
        setLoading(true);
        const startIndex = (page - 1) * rowsPerPage;
        const endIndex = startIndex + rowsPerPage;
        let ids = displayConceptIds.slice(startIndex, endIndex);
        let conceptLookup = await dataGetter.fetchAndCacheItems(dataGetter.apiCalls.concepts, ids);
        const _concepts = ids.map(id => conceptLookup[id]);
        setConcepts(_concepts);
        setLoading(false);
    };

    const handlePageChange = page => {
        fetchConcepts(page, perPage);
    };

    const handlePerRowsChange = async (newPerPage, page) => {
        setPerPage(newPerPage);
        fetchConcepts(page, newPerPage);
    };

    useEffect(() => {
        fetchConcepts(1, perPage);
    }, [displayConceptIds]);

    if (isEmpty(displayConceptIds)) {
        return null;
    }

    const handleSelectedRows = ({ selectedRows }) => {
        cidsDispatch({ type: 'add', cids: selectedRows.map(row => row.concept_id)});
    };

    return <DataTable
        customStyles={customStyles}
        columns={getColDefs([divWidth, 1234])}
        data={concepts}
        selectableRows
        onSelectedRowsChange={handleSelectedRows}
        progressPending={loading}
        pagination
        paginationServer
        paginationTotalRows={totalRows}
        paginationRowsPerPageOptions={[20, 50, 100]}
        onChangeRowsPerPage={handlePerRowsChange}
        onChangePage={handlePageChange}
        dense
        className="comparison-data-table"
    />;
}

function AddedCidsConceptTable(props) {
    const { divWidth } = props;
    const [selectedRows, setSelectedRows] = useState([]);
    const [toggleCleared, setToggleCleared] = useState(false);
    const [cids, cidsDispatch] = useCids();
    const dataGetter = useDataGetter();
    const [concepts, setConcepts] = useState([]);
    const [loading, setLoading] = useState(false);
    const totalRows = cids.length;
    const [perPage, setPerPage] = useState(30);
    const [page, setPage] = useState(1);

    let customStyles = styles(1);
    set(customStyles, 'cells.style.padding', '0px 5px 0px 5px');

    const fetchConcepts = async (pageNumber, rowsPerPage) => {
        setLoading(true);
        const startIndex = (pageNumber - 1) * rowsPerPage;
        const endIndex = startIndex + rowsPerPage;
        let ids = cids.slice(startIndex, endIndex);
        let conceptLookup = await dataGetter.fetchAndCacheItems(dataGetter.apiCalls.concepts, ids);
        const _concepts = ids.map(id => conceptLookup[id]);
        setConcepts(_concepts);
        setLoading(false);
    };

    const handlePageChange = (pageNumber) => {
        setPage(pageNumber);
        fetchConcepts(pageNumber, perPage);
    };

    const handlePerRowsChange = async (newPerPage, pageNumber) => {
        setPerPage(newPerPage);
        setPage(pageNumber);
        fetchConcepts(pageNumber, newPerPage);
    };

    useEffect(() => {
        fetchConcepts(1, perPage);
    }, [cids, perPage]);

    const handleRowSelected = useCallback(state => {
        setSelectedRows(state.selectedRows);
    }, []);

    const contextActions = useMemo(() => {
        const handleDelete = () => {
            if (window.confirm(`Are you sure you want to delete:\r ${selectedRows.map(r => r.concept_name)}?`)) {
                setToggleCleared(!toggleCleared);
                cidsDispatch({ type: 'delete', cids: selectedRows.map(row => row.concept_id)});
            }
        };
        return (
            <Button key="delete" onClick={handleDelete} style={{ backgroundColor: 'red' }}>
                Delete
            </Button>
        );
    }, [cids, selectedRows, toggleCleared, cidsDispatch]);

    return (
        <DataTable
            title="Remove added concepts"
            customStyles={customStyles}
            columns={getColDefs([divWidth, 1234])}
            data={concepts}
            selectableRows
            contextActions={contextActions}
            onSelectedRowsChange={handleRowSelected}
            clearSelectedRows={toggleCleared}
            progressPending={loading}
            pagination
            paginationServer
            paginationTotalRows={totalRows}
            paginationPerPage={perPage}
            paginationDefaultPage={1}
            paginationRowsPerPageOptions={[10, 20, 30, 50, 100]}
            onChangePage={handlePageChange}
            onChangeRowsPerPage={handlePerRowsChange}
            dense
            className="comparison-data-table"
        />
    );
}

function AddedCidsConceptTableHOLD(props) {
    let { divWidth } = props;
    const [selectedRows, setSelectedRows] = React.useState([]);
    const [toggleCleared, setToggleCleared] = React.useState(false);
    const [cids, cidsDispatch] = useCids();
    const dataGetter = useDataGetter();
    const c: Concept[] = [];
    const [concepts, setConcepts] = useState(c);
    const [loading, setLoading] = useState(false);
    const totalRows = cids.length;
    const [perPage, setPerPage] = useState(30);
    let customStyles = styles(1);
    set(customStyles, 'cells.style.padding', '0px 5px 0px 5px');

    const fetchConcepts = async page => {
        setLoading(true);
        let ids = cids.slice(page - 1, perPage);
        let conceptLookup = await dataGetter.fetchAndCacheItems(dataGetter.apiCalls.concepts, ids);
        const _concepts = ids.map(id => conceptLookup[id]);
        setConcepts(_concepts);
        setLoading(false);
    };
    const handlePageChange = page => {
        console.log("handling page change");
        fetchConcepts(page);
    };
    const handlePerRowsChange = async (newPerPage, page) => {
        console.log("handling perRows change");
        setLoading(true);
        let ids = cids.slice(page - 1, page - 1 + perPage);
        let conceptLookup = await dataGetter.fetchAndCacheItems(dataGetter.apiCalls.concepts, ids);
        const _concepts = ids.map(id => conceptLookup[id]);
        setConcepts(_concepts);
        setPerPage(newPerPage);
        setLoading(false);
    };
    useEffect(() => {
        fetchConcepts(1); // fetch page 1 of users
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [cids]);

    const handleRowSelected = React.useCallback(state => {
        setSelectedRows(state.selectedRows);
    }, []);
    const contextActions = React.useMemo(() => {
        const handleDelete = () => {
            // eslint-disable-next-line no-alert
            if (window.confirm(`Are you sure you want to delete:\r ${selectedRows.map(r => r.concept_name)}?`)) {
                setToggleCleared(!toggleCleared);
                cidsDispatch({ type: 'delete', cids: selectedRows.map(row => row.concept_id)});
            }
        };
        return (
            <Button key="delete" onClick={handleDelete} style={{ backgroundColor: 'red' }}>
                Delete
            </Button>);
    }, [cids, selectedRows, toggleCleared]);

    return <DataTable title="Remove added concepts"
                      customStyles={customStyles}
                      columns={getColDefs([divWidth, 1234])} // need an array here but don't need the height
                      data={concepts}
                      selectableRows
                      contextActions={contextActions}
                      onSelectedRowsChange={handleRowSelected}
                      clearSelectedRows={toggleCleared}
                      progressPending={loading}
                      dense
                      className="comparison-data-table"
                      pagination/>;
}

/*
function TestingSelectionExample() {
  const [selectedRows, setSelectedRows] = React.useState([]);
  const [toggleCleared, setToggleCleared] = React.useState(true);
  const [data, setData] = React.useState(junkData);
  const handleRowSelected = React.useCallback(state => {
    setSelectedRows(state.selectedRows);
  }, []);
  const contextActions = React.useMemo(() => {
    const handleDelete = () => {
      // eslint-disable-next-line no-alert
      if (window.confirm(`Are you sure you want to delete:\r ${selectedRows.map(r => r.concept_id)}?`)) {
        setToggleCleared(!toggleCleared);
        setData(differenceBy(data, selectedRows, 'title'));
      }
    };
    return <Button key="delete" onClick={handleDelete} style={{
      backgroundColor: 'red'
    }} >
      Delete
    </Button>;
  }, [data, selectedRows, toggleCleared]);
  return <DataTable title="Desserts" columns={columns} data={data} selectableRows contextActions={contextActions} onSelectedRowsChange={handleRowSelected} clearSelectedRows={toggleCleared} pagination />;
}
let junkData = [
    {
        "concept_id": 442793,
        "concept_name": "Complication due to diabetes mellitus",
        "domain_id": "Condition",
        "vocabulary_id": "SNOMED",
        "concept_class_id": "Disorder",
        "standard_concept": "S",
        "concept_code": "74627003",
        "invalid_reason": null,
        "domain_cnt": 1,
        "domain": "condition_occurrence",
        "total_cnt": 6474230,
        "distinct_person_cnt": "692384",
        "selected": true
    },
    {
        "concept_id": 4235703,
        "concept_name": "Asthma management",
        "domain_id": "Observation",
        "vocabulary_id": "SNOMED",
        "concept_class_id": "Procedure",
        "standard_concept": "S",
        "concept_code": "406162001",
        "invalid_reason": null,
        "domain_cnt": 1,
        "domain": "observation",
        "total_cnt": 50526,
        "distinct_person_cnt": "8725",
        "selected": true
    },
    {
        "concept_id": 443731,
        "concept_name": "Renal disorder due to type 2 diabetes mellitus",
        "domain_id": "Condition",
        "vocabulary_id": "SNOMED",
        "concept_class_id": "Disorder",
        "standard_concept": "S",
        "concept_code": "420279001",
        "invalid_reason": null,
        "domain_cnt": 1,
        "domain": "condition_occurrence",
        "total_cnt": 3001400,
        "distinct_person_cnt": "277119",
        "selected": true
    },
    {
        "concept_id": 42529247,
        "concept_name": "How often did your asthma symptoms (wheezing, coughing, shortness of breath, chest tightness or pain) wake you up at night or earlier than usual in the morning during the past 4 weeks [ACT]",
        "domain_id": "Observation",
        "vocabulary_id": "LOINC",
        "concept_class_id": "Survey",
        "standard_concept": "S",
        "concept_code": "82671-9",
        "invalid_reason": null,
        "domain_cnt": 1,
        "domain": "observation",
        "total_cnt": 54500,
        "distinct_person_cnt": "9397",
        "selected": true
    },
    {
        "concept_id": 316577,
        "concept_name": "Poisoning by antiasthmatic",
        "domain_id": "Condition",
        "vocabulary_id": "SNOMED",
        "concept_class_id": "Disorder",
        "standard_concept": "S",
        "concept_code": "2935001",
        "invalid_reason": null,
        "domain_cnt": 1,
        "domain": "condition_occurrence",
        "total_cnt": 745,
        "distinct_person_cnt": "436",
        "selected": true
    }
]; */
