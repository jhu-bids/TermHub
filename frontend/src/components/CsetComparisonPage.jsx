import React, {
  useCallback,
  useEffect,
  useRef,
  useState,
  useMemo,
} from 'react';
import DataTable, {createTheme} from 'react-data-table-component';
import AddCircle from '@mui/icons-material/AddCircle';
import Download from '@mui/icons-material/Download';
import RemoveCircleOutline from '@mui/icons-material/RemoveCircleOutline';
import Box from '@mui/material/Box';
import IconButton from '@mui/material/IconButton';
import FormatListBulleted from '@mui/icons-material/FormatListBulleted';
import IndentedListIcon from '../assets/IndentedListIcon';
import Slider from '@mui/material/Slider';
// import Switch from '@mui/material/Switch';
import CloseIcon from '@mui/icons-material/Close';
import Button from '@mui/material/Button';
import {
  flatten,
  fromPairs,
  intersection,
  union,
  differenceWith,
  isEmpty,
  max,
  throttle,
  uniq,
  uniqBy,
  sum,
  get,
} from 'lodash';

import {dfs, dfsFromNode} from 'graphology-traversal/dfs';

import {
  fmt,
  saveCsv,
  useWindowSize,
  RIGHT_ARROW,
  NO_BREAK_SPACE,
} from '../utils';
import {Info} from "@mui/icons-material";
import {iconStyle, setColDefDimensions} from './dataTableUtils';
import {ConceptSetCard} from './ConceptSetCard';
import {Tooltip} from './Tooltip';
import {
  cellContents,
  cellStyle,
  Legend,
  newCsetAtlasWidget,
  textCellForItem,
  expandCset,
} from './NewCset';
import {FlexibleContainer} from './FlexibleContainer';
import {
  NEW_CSET_ID,
  urlWithSessionStorage, useCodesetIds,
  useGraphOptions, // useAppOptions,
  useNewCset, useCids, // useCompareOpt,
} from '../state/AppState';
import {GraphContainer, ExpandState} from '../state/GraphState';
import {getResearcherIdsFromCsets, useDataGetter} from '../state/DataGetter';
import {LI} from './AboutPage';
import {isEqual} from '@react-sigma/core';
// import {AddConcepts} from "./AddConcepts";

// TODO: Find concepts w/ good overlap and save a good URL for that
// TODO: show table w/ hierarchical indent
// TODO: Color table: I guess would need to see if could pass extra values/props and see if table widget can use that
//  ...for coloration, since we want certain rows grouped together
export async function fetchGraphData(props) {
  let {dataGetter, codeset_ids=[], cids=[], newCset = {}} = props;
  let promises = [ // these can run immediately
    dataGetter.fetchAndCacheItems(dataGetter.apiCalls.cset_members_items, codeset_ids),
    dataGetter.fetchAndCacheItems(dataGetter.apiCalls.csets, codeset_ids),
  ];
  // have to get concept_ids before fetching concepts
  let newCsetCids = [];
  if (!isEmpty(newCset)) {
    newCsetCids = Object.keys(newCset.definitions).map(d => parseInt(d));
  }
  cids = union(cids, newCsetCids);
  const graphData = await dataGetter.fetchAndCacheItems(
      dataGetter.apiCalls.concept_graph_new, {codeset_ids, cids});
  let {concept_ids} = graphData;

  promises.push(
      dataGetter.fetchAndCacheItems(dataGetter.apiCalls.concepts, concept_ids));

  let [csmi, selected_csets, conceptLookup] = await Promise.all(promises);

  /*
  let comparison_rpt;
  if (codeset_ids.length === 2) {
    const pcids = codeset_ids.sort().join('-');
    let compareOpt = false;
    if (compareOpt === 'compare-precalculated') {
      comparison_rpt = dataGetter.axiosCall(
          `single-n3c-comparison-rpt?pair=${codeset_ids.join('-')}`,
          {sendAlert: false, skipApiGroup: true});
    } else if (compareOpt === 'real-time-comparison') {
      throw new Error("haven't implemented real-time-comparison yet");
    } else {
      // throw new Error(`invalid compareOpt: ${compareOpt}`);
    }

    if (comparison_rpt) {
      comparison_rpt = await comparison_rpt;
      specialConcepts.added = comparison_rpt.added.map(d => d.concept_id + '');
      specialConcepts.removed = comparison_rpt.removed.map(d => d.concept_id + '');
    }
  }
 */
  /*
  // just for screenshot
  let x = csmi[718894835][4153380];
  x.item = true;
  x.csm = false;
  x.flags = 'DX';
  x.item_flags = "includeDescendants,isExcluded";
  x.includeDescendants = true;
  x.isExcluded = true;
   */

  selected_csets = codeset_ids.map(d => selected_csets[d]); // to get them in the order asked for

  if (!isEmpty(newCset)) {
    selected_csets.push(newCset);
    csmi[newCset.codeset_id] = newCset.definitions;
    // these will be modified once the concept graph is constructed
  }

  const concepts = Object.values(conceptLookup);

  const definitionConcepts = uniq(flatten(
      Object.values(csmi).map(d => Object.values(d)),
  ).filter(d => d.item).map(d => d.concept_id));

  const nonDefinitionConcepts = uniq(flatten(
      Object.values(csmi).map(d => Object.values(d)),
  ).filter(d => !d.item).map(d => d.concept_id));

  const rxNormExtension = concepts.filter(d => d.vocabulary_id === 'RxNorm Extension').map(d => d.concept_id);

  let specialConcepts = {
    definitionConcepts: definitionConcepts.map(String),
    nonDefinitionConcepts: nonDefinitionConcepts.map(String),
    standard: uniq(Object.values(conceptLookup).
        filter(c => c.standard_concept).
        map(c => c.concept_id)),
    nonStandard: uniq(Object.values(conceptLookup).
        filter(c => !c.standard_concept).
        map(c => c.concept_id)),
    zeroRecord: uniq(Object.values(conceptLookup).
        filter(c => !c.total_cnt).
        map(c => c.concept_id)),
    addedCids: cids.map(String),
    rxNormExtension: rxNormExtension.map(String),
  };

  return {
    ...graphData,
    concept_ids,
    selected_csets,
    conceptLookup,
    csmi,
    concepts,
    specialConcepts,
  };
}

