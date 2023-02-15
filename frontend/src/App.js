/* https://reactjs.org/docs/hooks-intro.html
https://mui.com/material-ui/react-list/
https://mui.com/material-ui/getting-started/usage/
https://github.com/mui/material-ui
https://stackoverflow.com/questions/53219113/where-can-i-make-api-call-with-hooks-in-react
might be useful to look at https://mui.com/material-ui/guides/composition/#link
referred to by https://stackoverflow.com/questions/63216730/can-you-use-material-ui-link-with-react-router-dom-link
*/
import React, {} from 'react';
import './App.css';
import { // Link, useHref, useParams, BrowserRouter, redirect,
          Outlet, Navigate, useSearchParams, useLocation,
          createSearchParams, Routes, Route,} from "react-router-dom";
import MuiAppBar from "./MuiAppBar";
import Box from '@mui/material/Box';
import { // useMutation, useQueryClient, useQuery, useQueries,
          QueryClient,QueryClientProvider, } from '@tanstack/react-query'
import { keyBy, } from "lodash";
import { persistQueryClient, removeOldestQuery,} from '@tanstack/react-query-persist-client'
// import { createSyncStoragePersister } from '@tanstack/query-sync-storage-persister'
import { createWebStoragePersistor } from 'react-query/createWebStoragePersistor-experimental'
import { ReactQueryDevtools } from '@tanstack/react-query-devtools'
import {ConceptSetsPage, CsetComparisonPage} from "./Csets";
import {AboutPage} from "./AboutPage";
import {searchParamsToObj, updateSearchParams, backend_url, useDataWidget, clearSearchParams, } from "./utils";
import {UploadCsvPage} from "./UploadCsv";
import {DownloadJSON} from "./DownloadJSON";
// import _ from "./supergroup/supergroup";
const SEARCH_PARAM_STATE_CONFIG = {
  scalars: ['editCodesetId', ],
  global_props_but_not_search_params: ['searchParams', 'setSearchParams'],
  serialize: ['csetEditState'],
}

// import logo from './logo.svg';
// import { useIsFetching } from '@tanstack/react-query' // https://tanstack.com/query/v4/docs/react/guides/background-fetching-indicators
// import dotenv from 'dotenv';
// import * as dotenv from 'dotenv' // see https://github.com/motdotla/dotenv#how-do-i-use-dotenv-with-import
// dotenv.config()
// const buf = Buffer.from('API_ROOT=api_root')
// const config = dotenv.parse(buf) // will return an object
// console.log(config)
// const API_ROOT = 'http://127.0.0.1:8000'

// const enclave_url = path => `${API_ROOT}/passthru?path=${path}`

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      cacheTime: 1000 * 60 * 60 * 24, // 24 hours
      // https://tanstack.com/query/v4/docs/guides/window-focus-refetching
      refetchOnWindowFocus: false,
      refetchOnmount: false,
      refetchOnReconnect: false,
      retry: false,
      staleTime: Infinity,
    },
  },
})

// const localStoragePersister = createSyncStoragePersister({ storage: window.localStorage })
const localStoragePersister = createWebStoragePersistor({ storage: window.localStorage })

persistQueryClient({
  queryClient,
  persister: localStoragePersister,
  retry: removeOldestQuery,
  maxAge: Infinity,
})
/*
  TODO: I've got some bad state stuff going on. Maybe violating this principle:
  For example, one rule is that you should not mutate an existing state object or ref object. Doing so
  may lead to unexpected behavior such as not triggering re-renders, triggering too many re-renders, and
  triggering partial re-renders (meaning some components re-render while others don't when they should).
    -- Kato, Daishi. Micro State Management with React Hooks (p. 32). Packt Publishing. Kindle Edition.
 */

