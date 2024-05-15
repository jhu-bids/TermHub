/*
 * todo's
 *  todo: 1. Siggie was going to add some sort of Table here
 * */
import React, {useEffect, useState} from "react";
// import {queryClient} from "../App";
import Typography from "@mui/material/Typography";
import Button from "@mui/material/Button";
import {TextField,} from "@mui/material";
import {Link, useLocation} from "react-router-dom";
import {VERSION} from "../env";
import {useDataCache} from "../state/DataCache";
import {useDataGetter} from "../state/DataGetter";
import {useSearchParamsState} from "../state/StorageProvider";

// import * as po from './Popover';

// import React, {useState, useReducer, useEffect, useRef} from 'react';
// import {Table} from './Table';
// import {cfmt} from "./utils";

export const TextBody = (props) => (
  <Typography variant="body2" color="text.primary" gutterBottom>
    {props.children}
  </Typography>
);
export const TextBold = (props) => (
  <Typography
    sx={{ fontWeight: "bold" }}
    variant="body2"
    color="text.primary"
    gutterBottom
  >
    {props.children}
  </Typography>
);
export const TextH1 = (props) => (
  <Typography
    variant="h5"
    color="text.primary"
    style={{ marginTop: "30px" }}
    gutterBottom
  >
    {props.children}
  </Typography>
);
export const TextH2 = (props) => (
  <Typography
    variant="h6"
    color="text.primary"
    style={{ marginTop: "5px" }}
    gutterBottom
  >
    {props.children}
  </Typography>
);
export const LI = (props) => (
  <li>
    <Typography
      variant="body2"
      color="text.primary"
      style={{ marginTop: "5px" }}
      gutterBottom
    >
      {props.children}
    </Typography>
  </li>
);
export const PRE = (props) => (
    <Typography
        variant="pre"
        color="text.primary"
        style={{ marginTop: "5px",
                display: "block",
                unicodeBidi: "embed",
                fontFamily: "monospace",
                whiteSpace: "pre",
        }}
        gutterBottom
    >
      {props.children}
    </Typography>
);
export let DOCS = {};


