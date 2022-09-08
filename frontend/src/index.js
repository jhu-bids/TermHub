import React from 'react';
import ReactDOM from 'react-dom/client';
import { BrowserRouter, Routes, Route, matchPath } from "react-router-dom";

import './index.css';
import {App, AboutPage, EnclaveOntoAPI, } from './App';
import {ConceptSetsPage, CsetSearch, ConceptList } from './CSets';
import MuiAppBar from './MuiAppBar';
import Table from './Table'
// script src="http://localhost:8097"></script>
// import reportWebVitals from './reportWebVitals';


function ErrorPath() {
  return <h3>Unknown path</h3>
}
const root = ReactDOM.createRoot(document.getElementById('root'));
root.render(
    <BrowserRouter>
      <Routes>

        <Route path="/" element={<App />}>
          {/*<Route path="ontocall" element={<EnclaveOntoAPI />} />*/}
          <Route path="csets-from-disk" element={<CsetSearch/>} />
          {/* <Route path="csets-from-disk/:conceptId" element={<ConceptSet />} /> */}
          <Route path="OMOPConceptSets" element={<ConceptSetsPage />} />
          <Route path="about" element={<AboutPage />} />
          <Route path="testing" element={<Testing />} />
          {/* <Route path="OMOPConceptSet/:conceptId" element={<OldConceptSet />} /> */}
          {/*<Route path=":conceptId" element={<ConceptList />}/>*/}
          <Route path="*"  element={<ErrorPath/>} />
        </Route>
      </Routes>
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
