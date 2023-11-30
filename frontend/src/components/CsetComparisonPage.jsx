import React, {useCallback, useEffect, useRef, useState,} from "react";
import DataTable, {createTheme} from "react-data-table-component";
import AddCircle from "@mui/icons-material/AddCircle";
import Download from "@mui/icons-material/Download";
import RemoveCircleOutline from "@mui/icons-material/RemoveCircleOutline";
import Box from "@mui/material/Box";
import IconButton from "@mui/material/IconButton";
import Slider from "@mui/material/Slider";
import Switch from "@mui/material/Switch";
import CloseIcon from "@mui/icons-material/Close";
import Button from "@mui/material/Button";
import { flatten, fromPairs, intersection, isEmpty, max, throttle, union, uniqBy } from "lodash";

import {fmt, saveCsv, useWindowSize} from "./utils";
import {setColDefDimensions} from "./dataTableUtils";
import {ConceptSetCard} from "./ConceptSetCard";
import {Tooltip} from "./Tooltip";
import { cellContents, cellStyle, getCodesetEditActionFunc, getItem, Legend, newCsetAtlasWidget, textCellForItem, } from "./NewCset";
import {FlexibleContainer} from "./FlexibleContainer";
import {NEW_CSET_ID, urlWithSessionStorage, useCodesetIds, useHierarchySettings, useNewCset,} from "../state/AppState";
import {useDataCache} from "../state/DataCache";
import {getResearcherIdsFromCsets, useDataGetter} from "../state/DataGetter";
import {LI} from "./AboutPage";