export function AboutPage() {
  const {sp} = useSearchParamsState();
  // const {codeset_ids=[], all_csets=[], cset_data={}} = props;
  // const {data_counts=[], } = cset_data;
  //
  // const rowData = data_counts.map(
  //     line => {
  //       line = line.map(d => cfmt(d));
  //       const [Message, ConceptSetNames, CodesetIds, Concepts] = line;
  //       return {Message, ConceptSetNames, CodesetIds, Concepts};
  //     }
  // )
  const dataCache = useDataCache();
  const dataGetter = useDataGetter();
  const [codeset_ids, setCodeset_ids] = useState(sp.codeset_ids);
  const [refreshButtonClicked, setRefreshButtonClicked] = useState();
  const [lastRefreshed, setLastRefreshed] = useState();
  const location = useLocation();
  const { search } = location;

  const handleRefresh = async () => {
    try {
      console.log('Triggering database refresh and clearing cache so new data will be fetched when ready');
      // empty cache immediately, and then again after the db-refresh call is done
      dataCache.emptyCache();
      await dataGetter.axiosCall('db-refresh', {backend: true, verbose: false, title: 'Refreshing VS-Hub database from Enclave'});
      dataCache.emptyCache();
    } catch (error) {
      console.error('Error:', error);
    }
  };

  useEffect(() => {
    (async () =>{
      let lastRefreshed = dataCache.lastRefreshed();
      if (!lastRefreshed) {
        await dataCache.cacheCheck(dataGetter);
        lastRefreshed = dataCache.lastRefreshed();
      }
      setLastRefreshed(lastRefreshed);
    })()
  });

  return (
    <div style={{ margin: "15px 30px 15px 40px" }}>
      <TextH1>About VS-Hub</TextH1>
      <TextBody>
        VS-Hub is a tool for comparing, analyzing, updating, and (soon)
        creating concept sets. At the current time it only handles concept sets
        in the <a href="https://covid.cd2h.org/enclave">N3C Enclave</a>, but is
        charted to expand beyond N3C (to work with FHIR, VSAC, OHDSI/ATLAS, and
        other sources of code sets and targets for new code set development) in
        the near future.
      </TextBody>
      <TextBody>
        This <a href="https://youtu.be/EAwBZUiNUUk?t=2130">demo video</a> from
        the October 31, 2022 N3C Forum provides a brief introduction. (VS-Hub
        has evolved since the video was made. Use the <a href="https://github.com/jhu-bids/termhub/issues/new/choose" target="_blank" rel="noopener noreferrer">create issue</a> button below
        to clamor for a new video and we will push that up on our priority
        list.)
      </TextBody>

      <TextH1>Bug reports & feature requests</TextH1>
      <TextBody>
        If you encounter a bug or a poor user experience issue, or have a
        feature request in mind, we would love to hear from you.
      </TextBody>
      <TextBody>
        {/*<p><Button variant={"outlined"}>*/}
        <Button variant={"contained"}
                href="https://github.com/jhu-bids/TermHub/issues/new/choose"
                target="_blank" rel="noreferrer"
        >
            Create an issue
        </Button>
      </TextBody>

      <TextH1>Database Refresh</TextH1>
      <TextBody>Will refresh the database with the latest data from the N3C Enclave.</TextBody>
      <TextBody><b>IMPORTANT:</b> There is a delay in the Enclave where when a concept set draft is finalized, its
        concept set members must be expanded. This can take between 20-45 minutes to complete. At that time, the members
        will be visible in the UI and also the API for fetching by VS-Hub. VS-Hub will detect if this issue occurs and
        will continue to check until the members are available and import them as soon as they are.</TextBody>
      <TextBody>Last refresh: {lastRefreshed ? lastRefreshed.toLocaleString() : 'fetching it...'}</TextBody>
      <TextBody>
        <Button
          variant={"contained"}
          onClick={() => {
            setRefreshButtonClicked(Date());
            handleRefresh();
        }}>
          Refresh database
        </Button>
      </TextBody>

      <TextH1>View / download N3C recommended concept sets</TextH1>
      <TextBody>
        <Button to="/N3CRecommended"
                variant={"contained"}
                component={Link}
                style={{margin: '7px', textTransform: 'none'}}
        >
          N3C Recommended
        </Button>
        <Button to="/N3CRecommended?comparison=true"
                variant={"contained"}
                component={Link}
                style={{margin: '7px', textTransform: 'none'}}
        >
          N3C Recommended comparison after vocab changes
        </Button>
      </TextBody>

      <TextH1>How to's</TextH1>
      <TextH2>How to: Fix the app if it's acting weird</TextH2>
        <ol>
          <LI>Try: Refreshing the page</LI>
          <LI>
            Try purging localStorage (by clicking here, or if you can't get to this page, open chrome(or other browser
            console, and enter `localStorage.clear()`): <Button variant={"contained"}
              // onClick={() => queryClient.removeQueries()}
              onClick={() => dataCache.emptyCache()}
            >
              Empty the data cache
            </Button>
          </LI>
          <LI>File a report: via <a href="https://github.com/jhu-bids/termhub/issues/new/choose" target="_blank" rel="noopener noreferrer">GitHub issue</a> or <a href="mailto:termhub-support@jhu.edu">termhub-support@jhu.edu</a></LI>
        </ol>
      <TextH2>How to: Load a set of concept sets</TextH2>
        <TextBody>
          Using the select list on the CSet Search page loads the concept
          sets one at a time, which can be slow. Until we fix that, you
          can enter a list of codeset_ids here.
        </TextBody>
        <TextField fullWidth multiline
                   label="Enter codeset_ids separated by spaces, commas, or newlines and click link below"
                   onChange={(evt) => {
                     const val = evt.target.value;
                     const cids = val.split(/[,\s]+/).filter(d=>d.length);
                     setCodeset_ids(cids);
                   }}
                   defaultValue={codeset_ids.join(', ')}
        >
        </TextField>
        <Button to={`/OMOPConceptSets?${codeset_ids.map(d => `codeset_ids=${d}`).join("&")}`}
                component={Link}
                style={{margin: '7px', textTransform: 'none'}}
        >
          /OMOPConceptSets?{codeset_ids.map(d => `codeset_ids=${d}`).join("&")}
        </Button>

        <TextH1>Debug / explore application data</TextH1>
        <TextBody>
            <Button
                    to={`/view-state${search ? search : ''}`}
                    variant={"contained"}
                    component={Link}
                    style={{margin: '7px', textTransform: 'none'}}
            >
                View state
            </Button>

            <Button
                to={`/usage${search ? search : ''}`}
                variant={"contained"}
                component={Link}
                style={{margin: '7px', textTransform: 'none'}}
            >
                Usage report
            </Button>
        </TextBody>

    </div>
  );
}

