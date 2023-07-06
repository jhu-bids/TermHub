import React, {useRef} from "react";
import Alert from '@mui/material/Alert';
import AlertTitle from '@mui/material/AlertTitle';
import Stack from '@mui/material/Stack';
import Button from '@mui/material/Button';

import {useStateSlice} from "../state/AppState";
import {FlexibleContainer} from "./FlexibleContainer";
export default function AlertMessages() {
  const [alerts, alertsDispatch] = useStateSlice("alerts");
  const countRef = useRef({n: 0, z: 500});

  let alertsArray = Object.values(alerts);
  if (alertsArray.length) {
    return (
        <FlexibleContainer title="Alerts" position={{x: window.innerWidth - 300, y: 300}}
                           startHidden={false} countRef={countRef}>
          <Stack sx={{ width: '100%' }} spacing={2}>
            {alertsArray.map((alert, i) => (
                <Alert severity={alert.severity}
                       key={i}
                       action={ <Button color="inherit" size="small"> UNDO </Button> }
                >
                  <AlertTitle>Error</AlertTitle>
                </Alert>
            ))}

            <Alert
            >
              This is a success alert — check it out!
            </Alert>

            <Alert severity="error">
              <AlertTitle>Error</AlertTitle>
              This is an error alert — <strong>check it out!</strong>
            </Alert>
            <Alert severity="warning">
              <AlertTitle>Warning</AlertTitle>
              This is a warning alert — <strong>check it out!</strong>
            </Alert>
            <Alert severity="info">
              <AlertTitle>Info</AlertTitle>
              This is an info alert — <strong>check it out!</strong>
            </Alert>
            <Alert severity="success">
              <AlertTitle>Success</AlertTitle>
              This is a success alert — <strong>check it out!</strong>
            </Alert>
          </Stack>
        </FlexibleContainer>);
  }
}

export const alertsReducer = (state, action) => {
  /*
      alerts for ongoing or failed api calls or other messages/warnings to display to users
      {
        id: 3, // or could be string with some meaning if desired
        alertType: 'error', // or 'warning', 'apicall', ...
        text: 'api call failed...' // ?
        errObj: {} // from axios or whatever
      }
   */
  if (!action || !action.type) return state;
  let {type, id, payload} = action;
  let alert;
  if (typeof (id) !== 'undefined') {
    alert = state[id];
  }
  switch (type) {
    case "create":
      if (alert) {
        throw new Error(`alert with id ${id} already exists`, alert);
      }
      // let {alertType, text, errObj} = action.payload;
      alert = {
        ...action.payload,
        id: id ?? Object.keys(state).length,
        status: 'unread',
        severity: 'info',
      }
      break;
    case "resolve":
      alert = {...alert, status: 'complete', severity: 'success', payload: {...alert.payload, ...payload}};
      break;
    case "error":
      alert = {...alert, status: 'error', severity: 'error', error: payload};
      break;
    default:
      throw new Error(`bad alert type: ${type}`);
  }
  return {...state, alert};
  throw new Error(`not sure what to do with action\n${JSON.stringify(action, null, 2)}`);
}