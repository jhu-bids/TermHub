/* Upload CSV */
import React from 'react';
import Typography from "@mui/material/Typography";
import Button from "@mui/material/Button";
import {Link} from "@mui/material";


function UploadCsvPage(props) {

  return (
      <div>
        <Typography variant="h5" color="text.primary" gutterBottom>
          Upload CSV
        </Typography>
        <Typography variant="body2" color="text.primary" gutterBottom>
          <p>You can : link to docs</p>
        </Typography>
        <Button variant={"contained"}>
          {/*TODO: find out to link*/}
          <Link href="/" color="inherit">New concept set version</Link>
        </Button>
        <span> </span>
        <Button variant={"contained"} disabled={true}>
          <Link href="/" color="inherit">New concept set container (coming soon)</Link>
        </Button>
      </div>
  );
}


export {UploadCsvPage, };
