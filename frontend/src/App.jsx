/* https://reactjs.org/docs/hooks-intro.html
https://mui.com/material-ui/react-list/
https://mui.com/material-ui/getting-started/usage/
https://github.com/mui/material-ui
https://stackoverflow.com/questions/53219113/where-can-i-make-api-call-with-hooks-in-react
might be useful to look at https://mui.com/material-ui/guides/composition/#link
referred to by https://stackoverflow.com/questions/63216730/can-you-use-material-ui-link-with-react-router-dom-link
*/
import React, {useEffect} from "react";
import axios from "axios";
import {
  // Link, useHref, useParams, BrowserRouter, redirect,
  Outlet,
  Navigate,
  useLocation,
  createSearchParams,
  Routes,
  Route,
} from "react-router-dom";
import { createTheme, ThemeProvider } from "@mui/material/styles";
import "./App.css";
import { isEmpty } from "lodash";
// import {decompress, decompressFromEncodedURIComponent} from "lz-string";
// import * as lz from "lz-string";
// window.lz = lz;

import { ConceptSetsPage } from "./components/Csets";
import { CsetComparisonPage } from "./components/CsetComparisonPage";
import { AboutPage } from "./components/AboutPage";
// import { ConceptGraph } from "./components/GraphD3dag";
import { ConceptGraph, } from "./components/GraphPlayground";
import {ViewCurrentState, } from "./state/State";
import {
  CodesetIdsProvider,
  CidsProvider,
  AlertsProvider,
  useAlerts,
  useAlertsDispatch,
  NewCsetProvider,
  useNewCset, urlWithSessionStorage, // getSessionStorage, serializeSessionStorage,
} from "./state/AppState";
import {GraphProvider} from "./state/GraphState";
import {SearchParamsProvider, useSearchParamsState} from "./state/SearchParamsProvider";
import {backend_url, DataGetterProvider} from "./state/DataGetter";
import { UploadCsvPage } from "./components/UploadCsv";
// import { DownloadJSON } from "./components/DownloadJSON";
import MuiAppBar from "./components/MuiAppBar";
import {DataCacheProvider} from "./state/DataCache";
import {AlertMessages} from "./components/AlertMessages";
import {N3CRecommended} from "./components/N3CRecommended";
import {UsageReport} from "./components/UsageReport";
import {AddConcepts} from "./components/AddConcepts";
// import {EnclaveAuthTest, AuthCallback, Logout, } from "./components/utils";
import {DEPLOYMENT} from "./env";

