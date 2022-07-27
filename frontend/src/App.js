/* https://reactjs.org/docs/hooks-intro.html
https://mui.com/material-ui/react-list/
https://mui.com/material-ui/getting-started/usage/
https://github.com/mui/material-ui
*/
import React, {useState} from 'react';
// import logo from './logo.svg';
import './App.css';
import { Link, Outlet, useHref, useNavigate, useParams, useSearchParams, useLocation } from "react-router-dom";

import RRD from "react-router-dom";
// import Box from '@mui/joy/Box';
// import List from '@mui/joy/List';
// import ListItem from '@mui/joy/ListItem';
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

// might be useful to look at https://mui.com/material-ui/guides/composition/#link
// referred to by https://stackoverflow.com/questions/63216730/can-you-use-material-ui-link-with-react-router-dom-link

function App() {
  const [tabNum, setTabNum] = React.useState(0);
  let handleChange = (evt, tabnum) => {
    setTabNum(tabnum)
  }

  return (
    <div className="App">
      <nav
        style={{
          borderBottom: "solid 1px",
          paddingBottom: "1rem",
        }}
      >
        <Link style={{ display: "block", margin: "1rem 0" }} to={"/ontocall?path=objectTypes"} >
          objectTypes
        </Link>
        <Link style={{ display: "block", margin: "1rem 0" }} to={"/ontocall?path=objects/OMOPConceptSet"} >
          Concept sets
        </Link>
        <Tabs value={tabNum} onChange={handleChange} aria-label="nav tabs">
          <Tab label="Onto obj types" href="/ontocall?path=objectTypes" />
          <Tab label="Concept sets" href="/ontocall?path=objects/OMOPConceptSet" />
        </Tabs>
      </nav>
      {/* Outlet: Will render the results of whatever nested route has been clicked/activated. */}
      <Outlet />
    </div>
  );
}
function propIfExists(obj, prop) {
  return prop in obj ? obj[prop] : obj
}
function extractApiData(path, data) {
  if (path == 'objectTypes') {
    return objectTypesData(data)
  }
  if (path.startsWith('objects/OMOPConceptSet/')) {
    debugger
  }
  const possiblePropPathItems = ['data', 'json', 'data']
  const obj = possiblePropPathItems.reduce(propIfExists, data)
  let rows = obj.map(r=>propIfExists(r, 'properties'));
  return rows
}
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
function ConceptSet() {

}
function EnclaveOntoAPI() {
  const [searchParams, setSearchParams] = useSearchParams();
  function makeApiUrl() {
    return 'http://127.0.0.1:8000/ontocall?path=' + searchParams.get('path')
  }
  let [apiUrl, setApiUrl] = useState(makeApiUrl());
  const [rowCallback, setRowCallback] = useState(d=>d);
  const [enclaveData, setEnclaveData] = useState([]);
  let navigate = useNavigate();
  async function csetCallback(props) {
    let {rowData, colClicked} = props
    navigate(`/OMOPConceptSet/${rowData.codesetId}`)
    // setSearchParams({path:`objects/OMOPConceptSet/${rowData.codesetId}`})
  }

  React.useEffect(() => {
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

  console.log('rowCallback is', rowCallback)
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