// TODO: Find concepts w/ good overlap and save a good URL for that
// TODO: show table w/ hierarchical indent
// TODO: Color table: I guess would need to see if could pass extra values/props and see if table widget can use that
//  ...for coloration, since we want certain rows grouped together
function CsetComparisonPage() {
  const [codeset_ids, codesetIdsDispatch] = useCodesetIds();
  // const {sp, updateSp} = useSearchParamsState();
  const [newCset, newCsetDispatch] = useNewCset();
  const editingCset = !isEmpty(newCset);
  // const { selected_csets = [], researchers, } = cset_data;
  const dataGetter = useDataGetter();
  const dataCache = useDataCache();
  let [hierarchySettings, hsDispatch] = useHierarchySettings();
  const { nested } = hierarchySettings;
  const windowSize = useWindowSize();
  const infoPanelRef = useRef();
  const countRef = useRef({ n: 1, z: 10 });
  const [panelPosition, setPanelPosition] = useState({ x: 0, y: 0 });
  const [showCsetCodesetId, setShowCsetCodesetId] = useState();
  const sizes = getSizes(/*squishTo*/ 1);
  const customStyles = styles(sizes);
  const [data, setData] = useState({});
  const { indentedCids, concepts, conceptLookup, selected_csets, csmi, researchers, currentUserId,  } = data;

  useEffect(() => {
    (async () => {
      let whoami = dataGetter.fetchAndCacheItems(dataGetter.apiCalls.whoami, undefined);

      await dataGetter.getApiCallGroupId();

      let promises = [ // these can run immediately
        dataGetter.fetchAndCacheItems(dataGetter.apiCalls.cset_members_items, codeset_ids),
        dataGetter.fetchAndCacheItems(dataGetter.apiCalls.csets, codeset_ids),
      ];
      // have to get concept_ids before fetching concepts
      const concept_ids_by_codeset_id = await dataGetter.fetchAndCacheItems(dataGetter.apiCalls.concept_ids_by_codeset_id, codeset_ids);
      let concept_ids = union(flatten(Object.values(concept_ids_by_codeset_id)));

      if (!isEmpty(newCset)) {
        concept_ids = union(concept_ids, Object.values(newCset.definitions).map(d => d.concept_id));
      }

      // have to get indentedCids, which might contain more concept_ids after filling gaps
      const extra_concept_ids = []; // not collecting these yet
      let indentedTreeRows = await dataGetter.fetchAndCacheItems(
          dataGetter.apiCalls.indented_concept_list, { codeset_ids, extra_concept_ids });
      // indentedCids = [[<level>, <concept_id>], ...], or, if summarized: [<level>, [<concept_id>, <concept_id>,...]]

      // summarized rows have a list of the parent's child concept_ids in place of the parent's descendants
      let summarizedRows = [];
      let indentedCids = [];

      indentedTreeRows.forEach((d,i) => {
        if (typeof(d[1]) === 'number') {
          indentedCids[i] = d;
        } else {
          summarizedRows[i] = d;
        }
      });
      concept_ids = union(
          concept_ids,
          indentedCids.map(d => d[1])
      ).filter(d=>d).sort();

      summarizedRows.forEach((d,i) => {
          indentedCids[i] = d;
      });

      promises.push(dataGetter.fetchAndCacheItems(dataGetter.apiCalls.concepts, concept_ids));

      let [ csmi, selected_csets, conceptLookup, ] = await Promise.all(promises);

      selected_csets = codeset_ids.map(d => selected_csets[d]);

      if (!isEmpty(newCset)) {
        selected_csets.push(newCset);
        selected_csets = selected_csets.map(cset => {
          cset = {...cset};
          cset.intersecting_concepts= 0;
          cset.precision = 0;
          cset.recall = 0;
          cset.counts = {};
          return cset;
        });

        csmi = {...csmi, ...newCset.definitions};
      }

      const researcherIds = getResearcherIdsFromCsets(selected_csets);
      let researchers = dataGetter.fetchAndCacheItems(dataGetter.apiCalls.researchers, researcherIds);

      const concepts = Object.values(conceptLookup);

      const conceptsCids = concepts.map(d => d.concept_id).sort();
      /* this has been a valuable check, but it no longer works
      console.assert(intersection(conceptsCids, concept_ids).length === concept_ids.length,
                     "%o", {concepts, conceptsCids, concept_ids});
      */

      const currentUserId = (await whoami).id;
      researchers = await researchers;
      setData(current => ({...current, concept_ids, indentedCids, selected_csets, conceptLookup, csmi,
          concepts, researchers, currentUserId, }));
    })();
  }, [newCset]);

  useEffect(() => {
    if (infoPanelRef.current) {

      let margin_text = window
          .getComputedStyle(infoPanelRef.current)
          .getPropertyValue("margin-bottom");
      margin_text = margin_text.substring(0, margin_text.length - 2);
      const margin = parseInt(margin_text);

      setPanelPosition({
                         x: 0,
                         y: infoPanelRef.current.clientHeight + 2 * margin
                       });
    }
  }, [
              infoPanelRef.current,
              (infoPanelRef.current ? infoPanelRef.current.offsetHeight : 0),
            ]);


  if (isEmpty(concepts) || isEmpty(indentedCids)) {
    return <p>Downloading...</p>;
  }

  // TODO: component is rendering twice. why? not necessary? fix?
  if (!indentedCids) { // if no indentedCids (yet), no information to nest with, so turn off nesting for this
                //  invocation of getRowData (don't save to state)
    hierarchySettings = {...hierarchySettings, nested: false};
  }
  let {allRows, displayedRows, distinctRows, hidden} = getRowData({conceptLookup, indentedCids, hierarchySettings});
  let rowData;
  if (nested) {
    rowData = displayedRows;
  } else {
    // rowData = hierarchyToFlatCids(hierarchy).map(cid => conceptLookup[cid]);
    rowData = distinctRows;
  }

  const editAction = getCodesetEditActionFunc({ csmi, newCset, newCsetDispatch, });

  let columns = colConfig({
    csmi,
    selected_csets,
    concepts,
    editAction,
    sizes,
    windowSize,
    hidden,
    allRows,
    displayedRows,
    hierarchySettings,
    hsDispatch,
    newCset,
    newCsetDispatch,
    setShowCsetCodesetId,
  });

  let csetCard = null;
  if (showCsetCodesetId) {
    const cset = selected_csets.find(d => d.codeset_id == showCsetCodesetId);
    csetCard = (
        <FlexibleContainer key="csetCard" openOnly={true} title={cset.concept_set_version_title}
                           position={panelPosition} countRef={countRef}
                           closeAction={() => setShowCsetCodesetId(undefined)}>
          <ConceptSetCard
              cset={selected_csets.find(d => d.codeset_id == showCsetCodesetId)}
              researchers={researchers}
              hideTitle
              // context="show new cset info"
          />
        </FlexibleContainer>
    );
  }

  let infoPanels = [
    <Button key="distinct"
            disabled={!nested}
            onClick={() => hsDispatch({type:'nested', nested: false})}
            sx={{
              marginRight: '4px',
              display: "flex",
              flexDirection: "row",
            }}
    >
      {distinctRows.length} distinct concepts
    </Button>,
    <Button key="nested"
            disabled={nested}
            onClick={() => hsDispatch({type:'nested', nested: true})}
            sx={{ marginRight: '4px' }}
    >
      {displayedRows.length} in hierarchy
    </Button>,
    /*
    <Button key="download-distinct-tsv"
            variant="outlined"
            onClick={ () => downloadCSV({codeset_ids, displayedRows, selected_csets, csmi}, true) }
            sx={{
              cursor: 'pointer',
              marginRight: '4px',
            }}
    >
      TSV <Download></Download>
    </Button>,
    */
    <Button key="download-distinct-csv"
            variant="outlined"
            onClick={ () => downloadCSV({codeset_ids, displayedRows, selected_csets, csmi}) }
            sx={{
              cursor: 'pointer',
              marginRight: '4px',
            }}
    >
      CSV <Download></Download>
    </Button>,

    <FlexibleContainer key="legend" title="Legend" position={panelPosition} countRef={countRef}>
      <Legend editing={editingCset}/>
    </FlexibleContainer>,

    <Button key="add-cset"
            variant="outlined"
            onClick={() => {
              newCsetDispatch({type: 'createNewCset'});
            }}
            sx={{
              cursor: 'pointer',
              marginRight: '4px',
              display: editingCset ? "none" : "flex",
            }}
    >
      Create new concept set or version
    </Button>,

    /*
    <FlexibleContainer key="cset-table" title="Table of concept set being edited"
                       position={panelPosition} countRef={countRef}>
      <CsetsDataTable show_selected={true}
                      min_col={false}
                      clickable={false}
                      showTitle={false}
                      selected_csets={selected_csets} />
    </FlexibleContainer>,
    */
  ];

  let edited_cset;
  if (editingCset) {
    infoPanels.push(
        <FlexibleContainer key="cset" title="New concept set" startHidden={false} hideShowPrefix={true}
                           style={{width: '80%', resize: "both", }}
                           position={panelPosition}
                           countRef={countRef}>
          <ConceptSetCard
              cset={newCset}
              selected_csets={selected_csets}
              csmi={csmi}
              conceptLookup={conceptLookup}
              newCsetDispatch={newCsetDispatch}
              researchers={researchers}
              editing={true}
              hideTitle
              context="show new cset info"
              styles={{position: 'absolute', }}
          />
        </FlexibleContainer>
    );
    /* infoPanels.push(
        <FlexibleContainer key="compare" title={edited_cset.concept_set_name}>
          <CsetsDataTable {...props} show_selected={true} min_col={false} />
        </FlexibleContainer>
    ); */

    const atlasWidget = newCsetAtlasWidget(newCset, conceptLookup);

    infoPanels.push(
        <FlexibleContainer key="instructions"
                           title="Instructions to save new concept set"
                           style={{maxWidth: 700, }}
                           position={panelPosition} countRef={countRef}>
          {howToSaveStagedChanges({ newCset, atlasWidget })}
        </FlexibleContainer>
    );
  }

  let sendProps = {
    displayedRows, rowData, columns, selected_csets, customStyles
  };
  return (
    <div>
      <span data-testid="comp-page-loading"></span>
      {csetCard}
      <Box
          ref={infoPanelRef}
          sx={{
            width: "96%",
            margin: "9px",
            display: "flex",
            flexDirection: "row",
          }}
      >
        {infoPanels}
        {/*<Typography
            variant="h5"
            sx={{ marginLeft: "auto" }}
        >
          {
            (edited_cset ? `Editing ${edited_cset.concept_set_name}` : 'Click on concept set column heading to edit')
          }
        </Typography> */}
      </Box>
      <ComparisonDataTable /*squishTo={squishTo}*/ {...sendProps} />
      <span data-testid="comp-page-loaded"></span>
    </div>
  );
}

