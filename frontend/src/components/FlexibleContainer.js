import React, { useState, useRef } from "react";
import IconButton from "@mui/material/IconButton";
import CloseIcon from "@mui/icons-material/Close";
import Draggable from "react-draggable";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import zIndex from "@mui/material/styles/zIndex";

export function FlexibleContainer({ title, position, children, countRef }) {
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
          countRef.current.n++;
          countRef.current.z++;
          setDisplay("show");
        }}
      >
        Show {title}
      </Button>
    );
    return displayedContent; // maybe better if the buttons aren't draggable
  } else if (display === "show") {
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
        defaultPosition={{
          x: position.x + (countRef.current.n - 1) * 50,
          y: position.y + (countRef.current.n - 1) * 50
        }}
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