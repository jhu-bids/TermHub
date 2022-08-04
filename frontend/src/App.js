/* https://reactjs.org/docs/hooks-intro.html
https://mui.com/material-ui/react-list/
https://mui.com/material-ui/getting-started/usage/
https://github.com/mui/material-ui
https://stackoverflow.com/questions/53219113/where-can-i-make-api-call-with-hooks-in-react
might be useful to look at https://mui.com/material-ui/guides/composition/#link
referred to by https://stackoverflow.com/questions/63216730/can-you-use-material-ui-link-with-react-router-dom-link
*/
import React, {useState, useReducer, useEffect, useRef} from 'react';
import './App.css';
import { Link, Outlet, useHref, useNavigate, useParams, useSearchParams, useLocation } from "react-router-dom";
import MuiAppBar from "./MuiAppBar";
import List from '@mui/material/List';
import ListItem from '@mui/material/ListItem';
import AGtest from "./aggrid-test";   // name should be changed because it's no longer just test code
import RRD from "react-router-dom";

// wanting to install react-query and axios and use those for data fetch/cache/etc.
//  is this helpful? https://blog.openreplay.com/fetching-and-updating-data-with-react-query
import axios from "axios";

console.log(axios)
// import logo from './logo.svg';
// import Box from '@mui/joy/Box';
/*
when in doubt: https://reactjs.org/docs/hooks-reference.html and https://reactrouter.com/docs/en/v6

just found this: https://betterprogramming.pub/why-you-should-be-separating-your-server-cache-from-your-ui-state-1585a9ae8336
All the stuff below was from trying to find a solution to fetching data and using it across components

https://reactjs.org/docs/hooks-reference.html#useref
  React guarantees that setState function identity is stable and won’t change on re-renders.
  This is why it’s safe to omit from the useEffect or useCallback dependency list.

cool: https://reactjs.org/docs/hooks-reference.html#useref
  If the new state is computed using the previous state, you can pass
  a function to setState.The function will receive the previous
  value, and return an updated value.
     const [count, setCount] = useState(initialCount);
     <button onClick={() => setCount(initialCount)}>Reset</button>           // set with static value
     <button onClick={() => setCount(prevCount => prevCount - 1)}>-</button> // set with function

https://reactjs.org/docs/hooks-reference.html#conditionally-firing-an-effect
  The default behavior for effects is to fire the effect after every completed render.
  However, this may be overkill in some cases, like the subscription example from the
    previous section. We don’t need to create a new subscription on every update, only
    if the source prop has changed.... To implement this, pass a second argument to
    useEffect that is the array of values that the effect depends on.
OH!! Does that mean: without a dependency list, the useEffects function will run on every render?

*/

function App() {
  let location = useLocation();
  let navigate = useNavigate();
  useEffect(() => {
    if (location.pathname == '/') {
      navigate('/OMOPConceptSets')
    }
    console.log(location)
  }, [location])  // maybe not necessary to have location in dependencies
  return (
    <div className="App">
      <MuiAppBar/>
      {/* Outlet: Will render the results of whatever nested route has been clicked/activated. */}
      <Outlet />
    </div>
  );
}


/*
function getObjLinks() {
  // https://www.palantir.com/docs/foundry/api/ontology-resources/objects/list-linked-objects
  return <List>

    omop-concept-set-to-omop-concept
    omop-concept-set-version-item-to-omop-concept
    omop-concept-set-version-to-cset-version-info
    omop-concept-set-version-to-items
    omop-vocabulary-version-set-container-link
    vocab-version-set-version-link

    concept-change-version-link
    concept-set-bundle-item-omop-concept-set
    concept-set-review-concept-set
    concept-set-tag-to-concept-set-versions
    concept-set-version-change-acknowledgement-omop-concept-set
    concept-set-version-to-concept-set-container
    documentation-node-to-concept-set-version

    omop-concept-set-provenance
    omop-concept-set-container-omop-concept-domains
    omop-concept-set-to-omop-concept-domains
    omop-concept-set-container-to-concept-set-tag
    omop-concept-set-container-to-research-project
    omop-concept-set-to-research-project

    omop-concept-set-version-to-intended-domain-team
    set-ack-link
    concept-change-subscription
  </List>
}
*/

