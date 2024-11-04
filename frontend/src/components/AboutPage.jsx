/*
 * todo's
 *  todo: 1. Siggie was going to add some sort of Table here
 * */
import React, {useCallback, useEffect, useState, useRef} from 'react';
import {Autocomplete, TextField} from '@mui/material';
import {useNavigate} from 'react-router-dom';
import Typography from '@mui/material/Typography';
import Button from '@mui/material/Button';
import {Link, useLocation} from 'react-router-dom';
import {VERSION} from '../env';
import {useDataCache} from '../state/DataCache';
import {useDataGetter} from '../state/DataGetter';
import {
  useSearchParamsState,
  useSessionStorage,
} from '../state/StorageProvider';
import {useCodesetIds, resetReducers} from '../state/AppState';
import {isEmpty} from 'lodash';

export function ViewBundleReportSelector({bundles}) {
  const navigate = useNavigate();

  if (isEmpty(bundles)) {
    return null;
  }

  const handleOptionSelect = (event, selectedOption) => {
    if (selectedOption) {
      navigate(`/BundleReport?bundle=${selectedOption.value}`);
    }
  };

  return (
      <Autocomplete
          style={{width: 400}}
          options={bundles.map(b => ({label: b, value: b}))}
          renderInput={(params) => <TextField {...params}
                                              label="View a bundle report"/>}
          onChange={handleOptionSelect}
      />
  );
};

