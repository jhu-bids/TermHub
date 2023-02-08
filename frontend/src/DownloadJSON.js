import React from 'react';

import {useDataWidget} from "./utils";

function DownloadJSON(props) {
  const n3c_csets_url = 'get-n3c-recommended-codeset_ids';
  const [n3c_csets_data_widget, n3cprops] = useDataWidget('n3c-csets', n3c_csets_url);
  const n3c_codeset_ids = n3cprops.data;
  if (!n3c_codeset_ids) {
    return n3c_csets_data_widget;
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
        <pre>{JSON.stringify(n3c_codeset_ids)}</pre>
      </div>
  )
}

export {DownloadJSON};