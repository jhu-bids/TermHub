import React, {useState, useRef, useEffect} from "react";
import {once} from "lodash";
import IconButton from "@mui/material/IconButton";
import CloseIcon from "@mui/icons-material/Close";
import Draggable from "react-draggable";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
// import zIndex from "@mui/material/styles/zIndex";

export function ErrorAlert(props) {
  const {msg, err} = props;
}

const itemContent = once(() => {
  let stackTop = -1;
  let stack = [];
  const STARTING_ZINDEX = 1000;     // FlexibleContainers will increment from here

  function stackAdd(props) {
    const {title} = props;
    let stackPosition = stack.findIndex(d => d === title);
    if (stackPosition > -1) {
      // console.warn(`${title} already at stack [${stack.join()}][${stackPosition}]`);
    } else {
      stack.push(title);
      stackTop++;
      stackPosition = stackTop;
    }
    return stackPosition;
  }
  function stackRemove(props) {
    const {title} = props;
    stack = stack.filter(d => d !== title);
  }
  function stackPutOnTop(props) {
    const {title} = props;
    stack = stack.filter(d => d !== title);
    stack.push(title);
    stackTop++;
    return stackTop;
  }
  function showButton(props) {
    let { title, position, children, countRef, hideShowPrefix=false, closeAction=()=>{},
      setDisplay, startHidden=true, hideTitle, style, buttonStyle, openOnly=false} = props;

    style = { ...buttonStyle, display: "inline-block", };
    return (
        <Button
            sx={{ ...style, marginRight: "4px" }}
            variant="contained"
            color="primary"
            onClick={() => {
              countRef.current.n++;
              countRef.current.z++;
              setDisplay("shown");
            }}
        >
          {hideShowPrefix ? '' : 'Show '}{title}
        </Button>
    );
  }
  function showContent(props) {
    let { title, position, children, countRef, closeAction=()=>{}, zIndex, setZIndex,
      stackPosition, draggableRef, setDisplay, hideTitle, style, } = props;


    const closeFunc = (() => {
      countRef.current.n--;
      stack = stack.filter(d => d !== title);
      setDisplay("hidden");
      closeAction();
    });
    style = {
      ...style,
      // zIndex: countRef.current.z,
      zIndex: STARTING_ZINDEX + (zIndex || stackPosition), // zIndex can get updated by stackPutOnTop
      position: "absolute",
      backgroundColor: "#EEE",
      border: "2px solid green",
      minWidth: "200px",
      minHeight: "200px",
      maxWidth: "95%",
      // display: "flex",
      // flexDirection: "column",
      overflow: "scroll!important",
    };
    const displayedContent = (
        <Box
            ref={draggableRef}
            // closeFunc={() => setDisplay("hidden")}
            sx={style}
        >
          <div className="handle" data-testid={`flexcontainer-${title}`} style={{display: 'flex', flexDirection: 'row', cursor: "move", }}>
            {/*[{stack.join(', ')}][{stackPosition}]*/}
            {
              hideTitle ? null : <span style={{padding: '10px 3px 3px 10px'}}><strong>{title}</strong></span>
            }
            <IconButton onClick={closeFunc} sx={{
              marginLeft: 'auto',
              // position: "absolute", right: 0
            }}>
              <CloseIcon />
            </IconButton>
          </div>
          {children}
        </Box>
    );
    return (
        <Draggable
            onStart={() => {
              const stackPos = stackPutOnTop(props);
              setZIndex(stackPos);
            }}
            nodeRef={draggableRef}
            handle=".handle"
            defaultPosition={{
              x: position.x + (stackPosition) * 50,
              y: position.y + (stackPosition) * 50
            }}
        >
          {displayedContent}
        </Draggable>
    );
  }
  return [showButton, showContent, stackAdd, stackRemove];
});

export function FlexibleContainer(props) {
  let { startHidden=true, openOnly=false} = props;
  const [display, setDisplay] = useState((startHidden && !openOnly) ? "hidden" : "shown");
  const draggableRef = useRef(null);
  const [zIndex, setZIndex] = useState(); // this is just to force render on zindex change

  const [showButton, showContent, stackAdd, stackRemove] = itemContent();

  if (display === "hidden" && !openOnly) {
    stackRemove(props);
    return showButton({...props, setDisplay, setZIndex});
  } else if (display === "shown" || openOnly) {
    const stackPosition = stackAdd(props);
    return showContent({...props, draggableRef, setDisplay, stackPosition, zIndex, setZIndex,})
  }
}