function precisionRecall(props) {

}

function nodeToTree(node) {
  // a flat tree
  const subTrees = node.children().map(n => nodeToTree(n));
  return [node, ...subTrees];
}
export function getRowData(props) {
  console.log("getting row data");

  const {conceptLookup, indentedCids, hierarchySettings, } = props;
  const {/*collapsedDescendantPaths, */ collapsePaths, hideZeroCounts, hideRxNormExtension, nested } = hierarchySettings;

  let allRows, displayedRows;
  if (indentedCids) {   // not sure why they wouldn't be here...maybe not ready yet?
    [allRows, displayedRows] = nestedConcepts(conceptLookup, indentedCids, hierarchySettings);
  } else {
    allRows = concepts;
    displayedRows = concepts;
  }

  // console.log(`allRows: ${allRows.length}, displayedRows: ${displayedRows}`);
  const hidden = {
    rxNormExtension: allRows.filter(row => row.vocabulary_id === 'RxNorm Extension').length,
  }
  // const collapsedRows= allRows.filter(row => row.collapsed);
  // let rows = allRows.filter(row => !row.collapsed);
  if (nested) {
    // collapsedDescendantPaths are all the paths that get hidden, the descendants of all the collapsePaths
    const hiddenRows = flatten(Object.keys(collapsePaths).map(collapsedPath => {
      return allRows.map(r => r.pathToRoot).filter(
          p => p.length > collapsedPath.length && p.startsWith(collapsedPath));
    }));
    const collapsedDescendantPaths = fromPairs(hiddenRows.map(p => [p, true]));
    hidden.collapsed = nested ? collapsedDescendantPaths.length : 0;
    displayedRows = allRows.filter(row => !collapsedDescendantPaths[row.pathToRoot]);
  }

  // const rxNormExtensionRows = rows.filter(r => r.vocabulary_id == 'RxNorm Extension');
  if (hideRxNormExtension) {
    displayedRows = displayedRows.filter(r => r.vocabulary_id !== 'RxNorm Extension');
  }
  hidden.zeroCount = displayedRows.filter(row => row.total_cnt === 0).length;
  if (hideZeroCounts) {
    displayedRows = displayedRows.filter(r => r.total_cnt > 0);
  }
  const distinctRows = uniqBy(displayedRows, row => row.concept_id);
  return {allRows, displayedRows, distinctRows, hidden};
}
function nestedConcepts(conceptLookup, indentedCids, hierarchySettings) {
  const {collapsedDescendantPaths, hideZeroCounts, hideRxNormExtension} = hierarchySettings;

  // let allRows = indentedCids.map(r => ({level: r[0], concept_id: r[1], ...conceptLookup[r[1]]}));
  let allRows = [];
  let summaryRowNum = -1;
  for (let i = 0; i < indentedCids.length; i++) {
    const r = indentedCids[i];
    let row = {};
    if (typeof(r[1]) === 'number') {
      row = { level: r[0], ...conceptLookup[r[1]]};
    } else {
      row = {
        level: r[0],
        concept_id: summaryRowNum,
        concept_name: `${r[1].length} ${ r[0] ? 'children' : 'orphans'} not shown`, // if level==0, these are orphans
      }
      if (typeof(r[1]) ==='string') {
        row.concept_name = r[1];
      }
      summaryRowNum--;
    }
    allRows.push(row);
  }
  let displayedRows = [];
  let currentPath = [];

  for (let i = 0; i < allRows.length; i++) {
    let row = allRows[i];

    if (collapsedDescendantPaths[row.pathToRoot]) {
      continue;
    }

    if (row.level === currentPath.length) {
      currentPath.push(row.concept_id);
    }
    else if (row.level <= currentPath.length) {
      currentPath.splice(row.level);
      currentPath.push(row.concept_id);
    } else {
      throw new Error("shouldn't happen");
    }

    row.pathToRoot = currentPath.join('/');

    if (i < allRows.length - 1 && allRows[i + 1].level > row.level) {
      row.hasChildren = true;
    }
    displayedRows.push(row);
  }
  return [allRows, displayedRows];
  /*
  const graph = new Graph({allowSelfLoops: false, multi: false, type: 'directed'});
  // add each concept as a node in the graph, the concept properties become the node attributes
  concepts.forEach(c => graph.addNode(c.concept_id, c));
  edges.forEach(edge => graph.addEdge(...edge));

  // sort the nodes so the ones with the most descendants come first
  let nodeDepths = [];
  graph.nodes().map(n => {
    let descendants = 0;
    dfsFromNode(graph, n, (node, attr, depth) => {
      if (n !== node) {
        descendants++;
      }
    });
    nodeDepths.push({node: n, descendants});
  });
  let nodes = sortBy(nodeDepths, n => -n.descendants).map(n => n.node);

  let nodeSeen = {};
  nodes.map((n,i) => {
    let currentPath = [];
    if (nodeSeen[n]) {
      return;
    }
    dfsFromNode(graph, n, (node, attr, depth) => {
      nodeSeen[node] = true;
      if (depth === currentPath.length) {
        currentPath.push(node);
      }
      else if (depth <= currentPath.length) {
        currentPath.splice(depth);
        currentPath.push(node);
      } else {
        console.log(currentPath.join('/'), node);
        let paths = allSimplePaths(graph, currentPath[currentPath.length - 1], node);
        console.log(paths);
        throw new Error("shouldn't happen");
      }

      let row = {...graph.getNodeAttributes(node)};
      row.pathToRoot = currentPath.join('/');
      if (collapsedDescendantPaths[row.pathToRoot]) {
        // currentPath.pop(); // don't do this, descendants will continue popping
        allRows.push(row);
        return;
      }
      // console.log('   '.repeat(depth) + node);
      row.hasChildren = graph.outboundDegree(node) > 0;
      row.level = depth;
      allRows.push(row);
      displayedRows.push(row);
    });
  });
  return [allRows, displayedRows];
  */
}
function ComparisonDataTable(props) {
  const {
    columns,
    newCset = {},
    customStyles,
    rowData,
    /* squishTo = 1, cset_data, displayedRows, selected_csets */
  } = props;
  const { definitions = {}, members = {}, } = newCset;
  const infoPanelRef = useRef();
  // console.log(derivedState);

  useEffect(() => {
    for (let i = 0; i < columns.length; i++) {
      const el = document.querySelector(
        ".comparison-data-table .rdt_TableHeadRow " +
                `> .rdt_TableCol[data-column-id=\"${i+1}\"]`
      );
      if (el) {
        el.style.width = columns[i].width + "px";
      }
    }
  });

  const conditionalRowStyles = [
    {
      when: () => true,
      style: (row) => ({
        backgroundColor: row.concept_id in definitions ? "#F662" : "#FFF",
      }),
    },
  ];
  return (
    <DataTable
      customStyles={customStyles}
      conditionalRowStyles={conditionalRowStyles}
      className="comparison-data-table"
      theme="custom-theme" // theme="light"
      columns={columns}
      data={rowData}
      dense
      fixedHeader
      fixedHeaderScrollHeight={() => {
        // console.log(infoPanelRef.current);
        const MuiAppBar = document.querySelector(".Mui-app-bar");
        let headerMenuHeight = 64;
        if (MuiAppBar) {
          headerMenuHeight = MuiAppBar.clientHeight;
        }
        const { offsetTop = 0, offsetHeight = 0 } = infoPanelRef.current ?? {};
        return (
          window.innerHeight -
          (headerMenuHeight + offsetTop + offsetHeight) +
          "px"
        );
        // return "400px";
      }}
      /*
       */
      // highlightOnHover
      // responsive
      // subHeaderAlign="right"
      // subHeaderWrap
      //striped //pagination //selectableRowsComponent={Checkbox}
      //selectableRowsComponentProps={selectProps} //sortIcon={sortIcon}
      // expandOnRowClicked // expandableRows // {...props}
    />
  );
}
function getSizes(squishTo) {
  let sizes = {
    rowFontSize: 13 * squishTo + "px",
    // rowPadding:   ( 1 * squishTo) + 'px', // do these do anything?
    // rowPaddingTop:   ( 4 * squishTo) + 'px',
    // rowPaddingBottom:   ( 0 * squishTo) + 'px',
    collapseIcon: 13 * squishTo + "px",
    linkHeight: 20 * squishTo + "px",
    atlasHeight: 14 * squishTo + "px",
    athenaHeight: 12 * squishTo + "px",
  };
  return sizes;
}
function getCollapseIconAndName(collapsePaths, row, allRows, sizes, hsDispatch, ) {
  let Component, collapseAction;
  if (collapsePaths[row.pathToRoot]) {
    Component = AddCircle;
    collapseAction = 'expand';
  } else {
    Component = RemoveCircleOutline;
    collapseAction = 'collapse';
  }
  return (
      <span
          className="toggle-collapse concept-name-row"
          onClick={() => hsDispatch({ type: "collapseDescendants", row, allRows, collapseAction})}
      >
                <Component
                    sx={{
                      fontSize: sizes.collapseIcon,
                      display: "inline-flex",
                      marginRight: "0.15rem",
                      marginTop: "0.05rem",
                      verticalAlign: "top",
                    }}
                />
        <span className="concept-name-text">{row.concept_name}</span>
      </span>
  );
}
function colConfig(props) {
  let {
    selected_csets,
    concepts,
    sizes,
    editAction,
    windowSize,
    hidden,
    allRows,
    displayedRows,
    hierarchySettings,
    hsDispatch,
    csmi,
    newCset, newCsetDispatch,
    setShowCsetCodesetId
  } = props;
  const {collapsePaths, collapsedDescendantPaths, nested, hideRxNormExtension, hideZeroCounts} = hierarchySettings;
  const { definitions = {}, } = newCset;

  const maxNameLength = max(displayedRows.map(d => d.concept_name.length));
  let coldefs = [
    {
      name: "Concept name",
      selector: (row) => row.concept_name,
      format: (row) => {
        let content = nested ? (
          row.hasChildren
              ? getCollapseIconAndName(collapsePaths, row, allRows, sizes, hsDispatch)
              : (
                  <span className="concept-name-row">
                    <RemoveCircleOutline
                        // this is just here so it indents the same distance as the collapse icons
                      sx={{ fontSize: sizes.collapseIcon, visibility: "hidden" }}
                    />
                    <span className="concept-name-text">{row.concept_name}</span>
                  </span>)
        ) : (
            <span className="concept-name-text">{row.concept_name}</span>
        );
        return content;
      },
      sortable: !nested,
      // minWidth: 100,
      // remainingPct: .60,
      width: Math.min((400 + selected_csets.length * 80) * 1.5,
          window.innerWidth - 400 - selected_csets.length * 80) - 36,
      // grow: 4,
      wrap: true,
      compact: true,
      conditionalCellStyles: [
        {
          when: (row) => true,
          style: (row) => ({
            padding: '0px 3px 0px ' + (nested ? (16 + row.level * 16) : 16) + "px",
          }),
        },
      ],
    },
    {
      // name: "Vocabulary",
      headerProps: {
        headerContent: (
            concepts.some(d => d.vocabulary_id === 'RxNorm Extension')
            ? <div style={{display: 'flex', flexDirection: 'column'}}>
                <div>Vocabulary</div>
                <div style={{fontSize: 'x-small'}}>({hidden.rxNormExtension} {hideRxNormExtension ? 'hidden' : ''} RxNorm Extension rows)</div>
                <Tooltip label="Toggle hiding of RxNorm Extension concepts">
                  <Switch sx={{margin: '-8px 0px'}} checked={!hideRxNormExtension}
                          onClick={() => hsDispatch({type:'hideRxNormExtension', hideRxNormExtension: !hideRxNormExtension})}
                  />
                </Tooltip>
              </div>
            : "Vocabulary"
        )
        // headerContentProps: { onClick: editCodesetFunc, codeset_id: cset_col.codeset_id, },
      },
      selector: (row) => row.vocabulary_id,
      // format: (row) => <Tooltip label={row.vocabulary_id} content={row.vocabulary_id} />,
      sortable: !nested,
      width: 100,
      style: { justifyContent: "center" },
    },
    {
      name: "Concept ID",
      selector: (row) => row.concept_id < 0 ? '' : row.concept_id,
      sortable: !nested,
      width: 80,
      style: { justifyContent: "center" },
    },
    {
      name: "Links",
      selector: (row) => row.concept_id,
      headerProps: {
        tooltipContent: (
          <span>Click icons to open the concept in ATLAS or Athena</span>
        ),
      },
      // TODO: @fabiofdez: after widening this column so (i) icon would display, the cells should be centered. can you figure out how to do that?
      format: (row) => (
        <span
          style={{
            height: sizes.linkHeight,
            display: "flex",
            flex: 1,
            justifyContent: "space-between",
            alignItems: "center",
          }}
        >
          <a
            href={`https://atlas-demo.ohdsi.org/#/concept/${row.concept_id}`}
            target="_blank"
            rel="noreferrer"
            style={{
              display: "flex",
              aspectRatio: 1,
              alignItems: "center",
              padding: "3px",
            }}
          >
            <img
              height={sizes.atlasHeight}
              src="atlas.ico"
              alt="Link to this concept in ATLAS"
            />
          </a>
          &nbsp;
          <a
            href={`https://athena.ohdsi.org/search-terms/terms/${row.concept_id}`}
            target="_blank"
            rel="noreferrer"
            style={{
              display: "flex",
              aspectRatio: 1,
              alignItems: "center",
              padding: "3px",
            }}
          >
            <img
              height={sizes.athenaHeight}
              src="athena.ico"
              alt="Link to this concept in Athena"
            />
          </a>
        </span>
      ),
      sortable: !nested,
      width: 60,
      style: {
        backgroundColor: "lightgray",
        paddingRight: "0px",
        display: "flex",
        flex: 1,
        justifyContent: "center",
      },
    },
    // ...cset_cols,
    {
      // name: "Patients",
      headerProps: {
        headerContent: (
            <div style={{display: 'flex', flexDirection: 'column'}}>
              <Tooltip label="Approximate distinct person count. Small counts rounded up to 20.">
                <div>Patients</div>
                {/*<div>{hideZeroCounts ? 'Unhide ' : 'Hide '} {hidden.zeroCount} rows</div>*/}
              </Tooltip>
              <Tooltip label={`Toggle hiding of ${hidden.zeroCount} concepts with 0 patients`}>
                <Switch sx={{margin: '-8px 0px'}} checked={!hideZeroCounts}
                  onClick={() => hsDispatch({type:'hideZeroCounts', hideZeroCounts: !hideZeroCounts})}
                />
              </Tooltip>
            </div>
        )
        // headerContentProps: { onClick: editCodesetFunc, codeset_id: cset_col.codeset_id, },
      },
      selector: (row) => {
        // can be comma=separated list if pt cnts in more than one domain
        const cnts = row.distinct_person_cnt.split(',').map(n => parseInt(n));
        return max(cnts);
      },
      format: (row) => {
        if (typeof(row.distinct_person_cnt) === 'undefined') {
          return '';
        }
        const cnts = row.distinct_person_cnt.split(',').map(n => parseInt(n));
        return fmt(max(cnts));
      },
      sortable: !nested,
      right: true,
      width: 80,
      // minWidth: 80,
      // remainingPct: .10,
      style: { justifyContent: "center" },
    },
    {
      name: "Records",
      headerProps: {
        tooltipContent: "Record count. Small counts rounded up to 20.",
      },
      /* name:   <Tooltip label="Record count. Small counts rounded up to 20.">
                <span>Records</span>
            </Tooltip>, */
      selector: (row) => row.total_cnt,
      format: (row) => {
        if (typeof(row.distinct_person_cnt) === 'undefined') {
            return '';
        }
        return fmt(row.total_cnt)
      },
      sortable: !nested,
      right: true,
      width: 80,
      // minWidth: 80,
      // remainingPct: .10,
      style: { justifyContent: "center" },
    },
  ];
  let cset_cols = selected_csets.map((cset_col) => {
    const { codeset_id } = cset_col;
    let def = {
      cset_col,
      codeset_id,
      headerProps: {
        showInfoIcon: !!nested,
        //tooltipContent: "Click to create and edit new draft of this concept set",
        tooltipContent: `${cset_col.codeset_id} ${cset_col.concept_set_version_title}.
                            ${nested ? 'Click for details' : 'Click to sort.'}`,
        //style: { cursor: 'pointer', },

        // headerContent: cset_col.concept_set_name,
        headerContent: (
            <span onClick={() => setShowCsetCodesetId(cset_col.codeset_id)}>
              {cset_col.concept_set_name}
            </span>
        ),
        headerContentProps: {
          codeset_id: cset_col.codeset_id,
        },
      },
      selector: row => {
        const item = getItem({ codeset_id: cset_col.codeset_id,
          concept_id: row.concept_id, csmi, newCset, }) || {};
        return !(item.item || item.csm);
      },
      format: (row) => {
        return cellContents({
          ...props,
          row,
          cset_col,
          editAction,
        });
      },
      conditionalCellStyles: [
        {
          when: (row) => true, //csmiLookup[codeset_id][row.concept_id],
          // when: row => row.checkboxes && row.checkboxes[codeset_id],
          style: (row) => cellStyle({ ...props, cset_col, row }),
        },
      ],
      sortable: !nested,
      // compact: true,
      width: 80,
      // center: true,
    };

    if (codeset_id === NEW_CSET_ID) {
      def.headerProps.headerContent = (
        <div style={{display: 'flex', flexDirection: 'column'}}>
          {/*<Tooltip label={def.headerProps.tooltipContent}>*/}
          {/*  <div>{def.headerProps.headerContent}</div>*/}
          {/*</Tooltip>*/}
          New concept set
          <Tooltip label="Discard">
            <IconButton
                onClick={() => {
                  newCsetDispatch({type: 'reset'});
                }}
            >
              <CloseIcon />
            </IconButton>
          </Tooltip>
        </div>);
      delete def.headerProps.tooltipContent;
    }

    return def;
  });

  coldefs = [...coldefs, ...cset_cols];
  // coldefs.forEach(d => {delete d.width; d.flexGrow=1;})
  // coldefs[0].grow = 5;
  // delete coldefs[0].width;
  coldefs = setColDefDimensions({ coldefs, windowSize });
  // console.log(coldefs);
  /*
  if (!nested) {
    delete coldefs[0].conditionalCellStyles;
  }
   */
  return coldefs;
}

