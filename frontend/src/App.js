/* https://reactjs.org/docs/hooks-intro.html
https://mui.com/material-ui/react-list/
https://mui.com/material-ui/getting-started/usage/
https://github.com/mui/material-ui
*/
import React from 'react';
// import logo from './logo.svg';
import './App.css';
import { Link, Outlet, useParams } from "react-router-dom";
import Box from '@mui/joy/Box';
import List from '@mui/joy/List';
import ListItem from '@mui/joy/ListItem';
// import ListItemButton from '@mui/material/ListItemButton';
import ListItemButton from '@mui/joy/ListItemButton';
import ListItemText from '@mui/material/ListItemText';


// Issue: "ListItemText not defined" in JS console, and also my IDE highlights it in a different color here,
// ...yet when I ctrl+click "ListItemText", it opens up the source code.
// import ListItemText from '@mui/joy/ListItemText';

function App() {
  return (
    <div className="App">
      <h2>whatever</h2>
      <nav
        style={{
          borderBottom: "solid 1px",
          paddingBottom: "1rem",
        }}
      >
        <Link to="/objTypes">ObjTypes</Link> |{" "}
        <Link to="/else">Something else</Link>
      </nav>
      <h3>outlet here:</h3>
      <Outlet />
    </div>
  );
}
//<N3CObjectType/>

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

/* https://stackoverflow.com/questions/53219113/where-can-i-make-api-call-with-hooks-in-react */
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
      {/*{!data ? 'Loading...' : JSON.stringify(data)}*/}
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
                {/*<ListItemText key={x} primary={x} onClick={displayN3CObjectType(x)}/> */}
              </ListItemButton>
            </ListItem>
          )}
          </List>
        </nav>
      </Box>
    </div>
  );
}

function Else() {
  return <h1>else?</h1>
}

export {App, N3CObjectTypes, N3CObjectType, Else};
