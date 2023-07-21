import React, { useState, useRef } from "react";
import IconButton from "@mui/material/IconButton";
import CloseIcon from "@mui/icons-material/Close";
import Draggable from "react-draggable";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import zIndex from "@mui/material/styles/zIndex";

export function ErrorAlert(props) {
  const {msg, err} = props;

}
export function FlexibleContainer({ title, position, children, countRef,
                                    startHidden=true, style}) {
  const [display, setDisplay] = useState(startHidden ? "hidden" : "shown");
  const draggableRef = useRef(null);

  let displayedContent;
  style = { ...style, display: "inline-block", };
  if (display === "hidden") {
    displayedContent = (
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
        Show {title}
      </Button>
    );
    return displayedContent; // maybe better if the buttons aren't draggable
  } else if (display === "shown") {
    const closeFunc = () => {
      countRef.current.n--;
      setDisplay("hidden");
    };
    style = {
      ...style,
      zIndex: countRef.current.z,
      position: "absolute",
      backgroundColor: "#EEE",
      border: "2px solid green",
      minWidth: "200px",
      minHeight: "200px",
      display: "flex",
      flexDirection: "column",
    };
    displayedContent = (
        <Box
            ref={draggableRef}
            closeFunc={() => setDisplay("hidden")}
            sx={style}
        >
          <div className="handle" style={{display: 'flex', flexDirection: 'row', cursor: "move", }}>
            <span style={{padding: '10px 3px 3px 10px'}}><strong>{title}</strong></span>
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
  }
  return (
    <Draggable
        nodeRef={draggableRef}
        handle=".handle"
        defaultPosition={{
          x: position.x + (countRef.current.n - 1) * 50,
          y: position.y + (countRef.current.n - 1) * 50
        }}
    >
      {displayedContent}
    </Draggable>
  );
}