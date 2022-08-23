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

import {
    useQuery,
    useMutation,
    useQueryClient,
    QueryClient,
    QueryClientProvider,
} from '@tanstack/react-query'
import { ReactQueryDevtools } from '@tanstack/react-query-devtools'

// wanting to install react-query and axios and use those for data fetch/cache/etc.
//  is this helpful? https://blog.openreplay.com/fetching-and-updating-data-with-react-query
import axios from "axios";
const queryClient = new QueryClient()

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
const API_ROOT = 'http://127.0.0.1:8000'
const enclave_url = path => `${API_ROOT}/passthru?path=${path}`

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
    <QueryClientProvider client={queryClient}>
      <div className="App">
        <ReactQueryDevtools initialIsOpen={false} />
        <MuiAppBar/>
        {/* Outlet: Will render the results of whatever nested route has been clicked/activated. */}
        <Outlet />
      </div>
    </QueryClientProvider>
  );
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

function AboutPage() {
  return (
      <div>
        <p>TermHub is terminology management heaven.</p>
      </div>
  );
}


export {App, AboutPage, ConceptSets, ConceptSet, ConceptList};
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
