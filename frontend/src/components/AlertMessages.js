import React, {useRef} from "react";
import Alert from '@mui/material/Alert';
import AlertTitle from '@mui/material/AlertTitle';
import Stack from '@mui/material/Stack';
import Button from '@mui/material/Button';
import {Inspector} from "react-inspector";

import {useStateSlice} from "../state/AppState";
import {FlexibleContainer} from "./FlexibleContainer";
export function AlertMessages({alerts}) {
  // const [alerts, alertsDispatch] = useStateSlice("alerts");
  const countRef = useRef({n: 0, z: 500});

  let alertsArray = Object.values(alerts);
  if (alertsArray.length) {
    return (
        <FlexibleContainer title="Alerts" position={{x: window.innerWidth * 0.35 , y: 300}}
                           style={{width: '60%'}}
                           startHidden={false} countRef={countRef}>
          <Stack sx={{ width: '100%' }} spacing={2}>
            {alertsArray.map((alert, i) => (
                <Alert severity={alert.severity}
                       key={i}
                       onClose={() => {}}
                       action={ <Button color="inherit" size="small">??</Button> }
                >
                  <AlertTitle>{alert.title}</AlertTitle>
                  <Inspector data={alert} />
                </Alert>
            ))}
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
  let {type, id, } = action;
  if (!id) {
    throw new Error(`alertAction requires an id`, alert);
  }

  let alert = state[id];

  switch (type) {
    case "create":
      if (alert) {
        throw new Error(`alert with id ${id} already exists`, alert);
      }
      alert = {
        ...action,
        id: id ?? Object.keys(state).length,
        status: 'unread',
        severity: 'info',
      }
      break;
    case "resolve":
      alert = {...alert, ...action, status: 'complete', severity: 'success', };
      break;
    case "error":
      alert = {...alert, ...action, status: 'error', severity: 'error', };
      break;
    default:
      throw new Error(`bad alert type: ${type}`);
  }
  return {...state, [alert.id]: alert};
}