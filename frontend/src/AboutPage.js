/*
* todo's
*  todo: 1. Siggie was going to add some sort of Table here
* */
import React from 'react';
import Typography from "@mui/material/Typography";
import Button from "@mui/material/Button";
import {Link} from "@mui/material";
// import React, {useState, useReducer, useEffect, useRef} from 'react';
// import {Table} from './Table';
// import {cfmt} from "./utils";

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
        <Typography variant="h5" color="text.primary" gutterBottom>
          About TermHub
        </Typography>
        <Typography variant="body2" color="text.primary" gutterBottom>
          <p>TermHub is a tool for comparing, analyzing, updating, and (soon) creating concept sets. At the current
            time it only handles concept sets in the <a href="https://covid.cd2h.org/enclave">N3C Enclave</a>, but
            is charted to expand beyond N3C (to work with FHIR, VSAC, OHDSI/ATLAS, and other sources of code sets
            and targets for new code set development) in the near future.</p>
          <p>This <a href="https://youtu.be/EAwBZUiNUUk?t=2130">demo video</a> from the October 31, 2022 N3C Forum
             provides a brief introduction. (TermHub has evolved since the video was made. Use the create issue button
             below to clamor for a new video and we will push that up on our priority list.</p>
        </Typography>
        
        <Typography variant="h5" color="text.primary" gutterBottom>
          Bug reports & feature requests
        </Typography>
        <Typography variant="body2" color="text.primary" gutterBottom>
          If you encounter a bug or a poor user experience issue, or have a feature request in mind, we would love to hear from you.
          {/*<p><Button variant={"outlined"}>*/}
            <p><Button variant={"contained"}>
            {/*<a href="https://github.com/jhu-bids/TermHub/issues/new/choose"></a>Create an issue*/}
<Link href="https://github.com/jhu-bids/TermHub/issues/new/choose" color="inherit">
  Create an issue
</Link>
          </Button></p>
          
        </Typography>
        
        {/*<Table rowData={rowData}/>*/}

      </div>
  );
}


export {AboutPage, };
