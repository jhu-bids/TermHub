import React, {useState, useReducer, useEffect, useRef} from 'react';
import {Table} from './Table';
import {cfmt} from "./utils";

function AboutPage(props) {
  const {codeset_ids=[], all_csets=[], cset_data={}} = props;
  const {data_counts=[], } = cset_data;

  const rowData = data_counts.map(
      line => {
        line = line.map(d => cfmt(d));
        const [Message, ConceptSetNames, CodesetIds, Concepts] = line;
        return {Message, ConceptSetNames, CodesetIds, Concepts};
      }
  )

  return (
      <div>
        <p>TermHub is terminology management heaven.</p>
        <Table rowData={rowData}/>
      </div>
  );
}


export {AboutPage, };
