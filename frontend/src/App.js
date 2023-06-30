/* https://reactjs.org/docs/hooks-intro.html
https://mui.com/material-ui/react-list/
https://mui.com/material-ui/getting-started/usage/
https://github.com/mui/material-ui
https://stackoverflow.com/questions/53219113/where-can-i-make-api-call-with-hooks-in-react
might be useful to look at https://mui.com/material-ui/guides/composition/#link
referred to by https://stackoverflow.com/questions/63216730/can-you-use-material-ui-link-with-react-router-dom-link
*/
import React, {useState, useEffect} from "react";
import "./App.css";
import {
  // Link, useHref, useParams, BrowserRouter, redirect,
  Outlet,
  Navigate,
  useSearchParams,
  useLocation,
  createSearchParams,
  Routes,
  Route,
} from "react-router-dom";
import { createTheme, ThemeProvider } from "@mui/material/styles";

import { QueryClient, QueryClientProvider, } from "@tanstack/react-query"; // useMutation, useQueryClient, useQuery, useQueries,

import { persistQueryClient } from '@tanstack/react-query-persist-client'
import { createSyncStoragePersister } from '@tanstack/query-sync-storage-persister'
import { ReactQueryDevtools } from '@tanstack/react-query-devtools'
import { compress, decompress } from 'lz-string'; // using in persister to handle big result sets

import { isEmpty } from "lodash";

import { ConceptSetsPage } from "./components/Csets";
import { CsetComparisonPage } from "./pages/CsetComparisonPage";
import { AboutPage } from "./pages/AboutPage";
import { ConceptGraph } from "./components/ConceptGraph";
import { AppStateProvider, searchParamsToObj, updateSearchParams,
          dataAccessor, ViewCurrentState, prefetch, } from "./components/State";
import { UploadCsvPage } from "./components/UploadCsv";
import { DownloadJSON } from "./components/DownloadJSON";
import MuiAppBar from "./components/MuiAppBar";

export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      cacheTime: 1000 * 60 * 60 * 24, // 24 hours
      // https://tanstack.com/query/v4/docs/guides/window-focus-refetching
      refetchOnWindowFocus: false,
      refetchOnmount: false,
      refetchOnReconnect: false,
      retry: false,
      // staleTime: Infinity,
      staleTime: 1000 * 60 * 60 * 24, // 24 hours
    },
  },
});

const persister = createSyncStoragePersister({
  storage: window.localStorage,
  serialize: data => compress(JSON.stringify(data)),
  deserialize: data => JSON.parse(decompress(data)),
});
persistQueryClient({
  queryClient,
  persister,
  // maxAge: Infinity,
  maxAge: 1000 * 60 * 60 * 24, // 24 hours
  buster: '',
  hydrateOptions: undefined,
  dehydrateOptions: undefined,
});

/*
  TODO: I've got some bad state stuff going on. Maybe violating this principle:
  For example, one rule is that you should not mutate an existing state object or ref object. Doing so
  may lead to unexpected behavior such as not triggering re-renders, triggering too many re-renders, and
  triggering partial re-renders (meaning some components re-render while others don't when they should).
    -- Kato, Daishi. Micro State Management with React Hooks (p. 32). Packt Publishing. Kindle Edition.
 */