function downloadCSV(props, tsv=false) {
  const {displayedRows, codeset_ids, selected_csets, csmi, } = props;
  const filename = 'thdownload-' + codeset_ids.join('-') + (tsv ? '.tsv' : '.csv');
  const maxLevel = max(displayedRows.map(r => r.level));
  const first_keys = ['Patients', 'Records', 'Vocabulary', 'Concept code'];
  const addedEmptyColumns = ['Include', 'Exclude', 'Notes'];
  const cset_keys = codeset_ids.map(id => selected_csets.find(cset => cset.codeset_id === id).concept_set_name);
  /*
      output columns will be:
        level (of indentation)
        level1, level2, ...   for indented concept names
        ...first_keys
        ...other keys (not first or last)
        ...selected concept set keys
        Concept name
        ...addedEmptyColumns
   */
  const excluded_keys = ['pathToRoot', 'hasChildren'];
  const key_convert = {
    'level': 'Level',
    'concept_code': 'Concept code',
    'concept_class_id': 'Concept class',
    'domain_id': 'Concept domain',
    'domain': 'Domain tables with concept',
    'domain_cnt': 'Domain count',
    'standard_concept': 'OMOP standard',
    'invalid_reason': 'Invalid reason',
    'distinct_person_cnt': 'Patients',
    'total_cnt': 'Records',
    'vocabulary_id': 'Vocabulary',
    'concept_id': 'Concept ID',
    'concept_name': 'Concept name',
  };

  const rows = displayedRows.map(r => {
    let row = {};
    // adds indented concept names to rows
    for (let i = 0; i <= maxLevel; i++) {
      row['level' + i] = (r.level === i ? r.concept_name : '');
    }
    // renames row properties to column names
    for (let k in r) {
      if (!excluded_keys.includes(k)) {
        row[key_convert[k]] = r[k];
      }
    }
    for (let j = 0; j < addedEmptyColumns.length; j++) {
      row[addedEmptyColumns[j]] = '';
    }
    codeset_ids.forEach((codeset_id, i) => {
      const item = csmi[codeset_id][r.concept_id];
      row[cset_keys[i]] = item ? textCellForItem(item) : '';
    });
    return row;
  });

  // specify the order of columns in csv
  let columns = ['Level'];
  for (let i = 0; i <= maxLevel; i++) {
    columns.push('level' + i);
  }
  columns.push(...first_keys);
  Object.keys(displayedRows[0]).forEach(k => {
    if (excluded_keys.includes(k) || k === 'concept_name') {
      return;
    }
    if (!first_keys.includes(k) && k !== 'level') {
      columns.push(key_convert[k]);
    }
  });
  columns.push(...cset_keys, 'Concept name', ...addedEmptyColumns);

  saveCsv(rows, columns, filename);
}