function ConceptSets(props) {

  return  <div>
            nothing here yet, except
            <pre>
              {JSON.stringify({props}, null, 4)}
            </pre>
          </div>
}

function ConceptSet(props) {
  let { conceptId } = useParams();
  function makeApiUrl() {
    // don't hard code the prefix!! and then
    return `http://127.0.0.1:8000/ontocall?path=objects/OMOPConceptSet/${conceptId}`
  }
  const [apiUrl, setApiUrl] = useState(makeApiUrl());
  const [displayData, setDisplayData] = useState([]);
  const { csetStatus, csetData } = useFetch(apiUrl);
  const { conceptsStatus, conceptsData } = useFetch(apiUrl + '/links/omopconcepts');
  // let conceptsApiUrl = `http://127.0.0.1:8000/ontocall?path=objects/OMOPConceptSet/${conceptId}/links/omopconcepts'`
  const csetPageUrl = 'https://unite.nih.gov/workspace/hubble/exploration/autosaved/5e0c2366-8fe8-40d4-ab9e-544cb7f5c4f0_8V2KrH9XeLXy_0'

  /* useEffect: 2 params: (1) what to do / function, (2) list of observables that trigger
  * If has only 1 param, only runs once component is mounted. */
  useEffect(() => {
    console.log({conceptsData, csetData, conceptsStatus, csetStatus, csetPageUrl})
    if (!csetData) {
      return;
    }
    setDisplayData([
      {field: 'Code set ID', value: csetData.codesetId},
      {field: 'Created at', value: csetData.createdAt},
      {field: 'Version title', value: csetData.conceptSetVersionTitle},
      {field: 'Is most recent version', value: csetData.isMostRecentVersion},
      {field: 'Intention', value: csetData.intention},
      {field: 'Update message', value: csetData.updateMessage},
      {field: 'Provenance', value: csetData.provenance},
      {field: 'Limitations', value: csetData.limitations},
    ])
  }, [conceptsData, csetData, conceptsStatus, csetStatus, csetPageUrl]);

  return (
      <div>
        <List>
          <ListItem><b>Foo:</b>&nbsp;Bar<br/></ListItem>
          {
            displayData.map(({field, value}) =>
              <ListItem key={field}><b>{field}:</b>&nbsp; {value}<br/></ListItem>
            )
          }
        </List>
        <Outlet/>
        {/*<h3><a href={csetPageUrl + '?objectId=' + csetData.rid}>Concept set browser page</a></h3>*/}
        <pre>getting codesetId {conceptId} from <a href={apiUrl}>{apiUrl}</a></pre>
      </div>
  )
}
function ConceptList(props) {
  let {conceptId} = useParams();
  let params = useParams();
  return <div>
          <p>you want to see concepts for {conceptId}?</p>
          <pre>
            props:
            {JSON.stringify(props, null, 2)}
          </pre>
          <pre>
            params:
            {JSON.stringify(params, null, 2)}
          </pre>
        </div>
}


/* use*: Anything with 'use' in front is treated like a hook. A hook must be a component. Component can't be in global
 space. But if called from a component, we're good. That component can be the App component.*/
