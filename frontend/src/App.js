/* https://reactjs.org/docs/hooks-intro.html
https://mui.com/material-ui/react-list/
https://mui.com/material-ui/getting-started/usage/
https://github.com/mui/material-ui
*/
import React from 'react';
// import logo from './logo.svg';
import './App.css';
import Box from '@mui/material/Box';
import List from '@mui/material/List';
import ListItem from '@mui/material/ListItem';
import ListItemButton from '@mui/material/ListItemButton';
// Issue: "ListItemText not defined" in JS console, and also my IDE highlights it in a different color here,
// ...yet when I ctrl+click "ListItemText", it opens up the source code.
import ListItemText from '@mui/material/ListItemText';


function App() {
  return (
    <div className="App">
      <N3CObjectTypes/>
      <N3CObjectType/>
    </div>
  );
}

// TODO: Fix: Warning: React has detected a change in the order of Hooks called by N3CObjectTypes. This will lead to bugs and errors if not fixed. For more information, read the Rules of Hooks: https://reactjs.org/link/rules-of-hooks
// TODO: I think this is bad because considered nested function (call)
// TODO: I think I can fix by creating a state 'selectedN3CObject' instead of using onclick()
//  - set state in N3CObjectTypes
//  - get state in N3CObjectType
function N3CObjectType(objectName) {
  const [n3cObject, setN3cObject] = React.useState([]);

  React.useEffect(() => {
    if (!Object.keys(objectName).length === 0) {
      fetch('http://127.0.0.1:8000/ontocall/objectTypes/' + objectName)
        .then(results => results.json())
        .then(data => setN3cObject(data));
    }
  }, []); // <-- Have to pass in [] here!

  return (
    <div>
        {/*{n3cObject}*/}
      <span>hello</span>
    </div>
  );
}

/* https://stackoverflow.com/questions/53219113/where-can-i-make-api-call-with-hooks-in-react */
function N3CObjectTypes() {
  const [n3cObjects, setN3cObjects] = React.useState([]);

  React.useEffect(() => {
    fetch('http://127.0.0.1:8000/ontocall/objectTypes')
      .then(results => results.json())
      .then(data => setN3cObjects(data));
  }, []); // <-- Have to pass in [] here!

  return (
    <div>
      {/*{!data ? 'Loading...' : JSON.stringify(data)}*/}
      <Box sx={{ width: '100%', maxWidth: 360, bgcolor: 'background.paper' }}>
        <nav aria-label="main mailbox folders">
          <List>
          {n3cObjects.map(x =>
            <ListItem disablePadding>
              <ListItemButton>
                {/* TODO: fix warning: Warning: Each child in a list should have a unique "key" prop.*/}
                <ListItemText key={x} primary={x}/>
                {/*<ListItemText key={x} primary={x} onClick={N3CObjectType(x)}/>*/}
              </ListItemButton>
            </ListItem>
          )}
          </List>
        </nav>
      </Box>
    </div>
  );
}

export default App;
