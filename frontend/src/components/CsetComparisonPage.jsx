import React, {
  useCallback,
  useEffect,
  useRef,
  useState,
  Profiler,
} from 'react';
import DataTable, {createTheme} from 'react-data-table-component';
import AddCircle from '@mui/icons-material/AddCircle';
import Download from '@mui/icons-material/Download';
import RemoveCircleOutline from '@mui/icons-material/RemoveCircleOutline';
import Box from '@mui/material/Box';
import IconButton from '@mui/material/IconButton';
import Slider from '@mui/material/Slider';
import Switch from '@mui/material/Switch';
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

import {fmt, saveCsv, useWindowSize} from '../utils';
import {setColDefDimensions} from './dataTableUtils';
import {ConceptSetCard} from './ConceptSetCard';
import {Tooltip} from './Tooltip';
import {
  cellContents,
  cellStyle,
  getCodesetEditActionFunc,
  getItem,
  Legend,
  newCsetAtlasWidget,
  textCellForItem,
} from './NewCset';
import {FlexibleContainer} from './FlexibleContainer';
import {
  NEW_CSET_ID,
  urlWithSessionStorage, useCodesetIds,
  useGraphOptions, // useAppOptions,
  useNewCset, useCids, // useCompareOpt,
} from '../state/AppState';
import {GraphContainer} from '../state/GraphState';
import {getResearcherIdsFromCsets, useDataGetter} from '../state/DataGetter';
import {LI} from './AboutPage';
import {isEqual} from '@react-sigma/core';
// import {AddConcepts} from "./AddConcepts";

// TODO: Find concepts w/ good overlap and save a good URL for that
// TODO: show table w/ hierarchical indent
// TODO: Color table: I guess would need to see if could pass extra values/props and see if table widget can use that
//  ...for coloration, since we want certain rows grouped together
export async function fetchGraphData(props) {
  let {dataGetter, codeset_ids, cids, newCset = {}} = props;
  let promises = [ // these can run immediately
    dataGetter.fetchAndCacheItems(dataGetter.apiCalls.cset_members_items,
        codeset_ids),
    dataGetter.fetchAndCacheItems(dataGetter.apiCalls.csets, codeset_ids),
    dataGetter.fetchAndCacheItems(dataGetter.apiCalls.n3c_comparison_rpt),
  ];
  // have to get concept_ids before fetching concepts
  // const concept_ids_by_codeset_id = await dataGetter.fetchAndCacheItems(dataGetter.apiCalls.concept_ids_by_codeset_id, codeset_ids);
  // let concept_ids = union(flatten(Object.values(concept_ids_by_codeset_id)));

  const graphData = await dataGetter.fetchAndCacheItems(
      dataGetter.apiCalls.concept_graph_new,
      {codeset_ids: codeset_ids || [], cids: cids || []});
  let {concept_ids} = graphData;

  if (!isEmpty(newCset)) {
    concept_ids = union(concept_ids,
        Object.values(newCset.definitions).map(d => d.concept_id));
  }
  promises.push(
      dataGetter.fetchAndCacheItems(dataGetter.apiCalls.concepts, concept_ids));

  let [csmi, selected_csets, comparedPairs, conceptLookup] = await Promise.all(promises);
  let cpairs = comparedPairs.map(p => [p.cset_1_codeset_id, p.cset_2_codeset_id].sort().join('-'));

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
  }
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
    selected_csets = selected_csets.map(cset => {
      cset = {...cset};
      // not sure why these counts are needed...oh, maybe because we
      //  planned to update them and add them to the comparison UI somehow
      cset.intersecting_concepts = 0;
      cset.precision = 0;
      cset.recall = 0;
      cset.counts = {};
      return cset;
    });

    csmi = {...csmi, ...newCset.definitions};
  }

  const definitionConcepts = uniq(flatten(
      Object.values(csmi).map(d => Object.values(d)),
  ).filter(d => d.item).map(d => d.concept_id));

  const expansionConcepts = uniq(flatten(
      Object.values(csmi).map(d => Object.values(d)),
      // concepts that are in expansion but not definition
  ).filter(d => d.csm && !d.item).map(d => d.concept_id + ''));

  let specialConcepts = {
    definitionConcepts: definitionConcepts.map(String),
    expansionConcepts: expansionConcepts.map(String),
    nonStandard: uniq(Object.values(conceptLookup).
        filter(c => !c.standard_concept).
        map(c => c.concept_id)),
    zeroRecord: uniq(Object.values(conceptLookup).
        filter(c => !c.total_cnt).
        map(c => c.concept_id)),
    addedCids: cids.map(String),
  };

  if (comparison_rpt) {
    comparison_rpt = await comparison_rpt;
    specialConcepts.added = comparison_rpt.added.map(d => d.concept_id + '');
    specialConcepts.removed = comparison_rpt.removed.map(d => d.concept_id + '');
  }

  for (let cid in conceptLookup) {    // why putting all the specialConcepts membership as properties on the concept?
    let c = {...conceptLookup[cid]}; // don't want to mutate the cached concepts
    if (specialConcepts.definitionConcepts.includes(cid + '')) c.isItem = true;
    if (specialConcepts.expansionConcepts.includes(cid + '')) c.isMember = true;
    if ((specialConcepts.added || []).includes(cid + '')) c.added = true;
    if ((specialConcepts.removed || []).includes(cid + '')) c.removed = true;
    c.status = [
      c.isItem && 'In definition', c.isMember && 'In Expansion',
      c.added && 'Added', c.removed && 'Removed'].filter(d => d).join(', ');
    conceptLookup[cid] = c;
  }

  const concepts = Object.values(conceptLookup);
  return {
    ...graphData,
    concept_ids,
    selected_csets,
    conceptLookup,
    csmi,
    concepts,
    specialConcepts,
    comparison_rpt,
  };
}

