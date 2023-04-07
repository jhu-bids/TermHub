import React from 'react';
import Box from '@mui/material/Box';
import {Link, useLocation} from "react-router-dom";
import Button from '@mui/material/Button';

import {useDataWidget} from "./State";

function DownloadJSON(props) {
  const [bundles_widget, bundles_props] = useDataWidget('bundles', 'enclave-api-call/get_bundle_names');
  const n3c_csets_url = 'get-n3c-recommended-codeset_ids';
  const [n3c_csets_data_widget, n3cprops] = useDataWidget('n3c-csets', n3c_csets_url);
  const n3c_codeset_ids = n3cprops.data;
  const {search} = useLocation();
  console.log(search);
  if (! (n3c_codeset_ids && bundles_props.data)) {
    return  <div>
              <h3>Waiting for data</h3>
              <Box sx={{ display: 'flex' }}>
                {n3c_csets_data_widget}
                {bundles_widget}
              </Box>
            </div>
  }
  return (
      <div>
        What should we be able to do here?
        <ul>
          <li>First!!: get json for N3C Recommended</li>
          <li>give list of codeset_ids you want json for</li>
          <li>get json for all concept sets in a bundle</li>
          <li>get list of bundle names</li>
        </ul>
        <Box>Available bundles:
          {
            bundles_props.data.map(
                b => <Button
                      sx={{ my: 2, margin: '0px 2px 0px 2px', padding: '1px',
                        // display: 'block', border: '1px solid green', marginRight: '3px',
                      }}
                      key={b}
                      variant="outlined"  //"contained" // 'text'
                      size="small"
                      component={Link}
                      to={`/DownloadJSON?bundle=${b}`}
                >{b}</Button>
            )
          }

        </Box>
        <pre>{JSON.stringify(n3c_codeset_ids)}</pre>
        If you get a warning message about STANDARD_CONCEPT_CAPTION or INVALID_REASON_CAPTION, proceed
        without concern.
      </div>
  )
}

export {DownloadJSON};