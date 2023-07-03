/*
 * todo's
 *  todo: 1. Siggie was going to add some sort of Table here
 * */
import React, {useEffect, useState} from "react";
// import {queryClient} from "../App";
import Typography from "@mui/material/Typography";
import Button from "@mui/material/Button";
import { TextField, } from "@mui/material";
import { Link, useLocation } from "react-router-dom";
import VERSION from "../version";
import {useDataCache} from "../state/DataCache";
import {axiosCall} from "../state/DataGetter";

// import * as po from './Popover';

// import React, {useState, useReducer, useEffect, useRef} from 'react';
// import {Table} from './Table';
// import {cfmt} from "./utils";

let TextBody = (props) => (
  <Typography variant="body2" color="text.primary" gutterBottom>
    {props.children}
  </Typography>
);
let TextBold = (props) => (
  <Typography
    sx={{ fontWeight: "bold" }}
    variant="body2"
    color="text.primary"
    gutterBottom
  >
    {props.children}
  </Typography>
);
let TextH1 = (props) => (
  <Typography
    variant="h5"
    color="text.primary"
    style={{ marginTop: "30px" }}
    gutterBottom
  >
    {props.children}
  </Typography>
);
let TextH2 = (props) => (
  <Typography
    variant="h6"
    color="text.primary"
    style={{ marginTop: "5px" }}
    gutterBottom
  >
    {props.children}
  </Typography>
);
let LI = (props) => (
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
let DOCS = {};

const handleRefresh = async () => {
  try {
    await axiosCall('db-refresh', {backend: true, verbose: false, });
    console.log('Triggered: database refresh');
  } catch (error) {
    console.error('Error:', error);
  }
};

function AboutPage(props) {
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
  const [codeset_ids, setCodeset_ids] = useState(props.codeset_ids);
  const [refreshButtonClicked, setRefreshButtonClicked] = useState();
  const [lastRefreshed, setLastRefreshed] = useState();
  const location = useLocation();
  const { search } = location;

  useEffect(() => {
    (async () =>{
      let lastRefreshed = dataCache.lastRefreshed();
      if (!lastRefreshed) {
        await dataCache.cacheCheck();
        lastRefreshed = dataCache.lastRefreshed();
        setLastRefreshed(lastRefreshed);
      }
    })()
  });

  return (
    <div style={{ margin: "15px 30px 15px 40px" }}>
      <TextH1>About TermHub</TextH1>
      <TextBody>
        TermHub is a tool for comparing, analyzing, updating, and (soon)
        creating concept sets. At the current time it only handles concept sets
        in the <a href="https://covid.cd2h.org/enclave">N3C Enclave</a>, but is
        charted to expand beyond N3C (to work with FHIR, VSAC, OHDSI/ATLAS, and
        other sources of code sets and targets for new code set development) in
        the near future.
      </TextBody>
      <TextBody>
        This <a href="https://youtu.be/EAwBZUiNUUk?t=2130">demo video</a> from
        the October 31, 2022 N3C Forum provides a brief introduction. (TermHub
        has evolved since the video was made. Use the create issue button below
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
      <TextBody><b>IMPORTANT:</b> Concept set members are currently slowly updated in the API. As a tentative solution,
        to prevent bugs, new containers and code sets will not be imported into TermHub until those members are also
        available for fetching. This unfortunately slows down fetching of new code sets from being otherwise
        instantaneous to hours or days.</TextBody>
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

      <TextH1>How to's</TextH1>
      <TextH2>How to: Fix the app if it's acting weird</TextH2>
        <ol>
          <LI>Try: Refreshing the page</LI>
          <LI>
            Try purging localStorage (by clicking here, or if you can't get to this page, open chrome(or other browser
            console, and enter `localStorage.clear()`): <Button variant={"contained"}
              // onClick={() => queryClient.removeQueries()}
              onClick={() => localStorage.clear()}
            >
              Empty the data cache
            </Button>
          </LI>
          <LI>Complain to <a href="mailto:sigfried@jhu.edu">Siggie</a></LI>
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

      <TextH2>How to: Make changes to a codeset (via Atlas JSON)</TextH2>
      {/*todo: resolve console warnings: <ul>/<ol> cannot appear as a descendant of <p>.
            https://mui.com/material-ui/api/typography/*/}
      <ol>
        <LI>Go to the "Cset Search" page.</LI>
        <LI>Search for the codeset.</LI>
        <LI>Select the codeset from the dropdown menu.</LI>
        <LI>
          Optional: Select any additional codesets that might also be helpful in
          the process, e.g. to compare to the one we are editing.
        </LI>
        <LI>Go to the "Cset Comparison" page.</LI>
        <LI>Click on the column header for codeset you want to change.</LI>
        <ul>
          <LI>
            Click <b>+</b> to add a concept
          </LI>
          <LI>
            Click the <b>cancel sign</b> to remove a concept
          </LI>
          <LI>
            Click <b>D</b> to toggle <code>inludeDescendants</code>
          </LI>
          <LI>
            Click <b>M</b> to toggle <code>includeMapped</code>
          </LI>
          <LI>
            Click <b>X</b> to toggle <code>isExcluded</code>
          </LI>
        </ul>
        <LI>
          You will see two boxes at the top. The left box has some metadata
          about the codeset. The right box shows your <em>staged changes</em>.
          Click the <b>Export JSON</b> link in that <em>staged changes</em> box.
        </LI>
        <LI>A new browser tab will up with just the JSON. Copy or save it.</LI>
        <LI>
          Go back to the "Cset Comparison" page, and click the "Open in Enclave"
          link.
        </LI>
        <LI>A new tab for the N3C data enclave will open. Log in if needed.</LI>
        <LI>Click the "Versions" tab at the top left.</LI>
        <LI>Click the blue "Create new version" button at the bottom left.</LI>
        <LI>
          Fill out the information in the "Create New Draft OMOP Concept Set
          Version" popup, and click "Submit".
        </LI>
        <LI>
          Your new draft version should appear on the left (may require a page
          refresh). Click it.
        </LI>
        <LI>
          On the right hand side, there is a blue button called "Add Concepts".
          Click the down arrow, then select "Import ATLAS Concept Set Expression
          JSON" from the menu.
        </LI>
        <LI>
          Copy/paste the JSON obtained from TermHub earlier into the box, and
          click "Import Atlas JSON".
        </LI>
        <LI>Click the version on the left again.</LI>
        <LI>On the right, click the green "Done" button.</LI>
      </ol>

      {/* todo: Pages (what's this about?) */}

      <TextH1>
        <Link to={`/view-state${search ? search : ''}`}
              component={Link}
              style={{margin: '7px', textTransform: 'none'}}
        >
          View current state
        </Link>
      </TextH1>


    </div>
  );
}

DOCS.blank_search_intro = (
  <>
    <h1>Welcome to TermHub! Beta version { VERSION }</h1>
    <p style={{ paddingLeft: "12px", paddingRight: "130px" }}>
      TermHub is a tool for comparing, analyzing, updating, and creating concept
      sets. At the current time it only handles concept sets in the N3C Enclave,
      but is charted to expand beyond N3C in the near future.
    </p>
    <h2>Within TermHub you can:</h2>

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
          Learn more about TermHub and review the step by step “How To” section.
        </LI>
        <LI>Provide feedback by creating a GitHub issue.</LI>
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

/* was going to use tagged templates; see https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Template_literals
  but these docs are react chunks, so, should be easier
function processTemplate(strings, params={}) {
  const keys = Object.keys(params);
  if (strings.length !== keys.length + 1) {
    throw new Error("not supposed to happen, wrong number of params");
  }

}
function getDoc(docName, params={}) {
  const tmpl = DOCS[docName];
  return processTemplate(tmpl, params);
}
*/
function howToSaveStagedChanges(params) {
  return (
    <>
      <TextBold>In order to save your changes to the enclave:</TextBold>
      <ol>
        <LI>
          <a href={params.exportJsonLink} target="_blank" rel="noreferrer">
            Click to export JSON
          </a>
          . A new browser tab will open up with just the JSON. Copy or save it.
        </LI>
        <LI>
          Come back to this tab, and{" "}
          <a href={params.openInEnclaveLink} target="_blank" rel="noreferrer">
            click to open this concept set in the Enclave
          </a>
        </LI>
        <LI>A new tab for the N3C data enclave will open. Log in if needed.</LI>
        <LI>Click the "Versions" tab at the top left.</LI>
        <LI>Click the blue "Create new version" button at the bottom left.</LI>
        <LI>
          Fill out the information in the "Create New Draft OMOP Concept Set
          Version" popup, and click "Submit".
        </LI>
        <LI>
          Your new draft version should appear on the left (may require a page
          refresh). Click it.
        </LI>
        <LI>
          On the right hand side, there is a blue button called "Add Concepts".
          Click the down arrow, then select "Import ATLAS Concept Set Expression
          JSON" from the menu.
        </LI>
        <LI>
          Copy/paste the JSON obtained from TermHub earlier into the box, and
          click "Import Atlas JSON".
        </LI>
        <LI>Click the version on the left again.</LI>
        <LI>On the right, click the green "Done" button.</LI>
      </ol>
      <p>
        To save your work, click
        <Button
          onClick={() => {
            navigator.clipboard.writeText(window.location.toString());
          }}
        >
          Copy URL
        </Button>
        <br />
        Best practice is to paste this URL in your lab notebook and annotate
        your work there as well.
      </p>
    </>
  );
}



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

export {
  AboutPage,
  DOCS,
  TextBody,
  TextBold,
  TextH2,
  TextH1,
  LI,
  howToSaveStagedChanges /*HelpWidget, HelpButton,*/
};
