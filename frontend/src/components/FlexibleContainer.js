import React, { useState, useRef } from "react";
import IconButton from "@mui/material/IconButton";
import CloseIcon from "@mui/icons-material/Close";
import Draggable from "react-draggable";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";

export function FlexibleContainer({ title, position, children, onOpen }) {
  const [display, setDisplay] = useState("hidden");
  const draggableRef = useRef(null);

  let displayedContent;
  let style = {
    cursor: "move",
    display: "inline-block",
  };
  if (display === "hidden") {
    displayedContent = (
      <Button
        sx={{ ...style, marginRight: "4px" }}
        variant="contained"
        color="primary"
        onClick={() => {
          setDisplay("show");
          onOpen(0, 100);
        }}
      >
        Show {title}
      </Button>
    );
    return displayedContent; // maybe better if the buttons aren't draggable
  } else if (display === "show") {
    const closeFunc = () => setDisplay("hidden");
    style = {
      ...style,
      zIndex: 10,
      position: "absolute",
      backgroundColor: "#EEE",
      border: "2px solid green",
      minWidth: "200px",
      minHeight: "200px",
    };
    displayedContent = (
      <>
        <IconButton onClick={closeFunc} sx={{ position: "absolute", right: 0 }}>
          <CloseIcon />
        </IconButton>
        {children}
      </>
    );
  }
  return (
    <Draggable
        nodeRef={draggableRef}
        defaultPosition={position}
    >
      <Box
        ref={draggableRef}
        closeFunc={() => setDisplay("hidden")}
        sx={style}
      >
        {displayedContent}
      </Box>
    </Draggable>
  );
}