import React, {useEffect, useState} from 'react';
import ReactDOM from 'react-dom/client';
import {BrowserRouter, Routes, Route, matchPath, useLocation, useNavigate, createSearchParams} from "react-router-dom";
import {ConceptSetsPage, CsetComparisonPage} from './Csets';
import _ from 'lodash';
import {App, AboutPage, useSearchState, } from './App';
import './index.css';
// import MuiAppBar from './MuiAppBar';
// import Table from './Table'
// script src="http://localhost:8097"></script>
// import reportWebVitals from './reportWebVitals';

const test_codeset_ids = [400614256, 411456218, 419757429, 484619125, 818292046, 826535586];

function ErrorPath() {
  return <h3>Unknown path</h3>
}

function CsetsRoutes() {

  const location = useLocation();
  const navigate = useNavigate();

  let searchParamsAsObject = useSearchState();

  const [codeset_ids, setCodeset_ids] = useState(searchParamsAsObject.codeset_id || []);

  useEffect(() => {
    if (location.pathname == '/') {
      navigate('/OMOPConceptSets');
      return;
    }
    if (location.pathname == '/testing') {
      let params = createSearchParams({codeset_id: test_codeset_ids});
      navigate({
        pathname: '/cset-comparison',
        search: `?${params}`,
      });
    }
    setCodeset_ids(searchParamsAsObject.codeset_id)
  }, [location]);  // maybe not necessary to have location in dependencies

  console.log({codeset_ids})
  return (
      <Routes>
        <Route path="/" element={<App />}>
          {/*<Route path="ontocall" element={<EnclaveOntoAPI />} />*/}
          <Route path="cset-comparison" element={<CsetComparisonPage codeset_ids={codeset_ids}/>} />
          {/* <Route path="cset-comparison/:conceptId" element={<ConceptSet />} /> */}
          <Route path="OMOPConceptSets" element={<ConceptSetsPage codeset_ids={codeset_ids} />} />
          <Route path="about" element={<AboutPage />} />
          {/* <Route path="testing" element={<ConceptSetsPage codeset_ids={test_codeset_ids}/>} /> */}
          {/* <Route path="OMOPConceptSet/:conceptId" element={<OldConceptSet />} /> */}
          {/*<Route path=":conceptId" element={<ConceptList />}/>*/}
          <Route path="*"  element={<ErrorPath/>} />
        </Route>
      </Routes>
  )
}
const root = ReactDOM.createRoot(document.getElementById('root'));
root.render(
  <BrowserRouter>
    <CsetsRoutes />
  </BrowserRouter>
);

function Testing() {
  return <h3>nothing to see here</h3>
}
/*
<React.StrictMode>
</React.StrictMode>
*/
// If you want to start measuring performance in your app, pass a function
// to log results (for example: reportWebVitals(console.log))
// or send to an analytics endpoint. Learn more: https://bit.ly/CRA-vitals
// reportWebVitals();


/*
https://reactjs.org/docs/error-boundaries.html
<ErrorBoundary>
</ErrorBoundary>
class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false };
  }

  static getDerivedStateFromError(error) {
    // Update state so the next render will show the fallback UI.
    return { hasError: true };
  }


  componentDidCatch(error, errorInfo) {
    // You can also log the error to an error reporting service
    // logErrorToMyService(error, errorInfo);
    console.log(error, errorInfo);
  }

  render() {
    if (this.state.hasError) {
      // You can render any custom fallback UI
      return <h1>Something went wrong.</h1>;
    }

    return this.props.children;
  }
}
*/
