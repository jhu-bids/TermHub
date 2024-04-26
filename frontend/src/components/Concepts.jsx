/*
import React from'react';

export function Concepts(props) {
  // Allow user to search for and add concepts by concept_id or typeahead on concept_name

  // Was going to use web sockets so that backend can respond immediately to
  //  typing in the typeahead, but callWebSocket() below is not working right.
  //  Instead, implementing cancel of backend tasks. (#553)

  callWebSocket();

  return (
    <div>
      <h1>Concepts</h1>
      <div style={{border: '3px solid pink', }} id="refresh-status">
        Refresh status will appear here
      </div>
    </div>
  );
}
function callWebSocket() {
  const ws = new WebSocket("ws://localhost:8000/test-ws");

  ws.onopen = (event) => {
    console.log("WebSocket connection opened:", event);
  };

  ws.onmessage = (event) => {
    const msg = event.data;
    console.log(msg);
    const statusElem = document.getElementById("refresh-status");
    statusElem.innerText = msg;
  };

  ws.onclose = (event) => {
    console.log("WebSocket connection closed:", event);
  };

  ws.onerror = (error) => {
    console.error("WebSocket error:", error);
  };
}
*/