export function AboutPage() {
  // const {codeset_ids=[], all_csets=[], cset_data={}} = props;
  // const {data_counts=[], } = cset_data;
  //
  // const rowData = data_counts.map(
  //     line => {
  //       line = line.map(d => cfmt(d));
  //       const [Message, ConceptSetNames, CodesetIds, Concepts] = line;
  //       return {Message, ConceptSetNames, CodesetIds, Concepts};
  //     }
  // )
  const dataCache = useDataCache();
  const dataGetter = useDataGetter();
  const ss = useSessionStorage();
  const sp = useSearchParamsState();
  const loadCSetsRef = useRef(null);
  const [refreshButtonClicked, setRefreshButtonClicked] = useState();
  const [lastRefreshed, setLastRefreshed] = useState();
  const location = useLocation();
  const {search} = location;  // querystring for passing along to page links
  const [bundles, setBundles] = useState(null);

  useEffect(() => {
    (async () => {
      if (bundles) {
        return;
      }
      try {
        const _bundles = await dataGetter.axiosCall('get-bundle-names',
            {sendAlert: false});
        setBundles(_bundles);
      } catch (error) {
        console.error('Error fetching data:', error);
      }
    })();
  });

  const handleRefresh = async () => {
    try {
      console.log(
          'Triggering database refresh and clearing cache so new data will be fetched when ready');
      // empty cache immediately, and then again after the db-refresh call is done
      dataCache.clear();
      await dataGetter.axiosCall('db-refresh');
      dataCache.clear();
    } catch (error) {
      console.error('Error:', error);
    }
  };

  // const linkPath = `/OMOPConceptSets?${localCodesetIds.map(d => `codeset_ids=${d}`).join("&")}`;

  useEffect(() => {
    (async () => {
      try {
        let lastRefreshed = dataCache.lastRefreshed();
        if (!lastRefreshed) {
          await dataCache.cacheCheck(dataGetter);
          lastRefreshed = dataCache.lastRefreshed();
        }
        setLastRefreshed(lastRefreshed);
      } catch (e) {
        console.warn(
            'was getting a max update depth exceeded here. fix it if it comes up again');
      }
    })();
  }, []);

  console.log(loadCSetsRef);
  return (
      <div style={{margin: '15px 30px 15px 40px'}}>
        <TextH1>About VS-Hub</TextH1>
        <TextBody>
          VS-Hub is a tool for comparing, analyzing, updating, and (soon)
          creating concept sets. At the current time it only handles concept
          sets in the <a href="https://covid.cd2h.org/enclave">N3C Enclave</a>,
          but is charted to expand beyond N3C (to work with FHIR, VSAC,
          OHDSI/ATLAS, and other sources of code sets and targets for new code
          set development) in the near future.
        </TextBody>
        <TextBody>
          This <a href="https://youtu.be/EAwBZUiNUUk?t=2130">demo video</a> from
          the October 31, 2022 N3C Forum provides a brief introduction. (VS-Hub
          has evolved since the video was made. Use the <a
            href="https://github.com/jhu-bids/termhub/issues/new/choose"
            target="_blank" rel="noopener noreferrer">create issue</a> button
            below to clamor for a new video and we will push that up on our
            priority list.)
        </TextBody>

        <TextH1>Bug reports & feature requests</TextH1>
        <TextBody>
          If you encounter a bug or a poor user experience issue, or have a
          feature request in mind, we would love to hear from you.
        </TextBody>
        <TextBody>
          {/*<p><Button variant={"outlined"}>*/}
          <Button variant={'contained'}
                  href="https://github.com/jhu-bids/TermHub/issues/new/choose"
                  target="_blank" rel="noreferrer"
          >
            Create an issue
          </Button>
        </TextBody>

        <TextH1>Database Refresh</TextH1>
        <TextBody>Will refresh the database with the latest data from the N3C
          Enclave.</TextBody>
        <TextBody><b>IMPORTANT:</b> There is a delay in the Enclave where when a
          concept set draft is finalized, its concept set members must be
          expanded. This can take between 20-45 minutes to complete. At that
          time, the members will be visible in the UI and also the API for
          fetching by VS-Hub. VS-Hub will detect if this issue occurs and
          will continue to check until the members are available and import
          them as soon as they are.
        </TextBody>
        <TextBody>Last refresh: {lastRefreshed
            ? lastRefreshed.toLocaleString()
            : 'fetching it...'}</TextBody>
        <TextBody>
          <Button
              variant={'contained'}
              onClick={() => {
                setRefreshButtonClicked(Date());
                handleRefresh();
              }}>
            Refresh database
          </Button>
        </TextBody>

        <TextH1>View / download N3C recommended concept sets</TextH1>
        <TextBody>
          <Button to="/BundleReport?bundle=N3C Recommended"
              // to="/N3CRecommended"
                  variant={'contained'}
                  component={Link}
                  style={{margin: '7px', textTransform: 'none'}}
          >
            N3C Recommended
          </Button>
          <Button to="/N3CComparisonRpt"
                  variant={'contained'}
                  component={Link}
                  style={{margin: '7px', textTransform: 'none'}}
          >
            N3C Recommended comparison after vocab changes
          </Button>
        </TextBody>

        <ViewBundleReportSelector bundles={bundles}/>

        <TextH1>How to's</TextH1>
        <TextH2>How to: Fix the app if it's acting weird</TextH2>
        <ol>
          <LI>Try: Refreshing the page</LI>
          <LI>
            Try purging application state (by clicking here, or if you can't get
            to this page, open chrome(or
            other browser console, and
            enter <code>localStorage.clear()</code> and <code>sessionStorage.clear()</code>): <Button
              variant={'contained'}
              // onClick={() => queryClient.removeQueries()}
              onClick={() => {
                dataCache.clear();
                if (loadCSetsRef.current) loadCSetsRef.current.value = '';
                resetReducers();
                // maybe resetReducers makes these redundant?
                // ss.clear();
                // sp.clear();
              }}
          >
            Clear application state
          </Button>
          </LI>
          <LI>File a report: via <a
              href="https://github.com/jhu-bids/termhub/issues/new/choose"
              target="_blank"
              rel="noopener noreferrer">GitHub issue</a> or <a
              href="mailto:termhub-support@jhu.edu">termhub-support@jhu.edu</a></LI>
        </ol>
        <TextH2>How to: Load a set of concept sets</TextH2>
        <LoadCodesetIds loadCsetsRef={loadCSetsRef}/>

        <TextH1>Debug / explore application data</TextH1>
        <TextBody>
          <Button
              to={`/view-state${search ? search : ''}`}
              variant={'contained'}
              component={Link}
              style={{margin: '7px', textTransform: 'none'}}
          >
            View state
          </Button>

          <Button
              to={`/usage${search ? search : ''}`}
              variant={'contained'}
              component={Link}
              style={{margin: '7px', textTransform: 'none'}}
          >
            Usage report
          </Button>
        </TextBody>

      </div>
  );
}

function LoadCodesetIds(props) {
  let {containingPage, loadCsetsRef} = props;
  const didntGetRef = useRef(null);
  loadCsetsRef = loadCsetsRef || didntGetRef;
  let [codeset_ids, codesetIdsDispatch] = useCodesetIds();
  const [localCodesetIds, setLocalCodesetIds] = useState(codeset_ids);
  const testCodesetIds = [400614256, 419757429, 484619125]; // 411456218 : asthma wide
  if (isEmpty(codeset_ids)) {
    codeset_ids = localCodesetIds;
  }

  const handleCodesetIdsTextChange = useCallback((evt) => {
    const val = evt.target.value;
    const cset_ids = val.split(/[,\s]+/).filter(d => d.length);
    setLocalCodesetIds(cset_ids);
  }, []);

  return (
      <div style={{margin: '15px 30px 15px 40px'}}>
        <TextBody>
          You can add concept sets one at a time
          {containingPage === 'OMOPConceptSets'
              ? ' in the select box above '
              : ' on the Cset Search page '}
          or paste several in here.
          <Button style={{display: 'inline-block'}} variant="text"
                  onClick={(evt) => {
                    setLocalCodesetIds(testCodesetIds);
                    if (loadCsetsRef.current) {
                      loadCsetsRef.current.value = testCodesetIds.join(' ') +
                          ' ';
                    }
                  }}
          >
            Use asthma example concept sets.
          </Button>
        </TextBody>
        <TextField fullWidth multiline
                   label={codeset_ids.length
                       ? ''
                       : 'Enter codeset_ids separated by spaces, commas, or newlines and click button below'}
                   onChange={handleCodesetIdsTextChange}
                   defaultValue={codeset_ids.join(', ')}
                   inputRef={loadCsetsRef}
        >
        </TextField>
        {
          codeset_ids.length
              ? <Button
                  style={{margin: '7px', textTransform: 'none'}}
                  variant={'contained'}
                  onClick={(evt) => {
                    codesetIdsDispatch({
                      type: 'set_all',
                      codeset_ids: localCodesetIds,
                    });
                  }}
              >
                Load code sets {localCodesetIds.join(', ')}
              </Button>
              : null
        }
      </div>
  );
}

/*
function HelpWidget(props) {
  const {doc} = props;
  if (doc === 'legend') {
    return <Legend />;
  }

}
const WINDOW_OPEN_OPTIONS = {
  spec: {
    width: 100, /* window width * /
    height: 900, /* window height * /
  },
  // transform: 'scale(0.8)',
  top: 20,
  left: window.innerWidth - 250,
};
function HelpButton(props) {
  const {doc, windowOptions} = props;
  // const options = windowOptions ?? WINDOW_OPEN_OPTIONS;
  const options = WINDOW_OPEN_OPTIONS;
  const url = `/help?doc=${doc}`;
  const [handleWindowOpen, newWindowHandle] = useOpenInWindow(url, options);
  console.log({newWindowHandle});
  if (doc === 'legend') {
    return <Button onClick={handleWindowOpen}>Show legend</Button>;
  }
}
*/

/*
function LegendButton(props) {
return (
    <po.Popover>
      <po.PopoverTrigger sx={{float:'right'}}>Display legend</po.PopoverTrigger>
      <po.PopoverContent className="Popover legend" >
        <po.PopoverHeading>Legend</po.PopoverHeading>
        <Legend/>
        <po.PopoverClose>Close</po.PopoverClose>
      </po.PopoverContent>
    </po.Popover>)
}
function TestPop(startOpen=false) {
  const [open, setOpen] = useState(startOpen);
  return (
      <div className="App">
        <h1>Floating UI — Popover</h1>
        <po.Popover open={open} onOpenChange={setOpen}>
          <po.PopoverTrigger onClick={() => setOpen((v) => !v)}>
            My trigger
          </po.PopoverTrigger>
          <po.PopoverContent className="Popover">
            <po.PopoverHeading>My popover heading</po.PopoverHeading>
            <po.PopoverDescription>My popover description</po.PopoverDescription>
            <po.PopoverClose>Close</po.PopoverClose>
          </po.PopoverContent>
        </po.Popover>
      </div>
  );
}
*/
export const TextBody = (props) => (
    <Typography variant="body2" color="text.primary" gutterBottom>
      {props.children}
    </Typography>
);
export const TextBold = (props) => (
    <Typography
        sx={{fontWeight: 'bold'}}
        variant="body2"
        color="text.primary"
        gutterBottom
    >
      {props.children}
    </Typography>
);
export const TextH1 = (props) => (
    <Typography
        variant="h5"
        color="text.primary"
        style={{marginTop: '30px'}}
        gutterBottom
    >
      {props.children}
    </Typography>
);
export const TextH2 = (props) => (
    <Typography
        variant="h6"
        color="text.primary"
        style={{marginTop: '5px'}}
        gutterBottom
    >
      {props.children}
    </Typography>
);
export const LI = (props) => (
    <li>
      <Typography
          variant="body2"
          color="text.primary"
          style={{marginTop: '5px'}}
          gutterBottom
      >
        {props.children}
      </Typography>
    </li>
);
export const PRE = (props) => (
    <Typography
        variant="pre"
        color="text.primary"
        style={{
          marginTop: '5px',
          display: 'block',
          unicodeBidi: 'embed',
          fontFamily: 'monospace',
          whiteSpace: 'pre',
        }}
        gutterBottom
    >
      {props.children}
    </Typography>
);

export let DOCS = {};
DOCS.blank_search_intro = (
    <>
      <h1>Welcome to VS-Hub! Beta version {VERSION}</h1>
      <p style={{paddingLeft: '12px', paddingRight: '130px'}}>
        VS-Hub is a tool for comparing, analyzing, updating, and creating concept
        sets. At the current time it only handles concept sets in the N3C Enclave,
        but is charted to expand beyond N3C in the near future.
      </p>
      <h2>Within VS-Hub you can:</h2>

      <div style={{paddingLeft: '12px', paddingRight: '130px'}}>
        <p>
          <strong>CSET SEARCH</strong>
        </p>
        <ul>
          <LI>
            Perform searches for existing concept sets currently in the N3C
            Enclave.
          </LI>
        </ul>

        <p>
          <strong>CSET COMPARISON</strong>
        </p>
        <ul>
          <LI>Compare selected concept sets.</LI>
          <LI>
            Add and remove concepts by reviewing and selecting concept mappings,
            descendants, exclusions.
          </LI>
          <LI>
            Export JSON of modified concept set. (Required in order to put
            changes
            in Enclave, for now.)
          </LI>
        </ul>

        <p>
          <strong>LOAD A LIST OF CONCEPT SETS (codeset_ids)</strong>
        </p>
        <LoadCodesetIds containingPage="OMOPConceptSet"/>

        {/*
    <p><strong>UPLOAD CSV</strong>
      <ul>
        <LI>
          With a single CSV, you can create (i) a new version to an existing concept set, e.g. to
          add/delete concepts or change metadata, and (ii) coming soon: upload a completely new concept set ("concept set
          container").
        </LI>
      </ul>
    </p>
    */}

        <p>
          <strong>HELP/ABOUT</strong>
        </p>
        <ul>
          <LI>
            Learn more about VS-Hub and review the step by step <Link
              to="/about">“How To” section</Link>.
          </LI>
          <LI>Provide feedback by creating a <a
              href="https://github.com/jhu-bids/termhub/issues/new/choose"
              target="_blank" rel="noopener noreferrer">GitHub issue.</a></LI>
          <LI>
            Let us know of any bug or a poor user experience, or share a feature
            request.
          </LI>
        </ul>
      </div>
      <div style={{position: 'absolute', top: window.innerHeight - 40 + 'px'}}>
        &#169; Johns Hopkins University 2023. Available open source on{' '}
        <a href="https://github.com/jhu-bids/TermHub">GitHub</a> under a{' '}
        <a href="https://github.com/jhu-bids/TermHub/blob/develop/LICENSE">
          GPL 3 License
        </a>
        .
      </div>
    </>
);

