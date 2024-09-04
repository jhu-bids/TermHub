import { Edit, Info } from "@mui/icons-material";
import { sum } from "lodash";
import { useLayoutEffect, useRef, useState } from "react";
import { Tooltip } from "./Tooltip";

export function ColumnHeader(props) {
  let {
    tooltipContent,
    headerContent,
    headerContentProps,
    allottedWidth,
    coldef,
  } = props;
  const targetRef = useRef();
  const [headerDims, setHeaderDims] = useState({ width: 0, height: 0 });

  useLayoutEffect(() => {
    if (targetRef.current) {
      setHeaderDims({
        width: targetRef.current.offsetWidth,
        height: targetRef.current.offsetHeight,
      });
    }
  }, []);
  // coldef.requiredWidth = headerDims.width;

  let header_style = {
    padding: 2,
    // cursor: 'pointer',
    // whiteSpace: 'nowrap',
  };
  /*
  const rotate_header_style = {
    overflow: 'visible',
    textOverflow: 'unset',
    justifyContent: 'left', /* fixes weird thing with rightmost col shifting left when rotated * /
    marginRight: 'auto',
    transform: 'translate(20%,0px) rotate(-35deg)',
    // transform: 'rotate(-35deg)',
    transformOrigin: 'bottom left',
  }
  if (allottedWidth < headerDims.width) {
    header_style = {...header_style, ...rotate_header_style};
  }
  */
  /*
      {
        height: 182px,
        //height: auto,
        borderBottomStyle: solid,
        padding: 0,
        verticalAlign: bottom,
        overflow: visible,
        textOverflow: unset,
        marginTop: auto,
      }

   */
  // console.log({headerContent, allottedWidth, contentWidth: headerDims.width})
  if (tooltipContent) {
    const iconStyle = {
      fontSize: "80%",
      marginTop: "auto",
      marginBottom: "2px",
    };
    headerContent = (
      <span
        style={{
          display: "flex",
          alignItems: "center",
          wordBreak: "break-word",
          maxWidth: "100%",
          gap: "3px",
        }}
        codeset_id={coldef.codeset_id}
      >
        {headerContent}
        <Info sx={iconStyle} />
        {/* <span style={{whiteSpace: "nowrap", textOverflow: "ellipsis", overflow: "hidden"}}>
          {headerContent}
          // (coldef.codeset_id) ? <Edit sx={iconStyle} /> : <Info sx={iconStyle} />
        </span> */}
      </span>
    );
  }
  let header = (
    <span
      className="cset-column-header"
      ref={targetRef}
      style={{ ...header_style }}
      {...headerContentProps}
    >
      {headerContent}
    </span>
  );
  //: {allottedWidth}/{headerDims.width}</span>
  if (tooltipContent) {
    header = <Tooltip content={tooltipContent}>{header}</Tooltip>;
  }
  return header;
}
export function setColDefDimensions({ coldefs, windowSize, margin = 10 }) {
  /* expecting width OR minWidth and remainingPct */
  const [windowWidth, windowHeight] = windowSize;
  const fixedWidthSum = sum(coldefs.map((d) => d.width || 0));
  const remainingWidth = windowWidth - fixedWidthSum - 2 * margin;
  let usedWidth = margin * 2 + fixedWidthSum;
  coldefs = coldefs.map((d) => {
    if (d.remainingPct) {
      // d.width = Math.max(d.minWidth, remainingWidth * d.remainingPct)
      usedWidth += d.width;
    }
    d.grow = 1;
    let h = setColDefHeader(d);
    return h;
  });
  // console.log({windowSize, usedWidth, fixedWidthSum, remainingWidth, });
  return coldefs;
}
export function setColDefHeader(coldef) {
  let { name, headerProps = {}, width } = coldef;
  let { headerContent, headerContentProps, tooltipContent, } = headerProps;
  if (headerContent) {
    if (name) {
      throw new Error(
        "coldef included both name and headerContent; don't know which to use."
      );
    }
  } else {
    if (!name) {
      throw new Error(
        "coldef included neither name nor headerContent; need one."
      );
    }
    headerContent = name;
  }

  coldef.name = (
    <ColumnHeader
      allottedWidth={width}
      coldef={coldef}
      //*...headerProps} {...headerContentProps}
      headerContent={headerContent}
      tooltipContent={tooltipContent}
    />
  );
  coldef.width = coldef.width + "px";
  return coldef;
}