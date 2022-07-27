/* https://reactjs.org/docs/hooks-intro.html
https://mui.com/material-ui/react-list/
https://mui.com/material-ui/getting-started/usage/
https://github.com/mui/material-ui
*/
import React, {useState, useReducer, useEffect, useRef} from 'react';
// import logo from './logo.svg';
import './App.css';
import { Link, Outlet, useHref, useNavigate, useParams, useSearchParams, useLocation } from "react-router-dom";

import RRD from "react-router-dom";
// import Box from '@mui/joy/Box';
import List from '@mui/material/List';
import ListItem from '@mui/material/ListItem';
// import ListItemButton from '@mui/material/ListItemButton';
// import ListItemButton from '@mui/joy/ListItemButton';
// import ListItemText from '@mui/material/ListItemText';
// Issue: "ListItemText not defined" in JS console, and also my IDE highlights it in a different color here,
// ...yet when I ctrl+click "ListItemText", it opens up the source code.
// import ListItemText from '@mui/joy/ListItemText';

import Tabs from '@mui/material/Tabs';
// import LinkTab from '@mui/material/LinkTab';
import Tab from "@mui/material/Tab";
import Button from "@mui/material/Button";

import AGtest from "./aggrid-test";   // name should be changed because it's no longer just test code
//import MuiAppBar from "./MuiAppBar";

// might be useful to look at https://mui.com/material-ui/guides/composition/#link
// referred to by https://stackoverflow.com/questions/63216730/can-you-use-material-ui-link-with-react-router-dom-link