// createTheme creates a new theme named solarized that overrides the build in dark theme
// https://github.com/jbetancur/react-data-table-component/blob/master/src/DataTable/themes.ts
createTheme(
  "custom-theme",
  {
    text: {
      primary: "#268bd2",
      secondary: "#2aa198",
    },
    context: {
      background: "#cb4b16",
      text: "#FFFFFF",
    },
  },
  "light"
);

function styles(sizes) {
  return {
    /*
          tableWrapper: {
            style: {
              display: 'table',
            },
          },
        denseStyle: {
            minHeight: '2px',
        },
        */
    table: {
      style: {
        // maxWidth: '85%',
        // marginLeft: '20px',
        // maxWidth: '400px', doesn't work ?
      },
    },
    headCells: {
      style: {
        // transform: 'translate(10px,-15px) rotate(-45deg)',
        // transform: 'translate(0px,30px)',
        // height: '100%',
        // position: 'absolute',
        fontSize: "120%",
        overflow: "visible",
        // verticalAlign: 'bottom !important', // doesn't work
        marginTop: "auto",
        /*
                zIndex: 200,
                webkitAlignItems: 'end !important',
                alignItems: 'end !important',
                alignItemsFlexStart: 'end !important',
                display: 'inline !important',
                // textAlign: 'left',
                 */
        // setting height in .rdt_TableHeadRow works, but setting height here
        //  makes the header content align vertically in the center which is terrible
        // height: '180px',        // TODO: FIX!!!!
        padding: 0,
        // border: '3px solid green',
        // paddingLeft: '8px', // override the cell padding for head cells
        // paddingRight: '8px',
      },
    },
    rows: {
      style: {
        color: "black",
        minHeight: "0px", // override the row height    -- doesn't work, can only seem to do it from css
        padding: sizes.rowPadding,
        fontSize: sizes.rowFontSize,
        // height: '2px',
        // fontSize: '2px',
        // height: '3px',
        borderBottom: "1px solid #BBB",
      },
    },
    cells: {
      style: {
        minHeight: "0px", // override the row height
        // paddingLeft: '8px', // override the cell padding for data cells
        // paddingRight: '8px',
        padding: 0, //'0px 5px 0px 5px',
        borderRight: "1px solid #BBB",
      },
    },
  };
}
// const expandIcon    = <svg fill="currentColor" height="20" viewBox="0 -6 24 24" width="24" xmlns="http://www.w3.org/2000/svg"><path d="M8.59 16.34l4.58-4.59-4.58-4.59L10 5.75l6 6-6 6z"></path><path d="M0-.25h24v24H0z" fill="none"></path></svg>
// const collapseIcon  = <svg fill="currentColor" height="20" viewBox="0 -6 24 24" width="24" xmlns="http://www.w3.org/2000/svg"><path d="M7.41 7.84L12 12.42l4.59-4.58L18 9.25l-6 6-6-6z"></path><path d="M0-.75h24v24H0z" fill="none"></path></svg>
// const blankIcon     = <svg fill="currentColor" height="20" viewBox="0 -6 24 24" width="24" xmlns="http://www.w3.org/2000/svg" />
function SquishStuff() {
  // not using right now. wasn't fully working
  const [squishTo, setSquishTo] = useState(1);
  const tsquish = throttle((val) => {
    // console.log(`squish: ${squishTo} -> ${val}`);
    setSquishTo(val);
  }, 200);
  const squishChange = useCallback(tsquish, [squishTo, tsquish]);
}
function SquishSlider({ setSquish }) {
  // not refreshing... work on later
  function preventHorizontalKeyboardNavigation(event) {
    if (event.key === "ArrowLeft" || event.key === "ArrowRight") {
      event.preventDefault();
    }
  }
  function onChange(e, val) {
    // console.log('val: ', val);
    setSquish(val);
  }

  return (
    <Box /* sx={{ height: 300 }} */>
      <Slider
        // key={`slider-${squish}`}
        sx={{
          width: "60%",
          marginLeft: "15%",
          marginTop: "15px",
          // '& input[type="range"]': { WebkitAppearance: 'slider-vertical', },
        }}
        onChange={onChange}
        // onChangeCommitted={onChange}
        // orientation="vertical"
        min={0.01}
        max={2}
        step={0.1}
        // value={squish}
        defaultValue={1}
        aria-label="Squish factor"
        valueLabelDisplay="auto"
        onKeyDown={preventHorizontalKeyboardNavigation}
      />
    </Box>
  );
}

