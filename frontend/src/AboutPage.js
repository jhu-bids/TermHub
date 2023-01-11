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
          <p>TermHub is a tool for creating and updating concept sets. <a href="https://youtu.be/EAwBZUiNUUk?t=2130">Demo video</a>.</p>
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