/* structure is:
    <BrowserRouter>                 // from index.js root.render
        <QCProvider>                // all descendent components will be able to call useQuery
            <QueryStringStateMgr>   // gets state (codeset_ids for now) from query string, passes down through props
                <CsetsRoutes>       // where routes are defined (used to be directly in BrowserRouter in index.js
                    <App>           // all routes start with App
                        <Outlet/>   // this is where route content goes, all the other components
                    </App>
                </CsetsRoutes>
            <QueryStringStateMgr>
        </QCProvider />
    </BrowserRouter>
*/
function QCProvider() {
  // prefetch({itemType: 'all_csets'});
  return (
    // <React.StrictMode>
    // {/* StrictMode helps assure code goodness by running everything twice, but it's annoying*/}
    //   {" "}
    <QueryClientProvider client={queryClient}
                         persistOptions={{
                           persister,
                           // maxAge: Infinity,
                           maxAge: 1000 * 60 * 60 * 24, // 24 hours
                           serialize: data => compress(JSON.stringify(data)),
                           deserialize: data => JSON.parse(decompress(data)),
                         }}
    >
      <AppStateProvider>
        <QueryStringStateMgr />
        <ReactQueryDevtools initialIsOpen={false} />
      </AppStateProvider>
    </QueryClientProvider>
    // </React.StrictMode>
  );
}
function QueryStringStateMgr(props) {
  const location = useLocation();
  const [lastRefresh, setLastRefresh] = useState(dataAccessor.lastRefreshed());
  const [searchParams, setSearchParams] = useSearchParams();
  // gets state (codeset_ids for now) from query string, passes down through props
  // const [codeset_ids, setCodeset_ids] = useState(sp.codeset_ids || []);
  const sp = searchParamsToObj(searchParams, setSearchParams);
  const { codeset_ids = [] } = sp;

  useEffect(() => {
    (async () => {
      const timestamp = await dataAccessor.cacheCheck();
      if (timestamp > lastRefresh) {
        setLastRefresh(timestamp);
      }
    })();
  });

  let globalProps = { ...sp, searchParams, setSearchParams };

  if (sp.fixSearchParams) {
    delete sp.fixSearchParams;
    const csp = createSearchParams(sp);
    return <Navigate to={location.pathname + "?" + csp.toString()} />;
  }
  /*
  useEffect(() => {
    if (sp.codeset_ids && !isEqual(codeset_ids, sp.codeset_ids)) {
      setCodeset_ids(sp.codeset_ids);
    }
  }, [searchParams, codeset_ids, sp.codeset_ids]);
   */

  function changeCodesetIds(codeset_id, how) {
    // how = add | remove | toggle
    if (how === "set" && Array.isArray(codeset_id)) {
      updateSearchParams({
                           ...globalProps,
                           addProps: { codeset_ids: codeset_id },
                         });
      return;
    }
    const included = codeset_ids.includes(codeset_id);
    let action = how;
    if (how === "add" && included) return;
    if (how === "remove" && !included) return;
    if (how === "toggle") {
      action = included ? "remove" : "add";
    }
    if (action === "add") {
      updateSearchParams({
        ...globalProps,
        addProps: { codeset_ids: [...codeset_ids, codeset_id] },
      });
    } else if (action === "remove") {
      if (!included) return;
      updateSearchParams({
        ...globalProps,
        addProps: { codeset_ids: codeset_ids.filter((d) => d !== codeset_id) },
      });
    } else {
      throw new Error(
        "unrecognized action in changeCodesetIds: " +
          JSON.stringify({ how, codeset_id })
      );
    }
  }

  if (location.pathname === "/") {
    return <Navigate to="/OMOPConceptSets" />;
  }
  if (location.pathname === "/cset-comparison" && isEmpty(codeset_ids)) {
    return <Navigate to="/OMOPConceptSets" />;
  }
  if (location.pathname === "/testing") {
    const test_codeset_ids = [400614256, 411456218, 419757429, 484619125];
    let params = createSearchParams({ codeset_ids: test_codeset_ids });
    // setSearchParams(params);
    let url = "/cset-comparison?" + params;
    // return redirect(url); not exported even though it's in the docs
    return <Navigate to={url} replace={true} /* what does this do? */ />;
  }
  if (!globalProps.codeset_ids) {
    globalProps.codeset_ids = [];
  }
  return <RoutesContainer {...globalProps} changeCodesetIds={changeCodesetIds} />;
}
function RoutesContainer(props) {
  window.props_w = props;
  // console.log(window.props_w = props);
  return (
    <Routes>
      {/*<Route path="/help" element={<HelpWidget {...props} />} />*/}
      <Route path="/" element={<App {...props} />}>
        <Route
            path="cset-comparison"
            element={<CsetComparisonPage {...props}
                       // concepts={props.cset_data.concepts}
                       // conceptLookup={props.cset_data.conceptLookup}
                       // edges={props.cset_data.edges}
            />}
        />
        <Route
            path="OMOPConceptSets"
            element={<ConceptSetsPage {...props} />}
        />
        <Route path="about" element={<AboutPage {...props} />} />
        <Route path="upload-csv" element={<UploadCsvPage {...props} />} />
        <Route
            path="graph"
            element={<ConceptGraph {...props} />}
        />
        <Route path="download-json" element={<DownloadJSON {...props} />} />
        <Route path="view-state" element={<ViewCurrentState {...props} />} />
        {/* <Route path="OMOPConceptSet/:conceptId" element={<OldConceptSet />} /> */}
      </Route>
    </Routes>
  );
}
function App(props) {
  return (
    <ThemeProvider theme={theme}>
      {/*
        <Box sx={{backgroundColor: '#EEE', border: '2px solid green', minWidth: '200px', minHeight: '200px'}} >
          // <ContentItems/>
        </Box>
        */}
      <div className="App">
        {/* <ReactQueryDevtools initialIsOpen={false} />*/}
        <MuiAppBar {...props}>
          {/* Outlet: Will render the results of whatever nested route has been clicked/activated. */}
        </MuiAppBar>
        <Outlet />
      </div>
    </ThemeProvider>
  );
}
const theme = createTheme({
  // https://mui.com/material-ui/customization/theme-components/#global-style-overrides
  // https://mui.com/material-ui/guides/interoperability/#global-css
  // see example https://mui.com/material-ui/customization/theming/
  // status: { danger: orange[500], },
  components: {
    MuiCard: {
      defaultProps: {
        margin: "6pt",
      },
    },
  },
});

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

export { QCProvider };
