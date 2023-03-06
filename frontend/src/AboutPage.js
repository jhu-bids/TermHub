/*
* todo's
*  todo: 1. Siggie was going to add some sort of Table here
* */
import React, {useState, } from 'react';
import Typography from "@mui/material/Typography";
import Button from "@mui/material/Button";
import {Link} from "@mui/material";
import * as po from './Popover';
// import React, {useState, useReducer, useEffect, useRef} from 'react';
// import {Table} from './Table';
// import {cfmt} from "./utils";

let TextBody = (props) => (<Typography variant="body2" color="text.primary" gutterBottom>{props.children}</Typography>)
let TextH1 = (props) => (<Typography variant="h5" color="text.primary" style={{marginTop: '22px'}} gutterBottom>{props.children}</Typography>)
let TextH2 = (props) => (<Typography variant="h6" color="text.primary" style={{marginTop: '5px'}} gutterBottom>{props.children}</Typography>)
let DOCS = {};

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

  return (
      <div>
        <TextH1>About TermHub</TextH1>
          <TextBody>TermHub is a tool for comparing, analyzing, updating, and (soon) creating concept sets. At the current
            time it only handles concept sets in the <a href="https://covid.cd2h.org/enclave">N3C Enclave</a>, but
            is charted to expand beyond N3C (to work with FHIR, VSAC, OHDSI/ATLAS, and other sources of code sets
            and targets for new code set development) in the near future.</TextBody>
          <TextBody>This <a href="https://youtu.be/EAwBZUiNUUk?t=2130">demo video</a> from the October 31, 2022 N3C Forum
             provides a brief introduction. (TermHub has evolved since the video was made. Use the create issue button
             below to clamor for a new video and we will push that up on our priority list.</TextBody>

        <TextH1>Bug reports & feature requests</TextH1>
        <TextBody>
          If you encounter a bug or a poor user experience issue, or have a feature request in mind, we would love to hear from you.<br/>
          {/*<p><Button variant={"outlined"}>*/}
          <Button variant={"contained"}><Link href="https://github.com/jhu-bids/TermHub/issues/new/choose" color="inherit">
            Create an issue
          </Link></Button>
        </TextBody>
        
        <TextH1>How to's</TextH1>
        <TextH2>How to make changes to a codeset (via Atlas JSON)</TextH2>
        {/*todo: resolve console warnings: <ul>/<ol> cannot appear as a descendant of <p>.
            https://mui.com/material-ui/api/typography/*/}
        <TextBody>
          <ol>
            <li>Go to the "Cset Search" page.</li>
            <li>Search for the codeset.</li>
            <li>Select the codeset from the dropdown menu.</li>
            <li>Optional: Select any additional codesets that might also be helpful in the process, e.g. to compare to the one we are editing.</li>
            <li>Go to the "Cset Comparison" page.</li>
            <li>Click on the column header for codeset you want to change.</li>
              <ul>
                <li>Click <b>+</b> to add a concept</li>
                <li>Click the <b>cancel sign</b> to remove a concept</li>
                <li>Click <b>D</b> to toggle <code>inludeDescendants</code></li>
                <li>Click <b>M</b> to toggle <code>includeMapped</code></li>
                <li>Click <b>X</b> to toggle <code>isExcluded</code></li>
              </ul>
            <li>You will see two boxes at the top. The left box has some metadata about the codeset. The right box shows your <em>staged changes</em>. Click the <b>Export JSON</b> link in that <em>staged changes</em> box.</li>
            <li>A new browser tab will up with just the JSON. Copy or save it.</li>
            <li>Go back to the "Cset Comparison" page, and click the "Open in Enclave" link.</li>
            <li>A new tab for the N3C data enclave will open. Log in if needed.</li>
            <li>Click the "Versions" tab at the top left.</li>
            <li>Click the blue "Create new version" button at the bottom left.</li>
            <li>Fill out the information in the "Create New Draft OMOP Concept Set Version" popup, and click "Submit".</li>
            <li>Your new draft version should appear on the left (may require a page refresh). Click it.</li>
            <li>On the right hand side, there is a blue button called "Add Concepts". Click the down arrow, then select "Import ATLAS Concept Set Expression JSON" from the menu.</li>
            <li>Copy/paste the JSON obtained from TermHub earlier into the box, and click "Import Atlas JSON".</li>
            <li>Click the version on the left again.</li>
            <li>On the right, click the green "Done" button.</li>
          </ol>
        </TextBody>
        
        {/* todo: Pages */}
        
      </div>
  );
}

DOCS.blank_search_intro = (<>
  <h1>Welcome to TermHub! Beta version 0.1</h1>
  <p style={{paddingLeft: '12px', paddingRight: '130px', }}>TermHub is a tool for comparing, analyzing, updating, and creating concept sets.
    At the current time it only handles concept sets in the N3C Enclave, but is charted to
    expand beyond N3C in the near future.</p>
  <h2>Within TermHub you can:</h2>

  <div style={{paddingLeft: '12px', paddingRight: '130px', }}>
    <p><strong>CSET SEARCH</strong>: perform existing concept set searches as found in the N3C Enclave</p>

    <p><strong>CSET COMPARISON</strong>: compare to similar existing concept sets. Add and remove concepts by reviewing and selecting
          concept mappings, descendants, exclusions, etc. to build a new concept set that meets your research needs. </p>

    <p><strong>UPLOAD CSV</strong>: With a single CSV, you can create (i) a new version to an existing concept set, e.g. to
          add/delete concepts or change metadata, and (ii) coming soon: upload a completely new concept set ("concept set
          container").</p>

    <p><strong>HELP/ABOUT</strong>: Learn more about TermHub and review the step by step “How To” section. Provide feedback by
          creating an issue. Let us know of any bug or a poor user experience, or share a feature request.</p>

    <p><strong>Bug reports & feature requests</strong>: This is a beta version and we value your feedback. If you encounter a
          bug or a poor user experience issue, or have a feature request in mind, we would love to hear from you. Create an
          issue in the HELP/ABOUT
          section.</p>
  </div>
</>);

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

export {AboutPage, DOCS, TestPop, };