export function CsetComparisonPage() {
  const [codeset_ids] = useCodesetIds();
  const [cids, cidsDispatch] = useCids();
  // const [compareOpt, compareOptDispatch] = useCompareOpt();
  const [newCset, newCsetDispatch] = useNewCset();
  const [api_call_group_id, setApiCallGroupId] = useState();
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
    currentUserId,
    specialConcepts,
    comparison_rpt,
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

      let whoami = dataGetter.fetchAndCacheItems(dataGetter.apiCalls.whoami,
          undefined);

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
        comparison_rpt,
      } = graphData;

      // let _gc = new GraphContainer({ ...graphData, concepts, specialConcepts, csmi });
      //  that looks redundant, unneeded. fixing now but not testing. hopefully won't break anything:
      let _gc = new GraphContainer(graphData);


      let newGraphOptions = _gc.setGraphDisplayConfig(graphOptions);
      if (!isEqual(graphOptions, newGraphOptions)) {
        debugger;
      }
      graphOptions = newGraphOptions;
      let displayedRows = _gc.getDisplayedRows(graphOptions);


      newGraphOptions = _gc.setGraphDisplayConfig(graphOptions);
      if (!isEqual(graphOptions, newGraphOptions)) {
        debugger;
        // save the options to state. todo: why is this necessary?
        graphOptionsDispatch({type: 'REPLACE', graphOptions: newGraphOptions});
      }

      const currentUserId = (await whoami).id;
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
        currentUserId,
        specialConcepts,
        comparison_rpt,
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

  if (!gc || isEmpty(graphOptions) || isEmpty(displayedRows) ||
      isEmpty(selected_csets)) {
    // sometimes selected_csets and some other data disappears when the page is reloaded
    return <p>Downloading...</p>;
  }

  const nested = get(graphOptions, 'nested', true);   // defaults to true but allows false to be set

  const editAction = getCodesetEditActionFunc(
      {csmi, newCset, newCsetDispatch});

  const colDefs = getColDefs({
    gc,
    selected_csets,
    concepts,
    cids,
    sizes,
    editAction,
    windowSize,
    // hidden,
    displayedRows,
    graphOptions,
    graphOptionsDispatch,
    csmi,
    newCset, newCsetDispatch,
    setShowCsetCodesetId,
    comparison_rpt,
  });

  let csetCard = null;
  if (showCsetCodesetId) {
    const cset = selected_csets.find(d => d.codeset_id == showCsetCodesetId);
    csetCard = (
        <FlexibleContainer key="csetCard" openOnly={true}
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

  const graphDisplayOptionsWidth = 525;
  const graphDisplayOptionsHeight = Object.keys(gc.graphDisplayConfig).length *
      31 + 40;
  let infoPanels = [
    <FlexibleContainer key="stats-options" title="Stats and options"
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
    <Button key="nested"
            disabled={nested}
            onClick={() => graphOptionsDispatch({type:'nested', nested: true})}
            sx={{ marginRight: '4px' }}
    >
      {displayedRows.length} in hierarchy
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

    /* <FlexibleContainer key="cset-table" title="Table of concept set being edited"
                       position={panelPosition} countRef={countRef}>
      <CsetsDataTable show_selected={true}
                      min_col={false}
                      clickable={false}
                      showTitle={false}
                      selected_csets={selected_csets} />
    </FlexibleContainer>, */
  ];

  let edited_cset;
  if (editingCset) {
    infoPanels.push(
        <FlexibleContainer key="cset" title="New concept set"
                           startHidden={false}
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
    /* infoPanels.push(
        <FlexibleContainer key="compare" title={edited_cset.concept_set_name}>
          <CsetsDataTable {...props} show_selected={true} min_col={false} />
        </FlexibleContainer>
    ); */

    const atlasWidget = newCsetAtlasWidget(newCset, conceptLookup);

    infoPanels.push(
        <FlexibleContainer key="instructions"
                           title="Instructions to save new concept set"
                           style={{maxWidth: 700}}
                           position={panelPosition} countRef={countRef}>
          {howToSaveStagedChanges({newCset, atlasWidget})}
        </FlexibleContainer>,
    );
  }

  infoPanels.push(
      <FlexibleContainer key="legend" title="Legend" position={panelPosition}
                         countRef={countRef}>
        <Legend editing={editingCset}/>
      </FlexibleContainer>,
  );

  const tableProps = {
    rowData: displayedRows,
    columns: colDefs,
    selected_csets,
    customStyles,
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
      name: 'name',
      selector: (row) => row.name,
      style: {paddingLeft: 4},
    },
    {
      name: 'value',
      selector: (row) => row.value,
      format: (row) => fmt(row.value),
      width: 80,
      style: {justifyContent: 'right', paddingRight: 4},
    },
    {
      name: 'hidden-rows',
      selector: (row) => row.value,
      format: (row) => {
        // for explanation see displayOptions logic in
        //    GraphState:setGraphDisplayConfig
        let text;
        let tttext = '';
        if (row.specialTreatmentRule === 'show though collapsed') {
          if (graphOptions.specialConceptTreatment[row.type] === false) {
            if (row.hiddenConceptCnt > 0) {
              text = fmt(row.hiddenConceptCnt) + ' not shown';
              tttext = 'Click SHOW to make them visible.';
            }
          } else {
            if (row.displayedConceptCnt > 0) {
              text = fmt(row.displayedConceptCnt) + ' shown';
              tttext = `Currently showing records even if parents aren't expanded. Click UNSHOW to disable.`;
            }
          }
        } else if (row.specialTreatmentRule === 'hide though expanded') {
          if (graphOptions.specialConceptTreatment[row.type] === false) {
            if (row.displayedConceptCnt > 0) {
              // how many rows will be hidden if HIDE is clicked
              text = fmt(row.displayedConceptCnt) + ' visible';
            }
          } else {
            if (row.hiddenConceptCnt) {
              // how many rows will be unhidden if UNHIDE is clicked
              text = fmt(row.hiddenConceptCnt) + ' hidden';
            }
          }
        } else if (['Concepts', 'Expansion concepts'].includes(row.name)) {
          text = fmt(row.displayedConceptCnt) + ' visible';
        } else {
          text = '';
        }
        // isNaN(row.hiddenConceptCnt) ? '' : fmt(row.hiddenConceptCnt || '') + ' hidden'
        if (tttext) {
          return (
              <Tooltip label={tttext}>
                <span>{text}</span>
              </Tooltip>);
        }
        return text;
      },
      // sortable: false,
      // right: true,
      width: 120,
      style: {justifyContent: 'right', paddingRight: 4},
    },
    {
      name: 'specialTreatment',
      selector: (row) => row.specialTreatment,
      format: (row) => {
        if (typeof row.specialTreatmentDefault === 'undefined') {
          return '';
        }
        let onClick;
        onClick = () => {
          graphOptionsDispatch(
              {gc, type: 'TOGGLE_OPTION', specialConceptType: row.type});
        };
        let text = '';
        let tttext = '';
        if (row.specialTreatmentRule === 'expandAll') {
          onClick = () => {
            graphOptionsDispatch({gc, type: 'TOGGLE_EXPAND_ALL'});
          };
          text = get(graphOptions, 'expandAll') ? 'Collapse all' : 'Expand all';
          tttext = 'Does not affect rows hidden or shown by other options';
        } else if (row.specialTreatmentRule === 'show though collapsed') {
          if (row.specialTreatment) {
            text = 'unshow';
            tttext = 'Currently showing records even if parents aren\'t expanded. Click to disable.';
          } else {
            if (row.hiddenConceptCnt) {
              text = 'show';
              tttext = 'Show even if parents aren\'t expanded';
            }
          }
        } else if (row.specialTreatmentRule === 'hide though expanded') {
          if (row.specialTreatment) {
            text = 'unhide';
          } else {
            text = 'hide';
          }
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

function precisionRecall(props) {
  // TODO: write someday -- precision recall of newCset against all? Or each against all? Not sure what the plan was
}

function nodeToTree(node) { // Not using
  // a flat tree
  const subTrees = node.childIds().map(n => nodeToTree(n));
  return [node, ...subTrees];
}

function getCollapseIconAndName(
    row, sizes, graphOptions, graphOptionsDispatch, gc) {
  let Component;
  let direction;
  if (
      // graphOptions.specificNodesExpanded.includes(parseInt(row.concept_id)) ||
      // (graphOptions.expandAll && !graphOptions.specificNodesCollapsed.includes(parseInt(row.concept_id)))
      // parseInt means it doesn't work with the 'unlinked' node
      graphOptions.specificNodesExpanded.find(d => d == row.concept_id) ||
      (graphOptions.expandAll &&
          !graphOptions.specificNodesCollapsed.find(d => d == row.concept_id))
  ) {
    Component = RemoveCircleOutline;
    direction = 'collapse';
  } else {
    Component = AddCircle;
    direction = 'expand';
  }
  return (
      <span
          className="toggle-collapse concept-name-row"
          onClick={
            (evt) => {
              graphOptionsDispatch({
                gc,
                type: 'TOGGLE_NODE_EXPANDED',
                nodeId: row.concept_id,
                direction,
              });
            }
          }
          // TODO: capture long click or double click or something to expand descendants
          // onDoubleClick={() => graphOptionsDispatch({type: "TOGGLE_NODE_EXPANDED", payload: {expandDescendants: true, nodeId: row.concept_id}})}
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
        <span className="concept-name-text">{row.concept_name}</span>
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
    editAction,
    windowSize,
    hidden,
    displayedRows,
    graphOptions,
    graphOptionsDispatch,
    csmi,
    newCset, newCsetDispatch,
    setShowCsetCodesetId,
    comparison_rpt,
  } = props;
  const {nested, hideRxNormExtension, hideZeroCounts} = graphOptions;
  const {definitions = {}} = newCset;

  const maxNameLength = max(displayedRows.map(d => d.concept_name.length));
  let coldefs = [
    {
      name: 'Concept name',
      selector: (row) => row.concept_name,
      format: (row) => {
        let name = row.concept_name;
        if (row.pathFromDisplayedNode && row.pathFromDisplayedNode.length) {
          let names = row.pathFromDisplayedNode.map(
              cid => gc.nodes[cid].concept_name);
          name = <span>
                            {names.map((name, index) => (
                                <span key={index}>
                                        <span
                                            style={{opacity: .5}}>{name}</span>
                                        <span> → </span>
                                    </span>
                            ))}
            {row.concept_name}
                           </span>;
        }
        let content = nested ? (
            row.hasChildren
                ? getCollapseIconAndName(row, sizes, graphOptions,
                    graphOptionsDispatch, gc)
                : (
                    <span className="concept-name-row">
                                {/*<RemoveCircleOutline
                                    // this is just here so it indents the same distance as the collapse icons
                                    sx={{fontSize: sizes.collapseIcon, visibility: "hidden"}} /> */}
                      <span className="concept-name-text">{name}</span>
                            </span>)
        ) : (
            // this is for non-nested which is not currently implemented (no button for it)
            //      it allowed sorting rows... TODO: figure out if bringing it back
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
      name: '#',
      selector: (row) => row.nodeOccurrence,
      width: 30,
      style: {justifyContent: 'center'},
    },
    {
      name: 'Status', // only shown for comparisons I think
      headerProps: {
        tooltipContent: 'Information about this row',
        /*
        tooltipContent: 'Whether concept is a definition item' +
            (comparison_rpt ? ' or added or removed in the comparison report' : '') +
            ". These concepts are displayed even if you haven't expanded their parents" +
            " and are highlighted with a row color.",
         */
        // doesn't work:
        // ttStyle: {zIndex: 1000, opacity: .1, overflow: 'visible', width: '300px', backgroundColor: 'pink'},
      },
      selector: (row) => row.status,
      sortable: false,
      width: 88,
      style: {paddingRight: 4, paddingLeft: 4},
      wrap: true,
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
      // name: "Vocabulary",
      headerProps: {
        headerContent: (
            concepts.some(d => d.vocabulary_id === 'RxNorm Extension')
                ? <div style={{display: 'flex', flexDirection: 'column'}}>
                  <div>Vocabulary</div>
                  <div
                      style={{fontSize: 'x-small'}}>({hidden.rxNormExtension} {hideRxNormExtension
                      ? 'hidden'
                      : ''} RxNorm
                    Extension rows)
                  </div>
                  <Tooltip label="Toggle hiding of RxNorm Extension concepts">
                    <Switch sx={{margin: '-8px 0px'}} checked={!hideRxNormExtension}
                            onClick={() => graphOptionsDispatch({          // not currently being used
                              type: 'hideRxNormExtension',
                              hideRxNormExtension: !hideRxNormExtension,
                            })}
                    />
                  </Tooltip>
                </div>
                : 'Vocabulary'
        ),
        // headerContentProps: { onClick: editCodesetFunc, codeset_id: cset_col.codeset_id, },
      },
      selector: (row) => row.vocabulary_id,
      // format: (row) => <Tooltip label={row.vocabulary_id} content={row.vocabulary_id} />,
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
  if (!comparison_rpt) {
    coldefs = coldefs.filter(d => d.name !== 'Status');
  }
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
        const item = getItem({
          codeset_id: cset_col.codeset_id,
          concept_id: row.concept_id, csmi, newCset,
        }) || {};
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
    /* squishTo = 1, cset_data, displayedRows, selected_csets */
  } = props;
  const {definitions = {}, members = {}} = newCset;
  const infoPanelRef = useRef();
  // console.log(derivedState);

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
        backgroundColor: row.removed && '#F662' ||
            row.added && '#00FF0016' ||
            row.isItem && '#33F2' || '#FFF',
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
  const {displayedRows, codeset_ids, selected_csets, csmi} = props;
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
  const first_keys = ['Patients', 'Records', 'Vocabulary', 'Concept code'];
  const addedEmptyColumns = ['Include', 'Exclude', 'Notes'];
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
  const excluded_keys = ['pathToRoot', 'hasChildren'];
  // let keys = uniq(flatten(displayedRows.map(d => Object.keys(d))));
  // console.log(keys)
  let keys = [ // as of 2024-03-07
    'concept_id',
    'concept_name',
    'domain_id',
    'vocabulary_id',
    'concept_class_id',
    'standard_concept',
    'concept_code',
    'invalid_reason',
    'domain_cnt',
    'domain',
    'total_cnt',
    'distinct_person_cnt',
    'isItem',
    'status',
    'levelsBelow',
    'descendantCount',
    'childCount',
    'drc',
    'hasChildren',
    'descendants',
    'childIds',
    'depth',
    'added',
    'removed',
    'not_a_concept',
  ];

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
    if (!first_keys.includes(k) && k !== 'depth') {
      columns.push(key_convert[k]);
    }
  });
  columns.push(...cset_keys, 'Concept name', ...addedEmptyColumns);

  const rows = displayedRows.map(r => {
    let row = {};
    // adds indented concept names to rows
    for (let i = 0; i <= maxLevel; i++) {
      row['level' + i] = (r.depth === i ? r.concept_name : '');
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
            href={urlWithSessionStorage({newCset: params.newCset})}
            target="_blank" rel="noreferrer">this link</a> (
          <Button
              onClick={() => {
                navigator.clipboard.writeText(
                    urlWithSessionStorage({newCset: params.newCset}));
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