export function CsetComparisonPage() {
  const [codeset_ids] = useCodesetIds();
  const [cids, cidsDispatch] = useCids();
  const [newCset, newCsetDispatch] = useNewCset();
  const [api_call_group_id, setApiCallGroupId] = useState();
  const [showRowInfo, setShowRowInfo] = useState();
  let [graphOptions, graphOptionsDispatch] = useGraphOptions();

  const editingCset = !isEmpty(newCset);
  // const { selected_csets = [], researchers, } = cset_data;
  const dataGetter = useDataGetter();
  const windowSize = useWindowSize();
  const infoPanelRef = useRef();
  const countRef = useRef({n: 1, z: 10});
  const [panelPosition, setPanelPosition] = useState({x: 0, y: 0});
  const [showCsetCodesetId, setShowCsetCodesetId] = useState(null); // when you click cset col heading, shows card for that cset
  const sizes = getSizes(/*squishTo*/ 1);
  const customStyles = styles(sizes);

  const [data, setData] = useState({});
  const {
    gc, displayedRows,
    concepts,
    concept_ids,
    conceptLookup,
    selected_csets,
    csmi,
    researchers,
    // currentUserId,
    specialConcepts,
  } = data;

  useEffect(() => {
    (async () => {
      const id = await dataGetter.getApiCallGroupId();
      setApiCallGroupId(id);
    })();
  }, []);

  useEffect(() => {
    (async () => {
      if (typeof (api_call_group_id) === 'undefined') return;
      if (!graphOptions) return;

      // let whoami = dataGetter.fetchAndCacheItems(dataGetter.apiCalls.whoami, undefined);

      const graphData = await fetchGraphData({
        dataGetter,
        graphOptions,
        // compareOpt,
        codeset_ids,
        cids,
        newCset,
      });

      let {
        concept_ids,
        selected_csets,
        conceptLookup,
        csmi,
        concepts,
        specialConcepts,
      } = graphData;

      // let _gc = new GraphContainer({ ...graphData, concepts, specialConcepts, csmi });
      //  that looks redundant, unneeded. fixing now but not testing. hopefully won't break anything:
      let _gc = new GraphContainer(graphData);
      if (newCset) {
        const expansion = await expandCset({newCset, graphContainer: _gc});
        csmi[newCset.codeset_id] = expansion;
      }

      const {allRows, allRowsById} = _gc.setupAllRows(_gc.roots);

      /* call setGraphDisplayConfig, then getDisplayedRows,
       * then setGraphDisplayConfig again, so
       *    1) get graphOptions from state if any are saved or create them
       *       from defaults
       *    2) figure out displayedRows accordingly
       *    3) set counts for StatsAndOptions table accordingly
       */
      let displayedRows = [];
      _gc.setGraphDisplayConfig(graphOptions, allRows, displayedRows);

      displayedRows = _gc.getDisplayedRows(graphOptions, allRows, allRowsById);

      _gc.setGraphDisplayConfig(graphOptions, allRows, displayedRows);

      // const currentUserId = (await whoami).id;
      const researcherIds = getResearcherIdsFromCsets(selected_csets);
      let researchers = await dataGetter.fetchAndCacheItems(
          dataGetter.apiCalls.researchers, researcherIds);

      setData(current => ({
        ...current,
        concept_ids,
        selected_csets,
        conceptLookup,
        csmi,
        concepts,
        researchers,
        // currentUserId,
        specialConcepts,
        gc: _gc,
        displayedRows,
      }));
    })();
  }, [newCset, graphOptions, api_call_group_id]); // todo: why api_call_group_id here? still needed?

  useEffect(() => {
    // if (process.env.NODE_ENV === 'test') {
      window.getGraphOptions = () => graphOptions;
      window.dispatchGraphOptions = (action) => graphOptionsDispatch(action);
    // }
  }, [graphOptions, graphOptionsDispatch]);

  useEffect(() => {
    if (infoPanelRef.current) {
      // I think the purpose of this is to set y position of first displayed (open)
      //  panel (FlexibleContainer) to be a short distance below the bar that shows
      //  the buttons
      let margin_text = window.getComputedStyle(infoPanelRef.current).
          getPropertyValue('margin-bottom');
      margin_text = margin_text.substring(0, margin_text.length - 2);
      const margin = parseInt(margin_text);

      setPanelPosition({
        x: 0,
        y: infoPanelRef.current.clientHeight + 2 * margin,
      });
    }
  }, [
    infoPanelRef.current,
    (infoPanelRef.current ? infoPanelRef.current.offsetHeight : 0)]);

  const atlasWidget = useMemo(() =>
      !isEmpty(newCset) && !isEmpty(conceptLookup) &&
      newCsetAtlasWidget(newCset, conceptLookup), [newCset, conceptLookup]);

  if (!gc || isEmpty(graphOptions) || isEmpty(displayedRows) ||
      isEmpty(concepts)) {
    // sometimes selected_csets and some other data disappears when the page is reloaded
    return <p>Downloading...</p>;
  }

  const colDefs = getColDefs({
    gc,
    selected_csets,
    concepts,
    cids,
    sizes,
    windowSize,
    // hidden,
    displayedRows,
    graphOptions,
    graphOptionsDispatch,
    csmi,
    newCset, newCsetDispatch,
    setShowCsetCodesetId,
  });

  let csetCard = null;
  if (showCsetCodesetId) {
    const cset = selected_csets.find(d => d.codeset_id == showCsetCodesetId);
    csetCard = (
        <FlexibleContainer id="csetCard" key="csetCard" openOnly={true}
                           title={cset.concept_set_version_title}
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

  const graphDisplayOptionsWidth = 825;
  const graphDisplayOptionsHeight = gc.graphDisplayConfigList.length *
      31 + 40;
  let infoPanels = [
    <IconButton
        key="toggle-nested"
        sx={{ bgcolor: 'primary.main', '&:hover': { bgcolor: 'primary.dark' },
           cursor: 'pointer', marginRight: '4px', color: 'white', borderRadius: 1, }}
        onClick={() => {
          graphOptionsDispatch({type: 'toggle-nested'});
          if (!graphOptions.nested) {
            // trying to force the table back to unsorted after toggling nesting back on
            window.location.reload();
            /* setData(current => ({  // this didn't work
              ...current,
              displayedRows: [...current.displayedRows.slice(1)]
            })) */
          }
        }}
        title= { graphOptions.nested
            ? "Switch display to unindented list. Allows sorting whole list."
            : "Switch display to indented list. Each level sorted by record count descending."
        }
    >
      { graphOptions.nested
          ? <FormatListBulleted sx={{ color: 'white', display: { xs: "none", md: "flex" }, mr: 1 }} />
          : <IndentedListIcon size={24} color="white" /> }
    </IconButton>,

    <FlexibleContainer id="stats-options" key="stats-options" title="Stats and options"
                       position={panelPosition} countRef={countRef}
                       style={{
                         minWidth: graphDisplayOptionsWidth + 'px',
                         resize: 'both',
                         minHeight: graphDisplayOptionsHeight + 'px',
                       }}
    >
      <StatsAndOptions {...{
        gc,
        graphOptions,
        graphOptionsDispatch,
        graphDisplayOptionsWidth,
        customStyles,
      }} />
    </FlexibleContainer>,

    /*
    <FlexibleContainer key="add-concept" title="Add concepts"
                       position={panelPosition} countRef={countRef}
                       style={{width: "90%", resize: "both", }}
    >
        {/*<AddConcepts {...{gc, customStyles}} />* /}
    </FlexibleContainer>,
    */

    /*
    <Button key="distinct"
            disabled={!nested}
            onClick={() => graphOptionsDispatch({type:'nested', nested: false})}
            sx={{
              marginRight: '4px',
              display: "flex",
              flexDirection: "row",
            }}
    >
      {distinctRows.length} distinct concepts
    </Button>,
    */
    /*
    <Button key="download-distinct-tsv"
            variant="contained"
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
            variant="contained"
            onClick={() => downloadCSV({
              codeset_ids,
              displayedRows: gc.wholeHierarchy(),
              selected_csets,
              csmi,
            })}
            sx={{
              cursor: 'pointer',
              marginRight: '4px',
            }}
    >
      CSV <Download></Download>
    </Button>,

    <Button key="add-cset"
            variant="contained"
            onClick={() => {
              newCsetDispatch({type: 'createNewCset'});
            }}
            sx={{
              cursor: 'pointer',
              marginRight: '4px',
              display: editingCset ? 'none' : 'flex',
            }}
    >
      Create new concept set or version
    </Button>,
  ];

  let edited_cset;
  if (editingCset) {
    infoPanels.push(
        <FlexibleContainer id="cset" key="cset" title="New concept set"
                           startHidden={true}
                           hideShowPrefix={true}
                           style={{width: '80%', resize: 'both'}}
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
              styles={{position: 'absolute'}}
          />
        </FlexibleContainer>,
    );

    infoPanels.push(
        <FlexibleContainer id="instructions" key="instructions"
                           title="Instructions to save new concept set"
                           style={{width: '600px', resize: 'both'}}
                           position={panelPosition} countRef={countRef}>
          {howToSaveStagedChanges({newCset, atlasWidget})}
        </FlexibleContainer>,
    );
  }

  infoPanels.push(
      <FlexibleContainer id="legend" key="legend" title="Legend" position={panelPosition}
                         countRef={countRef}>
        <Legend editing={editingCset}/>
      </FlexibleContainer>,
  );

  if (showRowInfo) {
    const row = showRowInfo;
    console.log(row);
    const concept = conceptLookup[row.concept_id];

    // paths = all paths to concept in displayedRows
    let conceptPaths = displayedRows
      .filter(d => d.concept_id == row.concept_id)
        // remove initial /, split into concept_ids
      .map(d => d.rowPath.slice(1).split('/'));

    let paths = conceptPaths
        // replace concept_ids with names, join with →
      .map(path => path.map(c => conceptLookup[c]?.concept_name || c).join(RIGHT_ARROW))
      // add spaces at end so window border doesn't touch text
      .map(path => path + NO_BREAK_SPACE + NO_BREAK_SPACE);

    console.log(selected_csets);
    let items = selected_csets.map(
        cset => {
          let item = csmi[cset.codeset_id][row.concept_id];
          if (!item) return;
          item = {
            ...item,
            codesetName: cset.concept_set_version_title,
          };
          console.log(item);
          if (item.descendantOf) {
            if (Number.isInteger(item.descendantOf)) {
              let ancestor = csmi[cset.codeset_id][item.descendantOf];
              if (ancestor?.includeDescendants) {
                item.descendantOf = {...ancestor, ...conceptLookup[ancestor.concept_id] };
              }
            } else {
              throw new Error("wasn't expecting this");
            }
          } else {
            // let's try to find definition this item descended from
            for (const path of conceptPaths) {
              for (const concept_id of path.reverse()) {
                let ancestor = csmi[cset.codeset_id][concept_id];
                if (ancestor?.includeDescendants) {
                  item.descendantOf = ancestor;
                  break;
                }
              }
              if (item.descendantOf) break;
            }
          }
          return item;
        }).filter(d => d);

    infoPanels.push(
        <FlexibleContainer id="rowInfo" key="rowInfo" title={concept.concept_name}
                           closeAction={() => setShowRowInfo(undefined)}
                           startHidden={false}
                           hideShowPrefix={true}
                           style={{midWidth: '500px', minHeight: '200px', resize: 'both'}}
                           position={panelPosition}
                           countRef={countRef}>
          <ul>
            <li>Concept <strong>{concept.concept_id}</strong> appears at these paths</li>
            <ul>
              {paths.map((p, i) => <li key={i}>{p}</li>)}
            </ul>
            {items.filter(d => d).map((item, i) => (
                <li key={i}>
                  In {item.codesetName} this concept is
                  <ul style={{paddingLeft: '2em'}}>
                    <li>{textCellForItem(item, true)}</li>
                    {
                      item.descendantOf
                        ? <li>Descended from{' '}
                            <strong>{item.descendantOf.concept_id} {item.descendantOf.concept_name}</strong>
                            {' '}<em>{textCellForItem(item.descendantOf, true, true)}</em>
                          </li>
                          : null
                    }
                  </ul>
                </li>
            ))}
          </ul>
        </FlexibleContainer>
    );
  }

  const tableProps = {
    rowData: displayedRows,
    columns: colDefs,
    selected_csets,
    customStyles,
    setShowRowInfo,
  };
  return (
      <div style={{margin: 10}}>
        <span data-testid="comp-page-loading"></span>
        {csetCard}
        <Box
            ref={infoPanelRef}
            sx={{
              width: '96%',
              margin: '9px',
              display: 'flex',
              flexDirection: 'row',
            }}
        >
          {infoPanels}
        </Box>
        <ComparisonDataTable /*squishTo={squishTo}*/ {...tableProps} />
        <span data-testid="comp-page-loaded"></span>
      </div>
  );
}

function StatsAndOptions(props) {
  const {
    gc,
    graphOptions,
    graphOptionsDispatch,
    graphDisplayOptionsWidth,
    customStyles,
  } = props;
  const infoPanelRef = useRef();
  let coldefs = [
    {
      name: 'Concept group',
      selector: (row) => row.name,
      style: {paddingLeft: 4},
    },
      // columns: Visible, Hidden -- concepts
      // columns: Visible, Hidden -- rows, but not now
    {
      name: 'Total',
      selector: (row) => row.total,
      format: (row) => fmt(row.total),
      width: 80,
      style: {justifyContent: 'right', paddingRight: 4},
    },
    {
      name: 'Visible',
      selector: (row) => row.displayedConceptCnt,
      format: (row) => fmt(row.displayedConceptCnt),
      width: 80,
      style: {justifyContent: 'right', paddingRight: 4},
    },
    {
      name: 'Hidden',
      selector: (row) => row.hiddenConceptCnt,
      format: (row) => fmt(row.hiddenConceptCnt),
      width: 80,
      style: {justifyContent: 'right', paddingRight: 4},
    },
    {
      name: 'State',
      selector: (row) => (graphOptions.specialConceptTreatment[row.type] || '').toString(),
      width: 80,
      style: {justifyContent: 'right', paddingRight: 4},
    },
    {
      name: 'Action',
      selector: (row) => row.specialTreatment,
      format: (row) => {
        let text = '';
        let tttext = '';

        let onClick = () => graphOptionsDispatch({gc, type: 'TOGGLE_OPTION', specialConceptType: row.type});

        if (row.type === 'concepts') {
          onClick = () => {
            graphOptionsDispatch({gc, type: 'TOGGLE_EXPAND_ALL'});
          };
          text = get(graphOptions, 'expandAll') ? 'Collapse all' : 'Expand all';
          tttext = 'Does not affect rows hidden or shown by other options';
        } else if (graphOptions.specialConceptTreatment[row.type] === 'hidden') {
          text = 'unhide';
        } else if (graphOptions.specialConceptTreatment[row.type] === 'shown') {
          text = 'hide';
        } else {
          throw new Error('shouldn\'t be here');
        }
        let button = (
            <Button key="stats"
                    onClick={onClick}
                    sx={{
                      marginRight: '4px',
                      display: 'flex',
                      flexDirection: 'row',
                    }}
            >
              {text}
            </Button>
        );
        // return button;
        if (tttext) {
          return (
              <Tooltip label={tttext} onClick={onClick}>
                {button}
              </Tooltip>);
        }
        return button;
      },
      width: 120,
      style: {justifyContent: 'center'},
    },
  ];
  const totalWidthOfOthers = sum(coldefs.map(d => d.width));
  coldefs[0].width = graphDisplayOptionsWidth - totalWidthOfOthers - 15;
  for (let def of coldefs) {
    def.width = def.width + 'px';
  }

  return (
      <DataTable
          className="stats-and-options"
          customStyles={customStyles}
          columns={coldefs}
          data={gc.graphDisplayConfigList}
          dense
      />
  );
}

function nodeToTree(node) { // Not using
  // a flat tree
  const subTrees = node.childIds().map(n => nodeToTree(n));
  return [node, ...subTrees];
}

function getCollapseIconAndName(
    row, name, sizes, graphOptions, graphOptionsDispatch, gc) {
  let Component;
  let direction;
  if (graphOptions.specificPaths[row.rowPath] === ExpandState.COLLAPSE) {
    // show (+) if this row is collapsed
    Component = AddCircle;
    direction = ExpandState.EXPAND;
  } else if ( // show (-) if
      // expandAll and not collapsed
      ( graphOptions.expandAll &&
        graphOptions.specificPaths[row.rowPath] !== ExpandState.COLLAPSE
      )
      // or expanded
      || graphOptions.specificPaths[row.rowPath] === ExpandState.EXPAND
      // or expand all
      || graphOptions.specificPaths[row.rowPath] === ExpandState.EXPAND_ALL
      // or child of expand all
      || row.display.showReasons.childOfExpandAll
  ) {
    Component = RemoveCircleOutline;
    direction = ExpandState.COLLAPSE;
  } else {
    // otherwise (+)
    Component = AddCircle;
    direction = ExpandState.EXPAND;
  }

  // Click handling variables
  let clickTimeout = null;

  const handleClick = (evt) => {
    graphOptionsDispatch({
      gc,
      type: 'TOGGLE_NODE_EXPANDED',
      rowPath: row.rowPath,
      direction,
    });
    return;
    // code for double clicking commented out. some weird edge cases and slight lag
    if (clickTimeout) {
      // If we get here, it's a double click
      clearTimeout(clickTimeout);
      clickTimeout = null;

      // Handle double click - expand descendants
      graphOptionsDispatch({
        type: "TOGGLE_NODE_EXPANDED",
        rowPath: row.rowPath,
        direction: direction === ExpandState.EXPAND ? ExpandState.EXPAND_ALL : ExpandState.COLLAPSE,
        gc
      });
    } else {
      // Single click - wait to see if double click comes
      clickTimeout = setTimeout(() => {
        // If we get here, it was a single click
        clickTimeout = null;
        graphOptionsDispatch({
          gc,
          type: 'TOGGLE_NODE_EXPANDED',
          rowPath: row.rowPath,
          direction,
        });
      }, 200);
    }
  };

  return (
      <span
          className="toggle-collapse concept-name-row"
          onClick={handleClick}
          // Remove onDoubleClick since we're handling it in onClick
      >
                <Component
                    sx={{
                      fontSize: sizes.collapseIcon,
                      display: 'inline-flex',
                      marginRight: '0.15rem',
                      marginTop: '0.05rem',
                      verticalAlign: 'top',
                    }}
                />
        <span className="concept-name-text">{name}</span>
      </span>
  );
}

function getColDefs(props) {
  let {
    gc,
    selected_csets,
    concepts,
    cids,
    sizes,
    windowSize,
    hidden,
    displayedRows,
    graphOptions,
    graphOptionsDispatch,
    csmi,
    newCset, newCsetDispatch,
    setShowCsetCodesetId,
  } = props;
  const {nested, } = graphOptions;

  let coldefs = [
    {
      name: 'Concept name',
      selector: (row) => row.concept_name,
      format: (row) => {
        let name = row.concept_name;
        // debugging show/hide:
        // name += ` --- ${Object.keys(row.display.hideReasons).join(', ')}; ${Object.keys(row.display.showReasons).join(', ')} ${row.display.result}`;
        let content = nested ? (
            row.hasChildren
                ? getCollapseIconAndName(row, name, sizes, graphOptions,
                    graphOptionsDispatch, gc)
                : (
                    <span className="concept-name-row">
                                {/*<RemoveCircleOutline
                                    // this is just here so it indents the same distance as the collapse icons
                                    sx={{fontSize: sizes.collapseIcon, visibility: "hidden"}} /> */}
                      <span className="concept-name-text">{name}</span>
                            </span>)
        ) : (
            <span className="concept-name-text">{name}</span>
        );
        return content;
      },
      sortable: !nested,
      // minWidth: 100,
      // remainingPct: .60,
      // WIDTH IS CALCULATED BELOW coldefs ASSIGNMENT BELOW AND IS
      //  WINDOW WIDTH MINUS WIDTHS OF ALL OTHER COLUMNS
      wrap: true,
      compact: true,
      conditionalCellStyles: [
        {
          when: (row) => true,
          style: (row) => ({
            padding: '0px 3px 0px ' +
                (nested
                    ? (9 + row.depth * 19 + (row.hasChildren ? 0 : 8))
                    : 19) +
                'px',
          }),
        },
      ],
    },
    {
      name: 'Levels below',
      headerProps: {
        tooltipContent: 'Levels of descendants below.',
      },
      selector: (row) => row.levelsBelow,
      format: (row) => {
        return fmt(row.levelsBelow || '');
      },
      sortable: false,
      right: true,
      width: 63,
      style: {justifyContent: 'right', paddingRight: 4},
    },
    {
      name: 'Child / descendant concepts',
      headerProps: {
        tooltipContent: 'Counts of direct child and descendant concepts.',
      },
      selector: (row) => row.descendantCount,
      format: (row) => {
        let text = fmt(row.childCount) + ' / ' + fmt(row.descendantCount);
        return text;
      },
      sortable: false,
      width: 80,
      style: {justifyContent: 'center'},
    },
    {
      name: 'Patients',
      headerProps: {
        tooltipContent: 'Approximate distinct person count. Small counts rounded up to 20.',
        /*
        headerContent: (
          <div style={{ display: 'flex', flexDirection: 'column' }}>
            <Tooltip
              label="Approximate distinct person count. Small counts rounded up to 20.">
              <div>Patients</div>
            </Tooltip>
            {
              hidden          // not currently being used
                ? <Tooltip
                  label={`Toggle hiding of ${hidden.zeroCount} concepts with 0 patients`}>
                  <Switch sx={{ margin: '-8px 0px' }} checked={!hideZeroCounts}
                          onClick={() => graphOptionsDispatch({          // not currently being used
                            type: 'hideZeroCounts',
                            hideZeroCounts: !hideZeroCounts,
                          })}
                  />
                </Tooltip>
                : ''
            }
          </div>
        ), */
        // headerContentProps: { onClick: editCodesetFunc, codeset_id: cset_col.codeset_id, },
      },
      selector: (row) => {
        // can be comma=separated list if pt cnts in more than one domain
        const cnts = row.distinct_person_cnt.split(',').map(n => parseInt(n));
        return max(cnts);
      },
      format: (row) => {
        if (typeof (row.distinct_person_cnt) === 'undefined') {
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
      style: {justifyContent: 'center'},
    },
    {
      // name: "Records",
      headerProps: {
        tooltipContent: 'Record count. Small counts rounded up to 20. Click to toggle hiding of zero counts.',
        headerContent: (
            <span onClick={() => graphOptionsDispatch(       // is still active, at least on dev
                {
                  gc,
                  type: 'TOGGLE_OPTION',
                  specialConceptType: 'zeroRecord',
                })}
                  style={{cursor: 'pointer'}}
            >
                      Records
                    </span>
        ),
      },
      /* name:   <Tooltip label="Record count. Small counts rounded up to 20.">
                <span>Records</span>
            </Tooltip>, */
      selector: (row) => row.total_cnt,
      format: (row) => {
        return fmt(row.total_cnt || '');
      },
      sortable: !nested,
      right: true,
      width: 80,
      // minWidth: 80,
      // remainingPct: .10,
      style: {justifyContent: 'right', paddingRight: 4},
    },
    {
      name: 'DRC',
      headerProps: {
        tooltipContent: 'Sum of descendant concept record counts.',
      },
      selector: (row) => row.drc,
      format: (row) => {
        return fmt(row.drc || '');
      },
      sortable: false,
      right: true,
      width: 80,
      style: {justifyContent: 'right', paddingRight: 4},
    },
    {
      name: "Vocabulary",
      selector: (row) => row.vocabulary_id,
      sortable: !nested,
      width: 100,
      style: {justifyContent: 'center'},
    },
    {
      name: 'Domain',
      selector: (row) => row.domain_id,
      sortable: !nested,
      width: 90,
      style: {justifyContent: 'center'},
    },
    {
      name: 'Class',
      selector: (row) => row.concept_class_id,
      sortable: !nested,
      width: 90,
      style: {justifyContent: 'center'},
    },
    {
      name: 'Std',
      selector: (row) => row.standard_concept,
      sortable: !nested,
      width: 30,
      style: {justifyContent: 'center'},
    },
    {
      name: 'Concept ID',
      selector: (row) => row.concept_id < 0 ? '' : row.concept_id,
      format: (row) => cids.includes(row.concept_id) ?
          <em>{row.concept_id < 0 ? '' : row.concept_id}</em> :
          row.concept_id < 0 ? '' : row.concept_id,
      sortable: !nested,
      width: 80,
      style: {justifyContent: 'center'},
    },
    {
      name: 'Links',
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
                display: 'flex',
                flex: 1,
                justifyContent: 'space-between',
                alignItems: 'center',
              }}
          >
                    <a
                        href={`https://atlas-demo.ohdsi.org/#/concept/${row.concept_id}`}
                        target="_blank"
                        rel="noreferrer"
                        style={{
                          display: 'flex',
                          aspectRatio: 1,
                          alignItems: 'center',
                          padding: '3px',
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
                  display: 'flex',
                  aspectRatio: 1,
                  alignItems: 'center',
                  padding: '3px',
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
        backgroundColor: 'lightgray',
        paddingRight: '0px',
        display: 'flex',
        flex: 1,
        justifyContent: 'center',
      },
    },
    // ...cset_cols,
  ];
  let cset_cols = selected_csets.map((cset_col) => {
    const {codeset_id} = cset_col;
    let def = {
      cset_col,
      codeset_id,
      headerProps: {
        //tooltipContent: "Click to create and edit new draft of this concept set",
        tooltipContent: `${cset_col.codeset_id} ${cset_col.concept_set_version_title}.
                            ${nested ? 'Click for details' : 'Click to sort.'}`,

        // headerContent: cset_col.concept_set_name,
        headerContent: (
            <span onClick={() => setShowCsetCodesetId(cset_col.codeset_id)}
                // not working for ellipsis; TODO: fix this later
                  style={{
                    cursor: 'pointer',
                    overflow: 'hidden',
                    textOverflow: 'ellipsis',
                  }}
            >
                      {cset_col.concept_set_name}
                    </span>
        ),
        headerContentProps: {
          codeset_id: cset_col.codeset_id,
        },
      },
      selector: row => {
        const item = get(csmi, [cset_col.codeset_id, row.concept_id]) || {};
        return !(item.item || item.csm);  // why?
      },
      format: (row) => {
        return cellContents({
          ...props,
          row,
          cset_col,
        });
      },
      conditionalCellStyles: [
        {
          when: (row) => true, //csmiLookup[codeset_id][row.concept_id],
          // when: row => row.checkboxes && row.checkboxes[codeset_id],
          style: (row) => cellStyle({...props, cset_col, row}),
        },
      ],
      sortable: !nested,
      // compact: true,
      width: 97,
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
                <CloseIcon/>
              </IconButton>
            </Tooltip>
          </div>);
      delete def.headerProps.tooltipContent;
    }

    return def;
  });

  coldefs = [...coldefs, ...cset_cols];

  // add pointer style to everything so users know they can click anywhere
  //  on row for row info
  coldefs = coldefs.map(d => ({
    ...d, style: {...(d.style ?? {}), cursor: 'pointer' }
  }));

  // concept name takes up remaining window width after all other columns
  const totalWidthOfOthers = sum(coldefs.map(d => d.width));

  /*
  coldefs[0].width = Math.min((620 + selected_csets.length * 80) * 1.5, // this part makes no sense, why was it like this?
      window.innerWidth - 620 - selected_csets.length * 80) - 36;
   */
  coldefs[0].width = // Math.min(totalWidthOfOthers * 1.5,
      window.innerWidth - totalWidthOfOthers - 60;
  // coldefs.forEach(d => {delete d.width; d.flexGrow=1;})
  // coldefs[0].grow = 5;
  // delete coldefs[0].width;
  coldefs = setColDefDimensions({coldefs, windowSize});
  // console.log(coldefs);
  /*
  if (!nested) {
    delete coldefs[0].conditionalCellStyles;
  }
   */
  return coldefs;
}

function ComparisonDataTable(props) {
  const {
    columns,
    newCset = {},
    customStyles,
    rowData,
    setShowRowInfo,
    /* squishTo = 1, cset_data, displayedRows, selected_csets */
  } = props;
  const infoPanelRef = useRef();

  useEffect(() => {
    for (let i = 0; i < columns.length; i++) {
      const el = document.querySelector(
          '.comparison-data-table .rdt_TableHeadRow ' +
          `> .rdt_TableCol[data-column-id=\"${i + 1}\"]`,
      );
      if (el) {
        el.style.width = columns[i].width + 'px';
      }
    }
  });

  const conditionalRowStyles = [
    {
      when: () => true,
      style: (row) => ({
        backgroundColor:
            row.removed && '#F662' ||
            row.added && '#00FF0016' ||
            '#FFF', // row.isItem && '#33F2' || '#FFF',
        opacity: row.nodeOccurrence > 0 ? .4 : 1,
        // backgroundColor: row.concept_id in definitions ? "#F662" : "#FFF",
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
          onRowClicked={row => {
            setShowRowInfo(row);
          }}
          dense
          fixedHeader
          fixedHeaderScrollHeight={() => {
            // console.log(infoPanelRef.current);
            const MuiAppBar = document.querySelector('.Mui-app-bar');
            let headerMenuHeight = 64;
            if (MuiAppBar) {
              headerMenuHeight = MuiAppBar.clientHeight;
            }
            const {offsetTop = 0, offsetHeight = 0} = infoPanelRef.current ??
            {};
            return (
                window.innerHeight -
                (headerMenuHeight + offsetTop + offsetHeight) +
                'px'
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
    rowFontSize: 13 * squishTo + 'px',
    // rowPadding:   ( 1 * squishTo) + 'px', // do these do anything?
    // rowPaddingTop:   ( 4 * squishTo) + 'px',
    // rowPaddingBottom:   ( 0 * squishTo) + 'px',
    collapseIcon: 13 * squishTo + 'px',
    linkHeight: 20 * squishTo + 'px',
    atlasHeight: 14 * squishTo + 'px',
    athenaHeight: 12 * squishTo + 'px',
  };
  return sizes;
}

function downloadCSV(props, tsv = false) {
  const {displayedRows, codeset_ids, selected_csets, csmi,
          separateLevels = false, includeNotesColumns = false, } = props;
  const filename = 'thdownload-' + codeset_ids.join('-') +
      (tsv ? '.tsv' : '.csv');
  const maxLevel = max(displayedRows.map(r => r.depth));
  const key_convert = {
    'depth': 'Level',
    'concept_name': 'Concept name',
    'concept_code': 'Concept code',
    'concept_id': 'Concept ID',
    'domain_id': 'Concept domain',
    'domain': 'Domain tables with concept',
    'domain_cnt': 'Domain count',
    'standard_concept': 'OMOP standard',
    'invalid_reason': 'Invalid reason',
    'distinct_person_cnt': 'Patients',
    'total_cnt': 'Records',
    'vocabulary_id': 'Vocabulary',
    'concept_class_id': 'Concept class',
    'added': 'Added',
    'removed': 'Removed',
    'childCount': 'Child count',
    'descendantCount': 'Descendant count',
    'drc': 'Descendant record count',
    'levelsBelow': 'Descendant levels',
  };
  // const first_keys = ['Patients', 'Records', 'Vocabulary', 'Concept code'];
  // first_keys things wasn't working. just commented out in case want to fix it later
  let addedEmptyColumns = [];
  if (includeNotesColumns)  addedEmptyColumns.push('Include', 'Exclude', 'Notes');
  const cset_keys = codeset_ids.map(
      id => selected_csets.find(
          cset => cset.codeset_id === id).concept_set_name);
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
  const excluded_keys = [
      'pathToRoot', 'hasChildren', 'childIds', 'descendants', 'domain_cnt',
      'levelsBelow', 'descendantCount', 'childCount',
  ];
  /* let keys = [ // as of 2024-03-07
    'concept_id', 'concept_name', 'domain_id', 'vocabulary_id', 'concept_class_id',
    'standard_concept', 'concept_code', 'invalid_reason', 'domain_cnt', 'domain',
    'total_cnt', 'distinct_person_cnt', 'isItem', 'status', 'levelsBelow',
    'descendantCount', 'childCount', 'drc', 'hasChildren', 'descendants', 'childIds',
    'depth', 'added', 'removed', 'not_a_concept', ]; */

  // specify the order of columns in csv
  let columns = [];
  if (separateLevels) {
    columns.push('Level');
    for (let i = 0; i <= maxLevel; i++) {
      columns.push('level' + i);
    }
  } else {
    columns.push('Concept name');
  }
  // columns.push(...first_keys);
  // get columns from what's actually in displayedRows[0]
  Object.keys(displayedRows[0]).forEach(k => {
    if (excluded_keys.includes(k) || k === 'concept_name') {
      return;
    }
    // if (!first_keys.includes(k) && k !== 'depth') {
    columns.push(key_convert[k]);
    // }
  });
  columns.push(...cset_keys);
  if (separateLevels) columns.push('Concept name');
  columns.push(...addedEmptyColumns);

  let rows = displayedRows.map(r => {
    let row = {};
    // adds indented concept names to rows
    if (separateLevels) {
      for (let i = 0; i <= maxLevel; i++) {
        row['level' + i] = (r.depth === i ? r.concept_name : '');
      }
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

  rows = uniqBy(rows, d => Object.values(d).join('|'));
  saveCsv(rows, columns, filename);
}

// createTheme creates a new theme named solarized that overrides the build in dark theme
// https://github.com/jbetancur/react-data-table-component/blob/master/src/DataTable/themes.ts
createTheme(
    'custom-theme',
    {
      text: {
        primary: '#268bd2',
        secondary: '#2aa198',
      },
      context: {
        background: '#cb4b16',
        text: '#FFFFFF',
      },
    },
    'light',
);

export function styles(sizes) {
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
        fontSize: '120%',
        overflow: 'visible',
        // verticalAlign: 'bottom !important', // doesn't work
        marginTop: 'auto',
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
        color: 'black',
        minHeight: '0px', // override the row height    -- doesn't work, can only seem to do it from css
        padding: sizes.rowPadding,
        fontSize: sizes.rowFontSize,
        // height: '2px',
        // fontSize: '2px',
        // height: '3px',
        borderBottom: '1px solid #BBB',
      },
    },
    cells: {
      style: {
        minHeight: '0px', // override the row height
        // paddingLeft: '8px', // override the cell padding for data cells
        // paddingRight: '8px',
        padding: 0, //'0px 5px 0px 5px',
        borderRight: '1px solid #BBB',
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

function SquishSlider({setSquish}) {
  // not refreshing... work on later
  function preventHorizontalKeyboardNavigation(event) {
    if (event.key === 'ArrowLeft' || event.key === 'ArrowRight') {
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
              width: '60%',
              marginLeft: '15%',
              marginTop: '15px',
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

export function howToSaveStagedChanges(params) {
  return (
      <>
        <ol>
          <LI>
            {params.atlasWidget}
            {/*<PRE>{atlasJson}</PRE>*/}
          </LI>
          <LI>
            Create a new concept set or new version of an existing concept in
            the{' '}
            <a
                href="https://unite.nih.gov/workspace/module/view/latest/ri.workshop.main.module.5a6c64c0-e82b-4cf8-ba5b-645cd77a1dbf"
                target="_blank" rel="noreferrer">
              enclave concept set editor
            </a>.
          </LI>
          <LI>
            When you get to the screen for editing the new draft version, you
            will
            see
            a blue button labelled "Add Concepts" on the upper right.
            Click the down arrow, then select "Import ATLAS Concept Set
            Expression
            JSON" from the menu.
          </LI>
          <LI>
            Paste the JSON copied into your clipboard from VS-Hub earlier into
            the
            box, and
            click "Import Atlas JSON".
          </LI>
          <LI>Click the version on the left again.</LI>
          <LI>On the right, click the green "Done" button.</LI>
        </ol>
        <p>
          Return to this work later by saving or bookmarking <a
            href={urlWithSessionStorage()}
            target="_blank" rel="noreferrer">this link</a> (
          <Button
              onClick={() => {
                navigator.clipboard.writeText(
                    urlWithSessionStorage());
              }}
          >
            Copy to clipboard
          </Button>.)
          <br/>
          Best practice is to paste this URL in your lab notebook and annotate
          your work there as well.
        </p>
      </>
  );
}