export { CsetComparisonPage };

export function howToSaveStagedChanges(params) {
  return (
      <>
        <ol>
          <LI>
            {params.atlasWidget}
            {/*<PRE>{atlasJson}</PRE>*/}
          </LI>
          <LI>
            Create a new concept set or new version of an existing concept in the{" "}
            <a href="https://unite.nih.gov/workspace/module/view/latest/ri.workshop.main.module.5a6c64c0-e82b-4cf8-ba5b-645cd77a1dbf"
               target="_blank" rel="noreferrer">
              enclave concept set editor
            </a>.
          </LI>
          <LI>
            When you get to the screen for editing the new draft version, you will see
            a blue button labelled "Add Concepts" on the upper right.
            Click the down arrow, then select "Import ATLAS Concept Set Expression
            JSON" from the menu.
          </LI>
          <LI>
            Paste the JSON copied into your clipboard from TermHub earlier into the box, and
            click "Import Atlas JSON".
          </LI>
          <LI>Click the version on the left again.</LI>
          <LI>On the right, click the green "Done" button.</LI>
        </ol>
        <p>
          Return to this work later by saving or bookmarking <a
            href={urlWithSessionStorage(params.newCset)} target="_blank" rel="noreferrer">this link</a> (
          <Button
              onClick={() => {
                navigator.clipboard.writeText(urlWithSessionStorage(params.newCset));
              }}
          >
            Copy to clipboard
          </Button>.)
          <br />
          Best practice is to paste this URL in your lab notebook and annotate
          your work there as well.
        </p>
      </>
  );
}