/* structure is:
    <BrowserRouter>                 // from index.js root.render
      <SearchParamsProvider>        // gets state from query string -- mainly codeset_ids
        <AlertsProvider>
          <NewCsetProvider>
            <DataCacheProvider>       // ability to save to and retrieve from cache in localStorage
              <DataGetterProvider>    // utilities for fetching data. dataCache needs access to this a couple of times
                                      //  so those method calls will have to pass in a dataGetter
                <GraphProvider>       // graph stuff for concept hierarchy
                  <RoutesContainer/>
                </GraphProvider>
              </DataGetterProvider>
            </DataCacheProvider>
          </NewCsetProvider>
        </AlertsProvider>
      </SearchParamsProvider>
    </BrowserRouter>
*/
function AppWrapper() {
  // prefetch({itemType: 'all_csets'});
  return (
    // <React.StrictMode> // {/* StrictMode helps assure code goodness by running everything twice, but it's annoying*/}
      <SearchParamsProvider>
        <AlertsProvider>
          <CodesetIdsProvider>
            <CidsProvider>
              <NewCsetProvider>
                <DataCacheProvider>
                  <DataGetterProvider>
                    <GraphProvider>
                      <RoutesContainer/>
                    </GraphProvider>
                  </DataGetterProvider>
                </DataCacheProvider>
              </NewCsetProvider>
            </CidsProvider>
          </CodesetIdsProvider>
        </AlertsProvider>
      </SearchParamsProvider>
    // </React.StrictMode>
  );
}
// window.compress = compress;
// window.decompress = decompress;
function RoutesContainer() {
  const spState = useSearchParamsState();
  let {sp, updateSp, } = spState;
  const {codeset_ids, } = sp;
  const location = useLocation();
  const [newCset, newCsetDispatch] = useNewCset();

  useEffect(() => {
    if (sp.sstorage) {
      const sstorage = JSON.parse(sp.sstorage);
      /*
      // compressing doesn't do much when you have to uri it
      try {
        // const sstorageString = lz.decompressFromEncodedURIComponent(sp.sstorage) || sp.sstorage;
        // sstorage = JSON.parse(sstorageString);
      } catch (e) {
        // const sstorageString = decompress(sp.sstorage);
        // sstorage = JSON.parse(sstorageString);
        console.warn('could not parse sstorage', e);
      }
       */
      Object.entries(sstorage).map(([k,v]) => {
        if (k === 'newCset' || k === 'session_id') {
          // restore alters newCset.definitions (unabbreviates)
          v = newCsetDispatch({type: 'restore', newCset: v});
        } else {
          console.warn('was only expecting newCset in sstorage search param, got', {[k]: v},
                       'adding to sessionStorage anyway');
          sessionStorage.setItem(k, JSON.stringify(v));
        }
      });

      updateSp({delProps: ['sstorage']});
      // this updateSp generates a warning
      //  You should call navigate() in a React.useEffect(), not when your component is first rendered.
      //  but seems to work ok anyway. If if doesn't, try going back to something like the code below.
      //  but the problem with code below is that you can't re-navigate by returning <Navigate...> from
      //    useEffect. has to be returned by RoutesContainer.
      // sp = {...sp};
      // delete sp.sstorage;
      // let csp = createSearchParams(sp);
      // let url = location.pathname + '?' + csp;
      // return <Navigate to={url} replace={true} />;
    }
  })
  let pathname = location.pathname;

  if (pathname === "/cset-comparison" && isEmpty(codeset_ids)) {
    pathname = '/';
  }
  if (pathname === "/") {
    return <Navigate to={`/OMOPConceptSets`} />;
  }
  if (pathname === "/testing") {
    const test_codeset_ids = [400614256, 411456218, 419757429, 484619125];
    let params = createSearchParams({ codeset_ids: test_codeset_ids });
    // setSearchParams(params);
    let url = "/cset-comparison?" + params;
    // return redirect(url); not exported even though it's in the docs
    return <Navigate to={url} replace={true} /* what does this do? */ />;
  }

  return (
    <Routes>
      {/*<Route path="/help" element={<HelpWidget/>} />*/}
      <Route path="/" element={<App/>}>
        <Route path="cset-comparison" element={<CsetComparisonPage/>} />
        <Route path="OMOPConceptSets" element={<ConceptSetsPage/>} />
        <Route path="add-concepts" element={<AddConcepts/>} />
        <Route path="about" element={<AboutPage/>} />
        <Route path="upload-csv" element={<UploadCsvPage/>} />
        {/*<Route path="auth/callback" element={<AuthCallback/>} />*/}
        {/*<Route path="auth/logout" element={<Logout/>} />*/}
        <Route
            path="graph"
            // element={<DisplayGraph/>}
            element={<ConceptGraph/>}
        />
        {/*<Route path="download-json" element={<DownloadJSON/>} />*/}
        <Route path="view-state" element={<ViewCurrentState/>} />
        <Route path="N3CRecommended" element={<N3CRecommended/>} />
        <Route path="usage" element={<UsageReport/>} />
        {/* <Route path="OMOPConceptSet/:conceptId" element={<OldConceptSet />} /> */}
      </Route>
    </Routes>
  );
}
function App(props) {
  const {sp} = useSearchParamsState();
  const location = useLocation();
  /*
  const alerts = useAlerts();
  const alertsDispatch = useAlertsDispatch();
  let alertsComponent = null;
  // turning this off even locally
  if (false && DEPLOYMENT === 'local' || sp.show_alerts) {
    alertsComponent = <AlertMessages alerts={alerts}/>;
  }
  */
  // console.log(DEPLOYMENT);

  return (
    <ThemeProvider theme={theme}>
      {/*{ sp.login ? <EnclaveAuthTest /> : null }*/}
      <div className="App">
        {/* <ReactQueryDevtools initialIsOpen={false} />*/}
        <MuiAppBar>
        </MuiAppBar>
        {/*{ alertsComponent }*/}
        <Outlet />
        {/* Outlet will render the results of whatever nested route has been clicked/activated. */}
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

export { AppWrapper };