const useFetch = (url) => {
  const cache = useRef({});

  const initialState = {
    status: 'idle',
    error: null,
    data: [],
  };

  const [state, dispatch] = useReducer((state, action) => {
    console.log(action, state)
    switch (action.type) {
      case 'FETCHING':
        return { ...initialState, status: 'fetching' };
      case 'FETCHED':
        return { ...initialState, status: 'fetched', data: action.payload };
      case 'FETCH_ERROR':
        return { ...initialState, status: 'error', error: action.payload };
      default:
        return state;
    }
  }, initialState);

  /* useEffect: 2 params: (1) what to do / function, (2) list of observables that trigger
  * If has only 1 param, only runs once component is mounted. */
  useEffect(() => {
    let cancelRequest = false;
    if (!url) return;

    const fetchData = async () => {
      console.log(`about to fetch ${url}`)
      dispatch({ type: 'FETCHING' });
      if (cache.current[url]) {
        const data = cache.current[url];
        dispatch({ type: 'FETCHED', payload: data });
      } else {
        try {
          const response = await fetch(url);
          const data = await response.json();
          cache.current[url] = data;
          if (cancelRequest) return;
          dispatch({ type: 'FETCHED', payload: data });
          // console.log('dispatched', data)
        } catch (error) {
          if (cancelRequest) return;
          dispatch({ type: 'FETCH_ERROR', payload: error.message });
        }
      }
    };

    fetchData();

    return function cleanup() {
      cancelRequest = true;
    };
  }, [url]);

  console.log('useFetch returning', state )
  return state
};


function propIfExists(obj, prop) {
  return prop in obj ? obj[prop] : obj
}


function extractApiData(path, data) {
  /*
  if (path == 'objectTypes') {
    return objectTypesData(data)
  }
  */
  if (path.startsWith('objects/OMOPConceptSet/')) {
    debugger
  }
  const possiblePropPathItems = ['data', 'json', 'data']
  const obj = possiblePropPathItems.reduce(propIfExists, data)
  let rows = obj.map(r=>propIfExists(r, 'properties'));
  return rows
}


/*
function objectTypesData(data) {
  const someObjTypePropertiesHaveDesc = data.some(d=>Object.entries(d.properties).some(d=>d.description))
  // console.log(data.map(d=>Object.entries(d.properties).map(p=>`${p[0]}(${p[1].baseType})`).join(', ')).join('\n\n'))
  if (someObjTypePropertiesHaveDesc) {
    console.log('someObjTypePropertiesHaveDesc!!!!!')
  }
  let rows = data.map(d => ({
    apiName: d.apiName,
    description: d.description,
    primaryKey: d.primaryKey.join(','),
    properties: Object.keys(d.properties).join(', '),
  }))
  return rows
}
*/


function EnclaveOntoAPI() {
  const [searchParams, setSearchParams] = useSearchParams();
  function makeApiUrl() {
    return 'http://127.0.0.1:8000/ontocall?path=' + searchParams.get('path')
  }
  const [apiUrl, setApiUrl] = useState(makeApiUrl());
  const [rowCallback, setRowCallback] = useState(d=>d);
  const [enclaveData, setEnclaveData] = useState([]);
  let navigate = useNavigate();

  async function csetCallback(props) {
    let {rowData, colClicked} = props
    navigate(`/OMOPConceptSet/${rowData.codesetId}`)
    // setSearchParams({path:`objects/OMOPConceptSet/${rowData.codesetId}`})
  }

  /* useEffect: 2 params: (1) what to do / function, (2) list of observables that trigger
  * If has only 1 param, only runs once component is mounted. */
  useEffect(() => {
    // async function fetchData() {
      let path = searchParams.get('path')
      let rows = []
      if (!path) {
        return setEnclaveData(rows);
      }
      let rc = d=>d;
      if (path === 'objects/OMOPConceptSet') {
        rc = csetCallback
      }
      setRowCallback(()=>rc)
      setApiUrl(makeApiUrl())
      let data = fetch(apiUrl)
          .then(results => {
            return results.json()
          })
          .then(data => {
            // console.log(data);
            rows = extractApiData(path, data)
            setEnclaveData(rows);
          });
  }, [searchParams]);

  return (
      <div>
        <p>I am supposed to be the results of <a href={apiUrl}>{apiUrl}</a></p>
        <AGtest rowData={enclaveData} rowCallback={rowCallback}/>
      </div>
  );
}


function AboutPage() {
  return (
      <div>
        <p>TermHub is terminology management heaven.</p>
      </div>
  );
}


export {App, AboutPage, EnclaveOntoAPI, ConceptSets, ConceptSet, ConceptList};