function App() {
  const [tabNum, setTabNum] = React.useState(0);
  let handleChange = (evt, tabnum) => {
    setTabNum(tabnum)
  }
  const links = [
    // [ 'Object types', useHref('/ontocall?path=objectTypes') ],
    [ 'Concept sets', useHref('/ontocall?path=objects/OMOPConceptSet') ],
  ]

  //return (<MuiAppBar />);
  return (
    <div className="App">
      {/*
      <Link style={{ display: "block", margin: "1rem 0" }} to={"/ontocall?path=objectTypes"} >
        objectTypes
      </Link>
      <Link style={{ display: "block", margin: "1rem 0" }} to={"/ontocall?path=objects/OMOPConceptSet"} >
        Concept sets
      </Link>
      */}
      <Tabs value={tabNum} onChange={handleChange} aria-label="nav tabs">
        {/* <Tab label="Onto obj types" to="/ontocall?path=objectTypes" component={Link} /> */}
        <Tab label="Concept sets" to="/ontocall?path=objects/OMOPConceptSet" component={Link}/>
      </Tabs>
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
function ConceptSet(props) {
  let { conceptId } = useParams();
  function makeApiUrl() {
    return `http://127.0.0.1:8000/ontocall?path=objects/OMOPConceptSet/${conceptId}`
  }
  const [apiUrl, setApiUrl] = useState(makeApiUrl());
  const { status, data } = useFetch(apiUrl);
  console.log({status, data})
  const csetPageUrl = 'https://unite.nih.gov/workspace/hubble/exploration/autosaved/5e0c2366-8fe8-40d4-ab9e-544cb7f5c4f0_8V2KrH9XeLXy_0'

  let ddata = [
    {field: 'Code set ID', value: data.codesetId},
    {field: 'Created at', value: data.createdAt},
    {field: 'Version title', value: data.conceptSetVersionTitle},
    {field: 'Is most recent version', value: data.isMostRecentVersion},
    {field: 'Intention', value: data.intention},
    {field: 'Update message', value: data.updateMessage},
    {field: 'Provenance', value: data.provenance},
    {field: 'Limitations', value: data.limitations},
  ]

  return (
      <div>
        <List>
          <ListItem><b>Foo:</b>&nbsp;Bar<br/></ListItem>
          {
            ddata.map(({field, value}) =>
              <ListItem key={field}><b>{field}:</b>&nbsp; {value}<br/></ListItem>
            )
          }
        </List>


        <h3><a href={csetPageUrl + '?objectId=' + data.rid}>Concept set browser page</a></h3>
        <pre>getting codesetId {conceptId} from <a href={apiUrl}>{apiUrl}</a></pre>
      </div>
  )
}



const useFetch = (url) => {
  const cache = useRef({});

  const initialState = {
    status: 'idle',
    error: null,
    data: [],
  };

  const [state, dispatch] = useReducer((state, action) => {
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

  useEffect(() => {
    let cancelRequest = false;
    if (!url) return;

    const fetchData = async () => {
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
          console.log('dispatched', data)
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

  useEffect(() => {
    // async function fetchData() {
      let path = searchParams.get('path')
      let rows = []
      if (!path) {
        return setEnclaveData(rows);
      }
      let rc = d=>d;
      if (path == 'objects/OMOPConceptSet') {
        rc = csetCallback
      }
      setRowCallback(()=>rc)
      setApiUrl(makeApiUrl())
      // let data = await fetch(apiUrl)
      let data = fetch(apiUrl)
          //.then(results => results.json())
          .then(results => {
            return results.json()
          })
          //.then(await (data => {   }))
          .then(data => {
            console.log(data)
            rows = extractApiData(path, data)
            setEnclaveData(rows);
            // return rows;
          });
      // return data
    // }
    // fetchData()
  }, [searchParams]); // <-- Have to pass in [] here!

  return (
      <div>
        <p>I am supposed to be the results of <a href={apiUrl}>{apiUrl}</a></p>
        <AGtest rowData={enclaveData} rowCallback={rowCallback}/>

        {/*
        <pre>
          {JSON.stringify(enclaveData, null, 2)}
        </pre>
        */}
      </div>
  );
}

/*
// TODO: Fix: Warning: React has detected a change in the order of Hooks called by N3CObjectTypes. This will lead to bugs and errors if not fixed. For more information, read the Rules of Hooks: https://reactjs.org/link/rules-of-hooks
// TODO: I think this is bad because considered nested function (call)
// TODO: I think I can fix by creating a state 'selectedN3CObject' instead of using onclick()
//  - set state in N3CObjectTypes
//  - get state in N3CObjectType
function N3CObjectType() {
  let params = useParams();
  let objectName = params.objType
  console.log(params)
  const [n3cObject, setN3cObject] = React.useState([]);

  React.useEffect(() => {
    //if (!Object.keys(objectName).length === 0) {
      let apicall = 'http://127.0.0.1:8000/ontocall?path=objectTypes/' + objectName
      console.log(`apicall:  ${apicall}`)
      fetch(apicall)
        .then(results => results.json())
        .then(data => {
          console.log(data)
          return setN3cObject(data);
        });
    //}
  }, []); // <-- Have to pass in [] here!

  return (
    <div>
      {n3cObject}
      <span>I am supposed to be an N3CObjectType {objectName}</span>
    </div>
  );
}

function displayN3CObjectType(typeName) {
  return () => <div>HERE IT IS: {typeName}</div>
}
*/
/*
// https://stackoverflow.com/questions/53219113/where-can-i-make-api-call-with-hooks-in-react
function N3CObjectTypes() {
  const [n3cObjects, setN3cObjects] = React.useState([]);

  React.useEffect(() => {
    fetch('http://127.0.0.1:8000/ontocall?path=objectTypes')
      .then(results => results.json())
      .then(data => {
        return setN3cObjects(data);
      });
  }, []); // <-- Have to pass in [] here!

  return (
    <div>
      <h3>wtf?</h3>
      <Outlet />
      {/*{!data ? 'Loading...' : JSON.stringify(data)}* /}
      <Box sx={{ width: '100%', maxWidth: 360, bgcolor: 'background.paper' }}>
        <nav aria-label="main mailbox folders">
          <List>
          {n3cObjects.map(x =>
            <ListItem key={x}>
              <ListItemButton variant="solid">
                <Link style={{ display: "block", margin: "1rem 0" }}
                      to={`/objTypes/${x}`}
                      key={x}
                >
                  {x}
                </Link>
                {/*<ListItemText key={x} primary={x} onClick={displayN3CObjectType(x)}/> * /}
              </ListItemButton>
            </ListItem>
          )}
          </List>
        </nav>
      </Box>
    </div>
  );
}
*/

export {App, EnclaveOntoAPI, ConceptSet};