/* structure is:
    <BrowserRouter>                     // from index.js root.render
        <QCProvider>                    // all descendent components will be able to call useQuery
            <QueryStringStateMgr>       // gets state (codeset_ids for now) from query string, passes down through props
                <DataContainer>         // fetches data from cr-hierarchy
                    <CsetsRoutes>       // where routes are defined (used to be directly in BrowserRouter in index.js
                        <App>           // all routes start with App
                            <Outlet/>   // this is where route content goes, all the other components
                        </App>
                    </CsetsRoutes>
                </DataContainer>
            <QueryStringStateMgr>
        </QCProvider />
    </BrowserRouter>
*/
function QCProvider() {
  return (
      // <React.StrictMode> // StrictMode helps assure code goodness by running everything twice, but it's annoying
        <QueryClientProvider client={queryClient}>
          <QueryStringStateMgr />
          <ReactQueryDevtools initialIsOpen={false} />
        </QueryClientProvider>
      // </React.StrictMode>
  );
}
function QueryStringStateMgr(props) {
  const location = useLocation();
  const [searchParams, setSearchParams ] = useSearchParams();
  // gets state (codeset_ids for now) from query string, passes down through props
  // const [codeset_ids, setCodeset_ids] = useState(sp.codeset_ids || []);
  const sp = searchParamsToObj(searchParams, setSearchParams);
  console.log({location, sp});
  const {codeset_ids=[], } = sp;
  // console.log(props);

  let globalProps = {...sp, searchParams, setSearchParams, }

  /*
  useEffect(() => {
    if (sp.codeset_ids && !isEqual(codeset_ids, sp.codeset_ids)) {
      setCodeset_ids(sp.codeset_ids);
    }
  }, [searchParams, codeset_ids, sp.codeset_ids]);
   */

  function changeCodesetIds(codeset_id, how) {
    // how = add | remove | toggle
    const included = codeset_ids.includes(codeset_id);
    let action = how;
    if (how === 'add' && included) return;
    if (how === 'remove' && !included) return;
    if (how === 'toggle') {
      action = included ? 'remove' : 'add';
    }
    if (action === 'add') {
      updateSearchParams({...globalProps, addProps: {codeset_ids: [...codeset_ids, codeset_id]}});
    } else if (action === 'remove') {
      if (!included) return;
      updateSearchParams({...globalProps, addProps: {codeset_ids: codeset_ids.filter(d => d !== codeset_id)}});
    } else {
      throw new Error('unrecognized action in changeCodesetIds: ' + JSON.stringify({how, codeset_id}));
    }
  }

  if (location.pathname === '/') {
    return <Navigate to='/OMOPConceptSets' />;
  }
  if (location.pathname === '/testing') {
    const test_codeset_ids = [400614256, 411456218, 419757429, 484619125, ];
    let params = createSearchParams({codeset_ids: test_codeset_ids});
    // setSearchParams(params);
    let url = '/cset-comparison?' + params;
    // return redirect(url); not exported even though it's in the docs
    return <Navigate to={url} replace={true} /* what does this do? */ />;
  }
  if(!globalProps.codeset_ids) {
    globalProps.codeset_ids = [];
  }
  return <DataContainer /* searchParams={searchParams}*/
                        // codeset_ids={codeset_ids}
                        changeCodesetIds={changeCodesetIds}
                        {...globalProps}
                        />;
}
function DataContainer(props) {
  let {codeset_ids, } = props;
  const all_csets_url = 'get-all-csets';
  const cset_data_url = 'cr-hierarchy?rec_format=flat&codeset_ids=' + codeset_ids.join('|');
  // /crconst cr_url = 'get-concept_relationships?codeset_ids=' + codeset_ids.join('|');

  /* TODO: This is a total disaster. do something with it */
  const [all_csets_widget, acprops] = useDataWidget("all_csets", all_csets_url);
  const [cset_data_widget, csprops] = useDataWidget(codeset_ids.join('|'), cset_data_url);
  // const [cr_widget, crprops] = useDataWidget('cr' + codeset_ids.join('|'), cr_url);
  const all_csets = acprops.data;
  const cset_data = csprops.data;
  // const concept_relationships = crprops.data;

  if (all_csets && cset_data /*&& concept_relationships*/) {
    cset_data.conceptLookup = keyBy(cset_data.concepts, 'concept_id');
    const csmiLookup = {};
    // cset_data.cset_members_items.map(mi => set(csmiLookup, [mi.codeset_id, mi.concept_id], mi));
    // the line above created the most bizarre crashing behavior -- fixed by replacing the lodash set with simple loop below
    cset_data.cset_members_items.forEach(mi => {
      csmiLookup[mi.codeset_id] = csmiLookup[mi.codeset_id] || {};
      csmiLookup[mi.codeset_id][mi.concept_id] = mi;
    });
    cset_data.csmiLookup = csmiLookup;
    // let cr = _.hierarchicalTableToTree(concept_relationships, 'concept_id_1', 'concept_id_2');
    // console.log(cr);

    console.log({props, cset_data, });
    return  <RoutesContainer {...props} all_csets={all_csets} cset_data={cset_data}/>
  }
  return (
      <Routes>
        <Route path="/" element={<App {...props} />}>
          <Route path="*"  element={
            <div>
              <h3>Waiting for data</h3>
              <Box sx={{ display: 'flex' }}>
                {all_csets_widget}
                {cset_data_widget}
                {/*cr_widget*/}
              </Box>
            </div>
          } />
        </Route>
      </Routes>
    );
}
function RoutesContainer(props) {
  console.log(window.props_w = props);
  return (
      <Routes>
        <Route path="/" element={<App {...props} />}>
          <Route path="cset-comparison" element={<CsetComparisonPage {...props} />} />
          <Route path="OMOPConceptSets" element={<ConceptSetsPage {...props}  />} />
          <Route path="about" element={<AboutPage {...props} />} />
          <Route path="upload-csv" element={<UploadCsvPage {...props} />} />
          <Route path="download-json" element={<DownloadJSON {...props} />} />
          {/* <Route path="OMOPConceptSet/:conceptId" element={<OldConceptSet />} /> */}
        </Route>
      </Routes>
  )
}
function App() {
  return (
      <div className="App">
        {/* <ReactQueryDevtools initialIsOpen={false} /> */ }
        <MuiAppBar/>
        {/* Outlet: Will render the results of whatever nested route has been clicked/activated. */}
        <Outlet/>
      </div>
  );
}

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

/*
function objectTypesData(data) {
  const someObjTypePropertiesHaveDesc = data.some(d=>Object.entries(d.properties).some(d=>d.description))
  // console.log(data.map(d=>Object.entries(d.properties).map(p=>`${p[0]}(${p[1].baseType})`).join(', ')).join('\n\n'))
  if (someObjTypePropertiesHaveDesc) {
    // console.log('someObjTypePropertiesHaveDesc!!!!!')
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

export {QCProvider, backend_url, SEARCH_PARAM_STATE_CONFIG, };

// TODO: @Siggie: Can we remove this comment or we need this list of links for ref still?
//       @Joe: we should move it to the individual concept set display component(s) as a
//             list of all the data we could be including
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
