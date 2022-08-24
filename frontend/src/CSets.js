import {useNavigate, useParams} from "react-router-dom";
import {useQuery} from "@tanstack/react-query";
import axios from "axios";
import AGtest from "./aggrid-test";
import {ReactQueryDevtools} from "@tanstack/react-query-devtools";
import List from "@mui/material/List";
import ListItem from "@mui/material/ListItem";
import React from "@types/react";

function ConceptSets(props) {
  let path = 'objects/OMOPConceptSet';
  let url = enclave_url(path)
  let navigate = useNavigate();
  const { isLoading, error, data, isFetching } = useQuery([url], () =>
      axios
          .get(url)
          .then((res) => res.data.data.map(d => d.properties))
  );
  if (isLoading) return "Loading...";

  if (error) return "An error has occurred: " + error.message;
  async function csetCallback(props) {
    let {rowData, colClicked} = props
    navigate(`/OMOPConceptSet/${rowData.codesetId}`)
  }

  return  (
      <div>
        <AGtest rowData={data} rowCallback={csetCallback}/>
        <pre>
        {JSON.stringify({data}, null, 4)}
      </pre>
        <div>{isFetching ? "Updating..." : ""}</div>
        <p>I am supposed to be the results of <a href={url}>{url}</a></p>
        <ReactQueryDevtools initialIsOpen />
      </div>)
}

function ConceptSet(props) {
  let {conceptId} = useParams();
  let path = `objects/OMOPConceptSet/${conceptId}`
  let url = enclave_url(path)
  const { isLoading, error, data, isFetching } = useQuery([path], () =>
      axios
          .get(url)
          .then((res) => {
            let csetData = res.data.properties;
            return [
              {field: 'Code set ID', value: csetData.codesetId},
              {field: 'Created at', value: csetData.createdAt},
              {field: 'Version title', value: csetData.conceptSetVersionTitle},
              {field: 'Is most recent version', value: csetData.isMostRecentVersion},
              {field: 'Intention', value: csetData.intention},
              {field: 'Update message', value: csetData.updateMessage},
              {field: 'Provenance', value: csetData.provenance},
              {field: 'Limitations', value: csetData.limitations},
            ]
          })
  );

  if (isLoading) return `Loading... (isFetching: ${JSON.stringify(isFetching)}`;
  if (error) return `An error has occurred with ${<a href={url}>{url}</a>}: ` + error.message;
  return <div>
    <List>
      {
        data.map(({field, value}) =>
                     <ListItem key={field}><b>{field}:</b>&nbsp; {value}<br/></ListItem>
        )
      }
    </List>
    <ConceptList />
    {/*nothing here yet except*/}
    {/*<pre>*/}
    {/*  {JSON.stringify({data}, null, 4)}*/}
    {/*</pre>*/}
    {/*<ReactQueryDevtools initialIsOpen />*/}
  </div>
}
function ConceptList(props) {
  let params = useParams();
  let {conceptId} = params;
  let path = `objects/OMOPConceptSet/${conceptId}/links/omopconcepts`;
  let url = enclave_url(path)
  const { isLoading, error, data, isFetching } = useQuery([path], () =>
      axios
          .get(url)
          .then((res) => res.data.data.map(d => d.properties)) )
  return <div>
    <AGtest rowData={data} />
    {/*rowCallback={csetCallback}/>*/}
    <p>you want to see concepts for {conceptId}?</p>
    <pre>
      {JSON.stringify({props, params, data}, null, 2)}
    </pre>
  </div>
}
