import React, {useState, useRef, } from 'react';
import Accordion from '@mui/material/Accordion';
import AccordionSummary from '@mui/material/AccordionSummary';
import AccordionDetails from '@mui/material/AccordionDetails';
import Typography from '@mui/material/Typography';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import Draggable from 'react-draggable';
import Box from '@mui/material/Box';
import Switch from '@mui/material/Switch';
import Paper from '@mui/material/Paper';
import Collapse from '@mui/material/Collapse';
import FormControlLabel from '@mui/material/FormControlLabel';
import useMeasure from 'react-use/lib/useMeasure';
import Button from "@mui/material/Button";

import {useAppState, DerivedStateProvider, useDerivedState, } from "./State";

export function DummyComponent({foo}) {
  return <h3>dummy component: {foo}</h3>
}
const contentComponents = {
  'DummyComponent': DummyComponent,
}
export function ContentItems(props) {
  const appState = useAppState();
  const [contentItems, dispatch] = appState.getSlice('contentItems');
  const items = contentItems.filter(item => item.show).map(
      item => {
        const {name, content, componentName, props} = item;
        if (content) return content;
        const Component = contentComponents[componentName];
        return <Component key={name} {...props} />;
      }
  );
  const buttons = contentItems.filter(item => !item.show).map(
      item => {
        const {name, content, Component, props} = item;
        return (
            <Button key={name} onClick={() => dispatch({type: 'contentItems-show', name: 'dummy'})} >
              Show {name}
            </Button>
        );
      }
  );
  return (
      <>
        {buttons}
        {items}
      </>
  )
}

export default function FlexibleContainer(
    {id, title, ComponentType, componentProps}) {
  const [display, setCollapsed] = useState('collapsed');
  const draggableRef = useRef(null);
  const setDisplay = (_display) => {
    setCollapsed(() => _display);
  };

  const position = { x: 0, y: 0 };
  let out;
  if (display === 'collapsed') {
    out = <Button
              variant="contained" color="primary"
              onClick={() => setDisplay('show')}>Show {title}</Button>;
  } else if (display === 'show') {
    out = (
        <Draggable nodeRef={draggableRef} defaultPosition={position}>
          <div ref={draggableRef} style={{ cursor: 'move', display: 'inline-block'}}>
            <ComponentType {...componentProps}
               closeFunc={() => setDisplay('collapsed')} />
            <Typography variant={"h3"} >
              Try to drag me
            </Typography>
          </div>
        </Draggable>
  );
}
return out;
}
function usePaperContainer({children}) {
// const [ref, { x, y, width, height, top, right, bottom, left }] = useMeasure();
const [ref, measures ] = useMeasure();
return { ref, measures, contents: (
      <Paper ref={ref} sx={{ m: 1 }} elevation={4} /*measures={measures}*/>
          {children}
        </Paper>
    )};
}
function CollapsibleContainerWithSwitch({id, title, children}) {
  // from https://mui.com/material-ui/transitions/
  const [checked, setChecked] = useState(false);
  const { measures, contents } = usePaperContainer({children});

  const handleChange = () => {
    setChecked((prev) => !prev);
  };
  console.log(measures, contents);
  const {width, height} = measures;
  return (
      <Box sx={{ }}>
        <FormControlLabel
            control={<Switch checked={checked} onChange={handleChange} />}
            label="Show"
        />
        <Box
            sx={{
              '& > :not(style)': {
                display: 'inline-block',
                justifyContent: 'space-around',
                // width, height,
              },
            }}
        >
        <Collapse in={checked} collapsedSize={40}>
          {contents}
          {/*
            <p>Width: {width}, Height: {height}</p>
            <div style={{border: '4px solid purple', display: 'inline-block'}}>
              {contents}
            </div>
          */}
        </Collapse>
          {/*
          <div>
            <Collapse in={checked}>{icon}</Collapse>
            <Collapse in={checked} collapsedSize={40}>
              {icon}
            </Collapse>
          </div>
          <div>
            <Box sx={{ width: '50%' }}>
              <Collapse orientation="horizontal" in={checked}>
                {icon}
              </Collapse>
            </Box>
            <Box sx={{ width: '50%' }}>
              <Collapse orientation="horizontal" in={checked} collapsedSize={40}>
                {icon}
              </Collapse>
            </Box>
          </div>
          */}
        </Box>
      </Box>
  );
}

function accordionPanels({panels=[]}) {
  console.log(panels);
  const out = panels.map((p,i) => {
    const {title, content, id=`panel${i}`} = p;
    return accordionPanel({id, title, content});
  })
  return (
      <div>{out}</div>
  );
}
function accordionPanel({id, title, content}) {
  const panel = (
      <Draggable key={id} defaultPosition={{x: 0, y: 0}} >
        <Accordion>
          <AccordionSummary
              expandIcon={<ExpandMoreIcon />}
              aria-controls={id + '-content'}
              id={id + '-header'}
          >
            <Typography>{title}</Typography>
          </AccordionSummary>
          <AccordionDetails>
            {content}
          </AccordionDetails>
        </Accordion>
      </Draggable>
  );
  return panel;
}
function SimpleAccordion() {
  // from https://mui.com/material-ui/react-accordion/
  return (
      <div>
        <Accordion>
          <AccordionSummary
              expandIcon={<ExpandMoreIcon />}
              aria-controls="panel1a-content"
              id="panel1a-header"
          >
            <Typography>Accordion 1</Typography>
          </AccordionSummary>
          <AccordionDetails>
            <Typography>
              Lorem ipsum dolor sit amet, consectetur adipiscing elit. Suspendisse
              malesuada lacus ex, sit amet blandit leo lobortis eget.
            </Typography>
          </AccordionDetails>
        </Accordion>
        <Accordion>
          <AccordionSummary
              expandIcon={<ExpandMoreIcon />}
              aria-controls="panel2a-content"
              id="panel2a-header"
          >
            <Typography>Accordion 2</Typography>
          </AccordionSummary>
          <AccordionDetails>
            <Typography>
              Lorem ipsum dolor sit amet, consectetur adipiscing elit. Suspendisse
              malesuada lacus ex, sit amet blandit leo lobortis eget.
            </Typography>
          </AccordionDetails>
        </Accordion>
        <Accordion disabled>
          <AccordionSummary
              expandIcon={<ExpandMoreIcon />}
              aria-controls="panel3a-content"
              id="panel3a-header"
          >
            <Typography>Disabled Accordion</Typography>
          </AccordionSummary>
        </Accordion>
      </div>
  );
}
export {FlexibleContainer, accordionPanels, accordionPanel, SimpleAccordion};