DOCS.blank_search_intro = (
  <>
    <h1>Welcome to VS-Hub! Beta version { VERSION }</h1>
    <p style={{ paddingLeft: "12px", paddingRight: "130px" }}>
      VS-Hub is a tool for comparing, analyzing, updating, and creating concept
      sets. At the current time it only handles concept sets in the N3C Enclave,
      but is charted to expand beyond N3C in the near future.
    </p>
    <h2>Within VS-Hub you can:</h2>

    <div style={{ paddingLeft: "12px", paddingRight: "130px" }}>
      <p>
        <strong>CSET SEARCH</strong>
      </p>
      <ul>
        <LI>
          Perform searches for existing concept sets currently in the N3C
          Enclave.
        </LI>
      </ul>

      <p>
        <strong>CSET COMPARISON</strong>
      </p>
      <ul>
        <LI>Compare selected concept sets.</LI>
        <LI>
          Add and remove concepts by reviewing and selecting concept mappings,
          descendants, exclusions.
        </LI>
        <LI>
          Export JSON of modified concept set. (Required in order to put changes
          in Enclave, for now.)
        </LI>
        <LI>
          <Button
                to="/testing"
                component={Link}
          >
            Example Comparison
          </Button>
        </LI>
      </ul>

      {/*
    <p><strong>UPLOAD CSV</strong>
      <ul>
        <LI>
          With a single CSV, you can create (i) a new version to an existing concept set, e.g. to
          add/delete concepts or change metadata, and (ii) coming soon: upload a completely new concept set ("concept set
          container").
        </LI>
      </ul>
    </p>
    */}

      <p>
        <strong>HELP/ABOUT</strong>
      </p>
      <ul>
        <LI>
          Learn more about VS-Hub and review the step by step “How To” section.
        </LI>
        <LI>Provide feedback by creating a <a href="https://github.com/jhu-bids/termhub/issues/new/choose" target="_blank" rel="noopener noreferrer">GitHub issue.</a></LI>
        <LI>
          Let us know of any bug or a poor user experience, or share a feature
          request.
        </LI>
      </ul>
    </div>
    <div style={{ position: "absolute", top: window.innerHeight - 40 + "px" }}>
      &#169; Johns Hopkins University 2023. Available open source on{" "}
      <a href="https://github.com/jhu-bids/TermHub">GitHub</a> under a{" "}
      <a href="https://github.com/jhu-bids/TermHub/blob/develop/LICENSE">
        GPL 3 License
      </a>
      .
    </div>
  </>
);



/*
function HelpWidget(props) {
  const {doc} = props;
  if (doc === 'legend') {
    return <Legend />;
  }

}
const WINDOW_OPEN_OPTIONS = {
  spec: {
    width: 100, /* window width * /
    height: 900, /* window height * /
  },
  // transform: 'scale(0.8)',
  top: 20,
  left: window.innerWidth - 250,
};
function HelpButton(props) {
  const {doc, windowOptions} = props;
  // const options = windowOptions ?? WINDOW_OPEN_OPTIONS;
  const options = WINDOW_OPEN_OPTIONS;
  const url = `/help?doc=${doc}`;
  const [handleWindowOpen, newWindowHandle] = useOpenInWindow(url, options);
  console.log({newWindowHandle});
  if (doc === 'legend') {
    return <Button onClick={handleWindowOpen}>Show legend</Button>;
  }
}
*/

/*
function LegendButton(props) {
return (
    <po.Popover>
      <po.PopoverTrigger sx={{float:'right'}}>Display legend</po.PopoverTrigger>
      <po.PopoverContent className="Popover legend" >
        <po.PopoverHeading>Legend</po.PopoverHeading>
        <Legend/>
        <po.PopoverClose>Close</po.PopoverClose>
      </po.PopoverContent>
    </po.Popover>)
}
function TestPop(startOpen=false) {
  const [open, setOpen] = useState(startOpen);
  return (
      <div className="App">
        <h1>Floating UI — Popover</h1>
        <po.Popover open={open} onOpenChange={setOpen}>
          <po.PopoverTrigger onClick={() => setOpen((v) => !v)}>
            My trigger
          </po.PopoverTrigger>
          <po.PopoverContent className="Popover">
            <po.PopoverHeading>My popover heading</po.PopoverHeading>
            <po.PopoverDescription>My popover description</po.PopoverDescription>
            <po.PopoverClose>Close</po.PopoverClose>
          </po.PopoverContent>
        </po.Popover>
      </div>
  );
}
*/
