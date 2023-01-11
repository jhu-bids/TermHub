/* Upload CSV */
import React from 'react';
import Typography from "@mui/material/Typography";
import Button from "@mui/material/Button";
import axios from "axios";
import {backend_url} from './App';
import {Link} from "@mui/material";

function axiosPut(path, data, backend=true) {
  let url = backend ? backend_url(path) : path;
  console.log('axiosPut url: ', url);
  var formData = new FormData();
  formData.append("csv", data);
  axios.post(url, formData, {
    headers: {
      'Content-Type': 'multipart/form-data'
    }
  })
}
function UploadCsvPage(props) {
  // TODO: finish handler or whatever needs to be done to hit the backend route
  //   https://stackoverflow.com/questions/40589302/how-to-enable-file-upload-on-reacts-material-ui-simple-input
  //   state: {
  //       csv: [],
  //   };

  //  Needs to upload here: /upload-csv-new-cset-version-with-concepts
  const handleUploadVersion = ({ target }) => {
      const fileReader = new FileReader();
      // todo: not sure about 'name'. might not be important until we allow multiple CSV
      // const name = target.accept.includes('image') ? 'images' : 'videos';
    const file = target.files[0]
    fileReader.readAsDataURL(file);
      fileReader.onload = (e) => {
        console.log('filreader onload e:')
        console.log(e)
        axiosPut('upload-csv-new-cset-version-with-concepts', e.target.result);
        // this.setState((prevState) => ({ [name]: [...prevState[name], e.target.result] }));
        // TODO: Needs to upload to: /upload-csv-new-cset-version-with-concepts
      };
  };
  
    const handleUploadContainer = ({ target }) => {
      const fileReader = new FileReader();
      // todo: not sure about 'name'. might not be important until we allow multiple CSV
      // const name = target.accept.includes('image') ? 'images' : 'videos';
      fileReader.readAsDataURL(target.files[0]);
      fileReader.onload = (e) => {
        // this.setState((prevState) => ({ [name]: [...prevState[name], e.target.result] }));
        axiosPut('upload-csv-new-container-with-concepts', e.target.result);
        // TODO: Needs to upload to: /upload-csv-new-container-with-concepts
      };
  };

  console.log('junk')
  return (
      // todo: padding / margin doesn't seem to work
      <div style={{padding: "10px, 10px, 10px, 10px", margin: "10px, 10px, 10px, 10px"}}>
        <Typography variant="h5" color="text.primary" gutterBottom>
          Upload CSV
        </Typography>
        <Typography variant="body2" color="text.primary" gutterBottom>
          With a single CSV, you can create (i) a new version to an existing concept set, e.g. to add/delete concepts
            or change metadata, and (ii) coming soon: upload a completely new concept set ("concept set container").
          <br/><br/>
          CSV format and additional information can be found in: <a href="https://github.com/jhu-bids/TermHub/blob/develop/enclave_wrangler/README.md">the documentation</a>
        </Typography>
        
        <input
          accept=".csv"
          // className={classes.input}
          style={{ display: 'none' }}
          id="upload-version"
          // multiple
          onChange={handleUploadVersion}
          type="file"
        />
        <label htmlFor="upload-version">
          {/*  TODO: Needs to upload to: /upload-csv-new-cset-version-with-concepts */}
          <Button variant="contained" component="span">New concept set version</Button>
        </label>
        
        <span> </span>
        
        <input
          accept="image/*"
          // className={classes.input}
          style={{ display: 'none' }}
          id="upload-container"
          // multiple
          onChange={handleUploadContainer}
          type="file"
        />
        <label htmlFor="upload-container">
          {/*  TODO: Needs to upload to: /upload-csv-new-container-with-concepts */}
          <Button variant="contained" component="span">New concept set container (coming soon)</Button>
        </label>
      </div>
  );
}


export {UploadCsvPage, };
