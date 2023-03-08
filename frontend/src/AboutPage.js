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

let TextBody = (props) => (<Typography variant="body2" color="text.primary" gutterBottom>{props.children}</Typography>);
let TextBold = (props) => (<Typography sx={{fontWeight:'bold'}} variant="body2" color="text.primary" gutterBottom>{props.children}</Typography>);
let TextH1 = (props) => (<Typography variant="h5" color="text.primary" style={{marginTop: '22px'}} gutterBottom>{props.children}</Typography>);
let TextH2 = (props) => (<Typography variant="h6" color="text.primary" style={{marginTop: '5px'}} gutterBottom>{props.children}</Typography>);
let LI = (props) => (<li><Typography variant="body2" color="text.primary" style={{marginTop: '5px'}} gutterBottom>{props.children}</Typography></li>);
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
      <div style={{margin: '15px 30px 15px 40px'}}>
        <TextH1>About TermHub</TextH1>
          <TextBody>TermHub is a tool for comparing, analyzing, updating, and (soon) creating concept sets. At the current
            time it only handles concept sets in the <a href="https://covid.cd2h.org/enclave">N3C Enclave</a>, but
            is charted to expand beyond N3C (to work with FHIR, VSAC, OHDSI/ATLAS, and other sources of code sets
            and targets for new code set development) in the near future.</TextBody>
          <TextBody>This <a href="https://youtu.be/EAwBZUiNUUk?t=2130">demo video</a> from the October 31, 2022 N3C Forum
             provides a brief introduction. (TermHub has evolved since the video was made. Use the create issue button
             below to clamor for a new video and we will push that up on our priority list.)</TextBody>

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
          <ol>
            <LI>Go to the "Cset Search" page.</LI>
            <LI>Search for the codeset.</LI>
            <LI>Select the codeset from the dropdown menu.</LI>
            <LI>Optional: Select any additional codesets that might also be helpful in the process, e.g. to compare to the one we are editing.</LI>
            <LI>Go to the "Cset Comparison" page.</LI>
            <LI>Click on the column header for codeset you want to change.</LI>
            <ul>
              <LI>Click <b>+</b> to add a concept</LI>
              <LI>Click the <b>cancel sign</b> to remove a concept</LI>
              <LI>Click <b>D</b> to toggle <code>inludeDescendants</code></LI>
              <LI>Click <b>M</b> to toggle <code>includeMapped</code></LI>
              <LI>Click <b>X</b> to toggle <code>isExcluded</code></LI>
            </ul>
            <LI>You will see two boxes at the top. The left box has some metadata about the codeset. The right box shows your <em>staged changes</em>. Click the <b>Export JSON</b> link in that <em>staged changes</em> box.</LI>
            <LI>A new browser tab will up with just the JSON. Copy or save it.</LI>
            <LI>Go back to the "Cset Comparison" page, and click the "Open in Enclave" link.</LI>
            <LI>A new tab for the N3C data enclave will open. Log in if needed.</LI>
            <LI>Click the "Versions" tab at the top left.</LI>
            <LI>Click the blue "Create new version" button at the bottom left.</LI>
            <LI>Fill out the information in the "Create New Draft OMOP Concept Set Version" popup, and click "Submit".</LI>
            <LI>Your new draft version should appear on the left (may require a page refresh). Click it.</LI>
            <LI>On the right hand side, there is a blue button called "Add Concepts". Click the down arrow, then select "Import ATLAS Concept Set Expression JSON" from the menu.</LI>
            <LI>Copy/paste the JSON obtained from TermHub earlier into the box, and click "Import Atlas JSON".</LI>
            <LI>Click the version on the left again.</LI>
            <LI>On the right, click the green "Done" button.</LI>
          </ol>
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
    <p><strong>CSET SEARCH</strong></p>
      <ul>
        <LI>Perform searches for existing concept sets currently in the N3C Enclave.</LI>
      </ul>

    <p><strong>CSET COMPARISON</strong></p>
      <ul>
        <LI>Compare selected concept sets.</LI>
        <LI>Add and remove concepts by reviewing and selecting
        concept mappings, descendants, exclusions.</LI>
        <LI>Export JSON of modified concept set. (Required in order to put changes in Enclave, for now.)</LI>
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

    <p><strong>HELP/ABOUT</strong></p>
      <ul>
        <LI>
          Learn more about TermHub and review the step by step “How To” section.
        </LI>
        <LI>
          Provide feedback by creating a GitHub issue.
        </LI>
        <LI>
          Let us know of any bug or a poor user experience, or share a feature request.
        </LI>
      </ul>
  </div>
  <div style={{position: 'absolute', top: (window.innerHeight - 40) + 'px'}}>
    &#169; Johns Hopkins University 2023. Available open source on <a href="https://github.com/jhu-bids/TermHub">GitHub</a> under
    a <a href="https://github.com/jhu-bids/TermHub/blob/develop/LICENSE">GPL 3 License</a>.
  </div>
</>);

function HelpWidget(props) {

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

export {AboutPage, DOCS, TestPop, HelpWidget, TextBody, TextBold, TextH2, TextH1, LI, };
