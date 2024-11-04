import {createContext, useContext} from 'react';
import {createSearchParams} from 'react-router-dom';
import axios from 'axios';
import {flatten, isEmpty, setWith, once, uniq, difference} from 'lodash';

// import {useAlertsDispatch} from "./AppState";
import {API_ROOT} from '../env';
import {useDataCache, monitorCachePerformance} from './DataCache';
import {compress} from 'lz-string';

export const backend_url = (path) => `${API_ROOT}/${path}`;

const DataGetterContext = createContext(null);

export function DataGetterProvider({children}) {
  // const alertsDispatch = useAlertsDispatch();
  const dataCache = useDataCache();
  const dataGetter = new DataGetter(dataCache /*alertsDispatch*/);
  monitorCachePerformance(dataGetter);

  return (
      <DataGetterContext.Provider value={dataGetter}>
        {children}
      </DataGetterContext.Provider>
  );
}

export function useDataGetter() {
  return useContext(DataGetterContext);
}

export class DataGetter {
  constructor(dataCache) {
    this.dataCache = dataCache;
  }

  async getApiCallGroupId() {
    const getid = once(() => {
      return this.axiosCall('next-api-call-group-id', {sendAlert: false});
    });
    this.api_call_group_id = await getid();
    console.log('api_call_group_id', this.api_call_group_id);
    return this.api_call_group_id;
  }

  async axiosCall(path, {
    backend = true,
    data,
    returnDataOnly = true,
    useGetForSmallData = true,
    verbose = false,
    sendAlert = false,
    title,
    makeQueryString,
    dataLengthFunc,
    skipApiGroup,
  } = {}) {
    let url = backend ? backend_url(path) : path;
    let request = {url};
    let alertAction = {
      request,
      type: 'create',
      eventType: 'axiosCall',
      title: title || path,
    };
    alertAction.id = alertAction.title + ':' + (new Date()).toISOString();
    let qsData = {};
    let qs = path.match(/\?/) ? '' : '?';
    if (path !== 'next-api-call-group-id' && this.api_call_group_id &&
        !skipApiGroup) {
      qs = qs + 'api_call_group_id=' + this.api_call_group_id + '&';
    }
    try {
      if (typeof (data) === 'undefined') {
        request.method = 'get';
      } else {
        let dataLength = 0;
        if (dataLengthFunc) {
          dataLength = dataLengthFunc(data);
        } else if (Array.isArray(data) || typeof (data) === 'string') {
          dataLength = data.length;
        } else {
          throw new Error('dataLengthFunc or data.length is required');
        }

        if (useGetForSmallData && dataLength <= 1000) {
          request.method = 'get';
          qs += makeQueryString(data).toString();
        } else {
          request.method = 'post';
          request.data = data;
        }
      }
      request.url = url + qs;
      verbose && console.log('axios request', request);

      // alertAction.id = compress(JSON.stringify(request));

      let response = axios(request);

      if (sendAlert) {
        alertAction.axiosCall = response;
        // this.alertsDispatch(alertAction);
        response = await response;
        alertAction = {...alertAction, response, type: 'resolve'};
        delete alertAction.axiosCall;
        // this.alertsDispatch(alertAction);
      }
      response = await response;
      return returnDataOnly ? response.data : response;
    } catch (error) {
      if (sendAlert) {
        alertAction = {...alertAction, error, type: 'error'};
        // this.alertsDispatch(alertAction);
      } else {
        throw new Error(error);
      }
    }
  }

  prefetch(props) {
    const {itemType, codeset_ids, keyName} = props;
    switch (itemType) {
      case 'all_csets':
        this.fetchAndCacheItems(itemType, [], 'codeset_id');
        break;
      default:
        throw new Error(`Don't know how to prefetch ${itemType}`);
    }
  }

  /*
      caching strategies
        - simple, no parameters, just cache the results
          - all_csets
        - one result object per key, object contains key
          - concepts: keyed on concept_id
          -
   */
  apiCalls = {
    all_csets: {
      expectedParams: undefined,
      api: 'get-all-csets',
      protocols: ['get'],
      cacheSlice: 'all_csets',
      key: undefined,
      alertTitle: 'Get all concept sets (partial) to populate select list',
      apiResultShape: 'array of keyed obj',
    },
    whoami: {
      expectedParams: undefined,
      api: 'whoami',
      protocols: ['get'],
      cacheSlice: 'whoami',
      key: undefined,
      alertTitle: 'Get all information about current user',
      apiResultShape: 'obj',
    },
    csets: {
      expectedParams: [],  // codeset_ids
      api: 'get-csets',
      makeQueryString: codeset_ids => 'codeset_ids=' + codeset_ids.join('|'), // pipe-delimited list
      protocols: ['get'],
      cacheSlice: 'csets',
      key: 'codeset_id',
      alertTitle: 'Get concept sets (full) for selected codeset_ids',
      apiResultShape: 'array of keyed obj',
    },
    cset_members_items: {
      expectedParams: [],  // codeset_ids
      api: 'get-cset-members-items',
      makeQueryString: codeset_ids => 'codeset_ids=' + codeset_ids.join('|'),
      protocols: ['get'],
      cacheSlice: 'cset_members_items',
      key: 'codeset_id.concept_id', // multipart key, requires splitting
      alertTitle: 'Get definition and expansion concepts (concept_set_members_items) for selected codeset_ids',
      apiResultShape: 'array of keyed obj',   //  [ {csmi}, {csmi}, ... ]
      cacheShape: 'obj of obj of obj', // cache.cset_members_items[codeset_id][concept_id] = csmi obj
    },
    concept_graph_new: {  // expects codeset_ids plus extra concept_ids (cids) if any requested
      expectedParams: {},
      dataLengthFunc: params => params.codeset_ids.length + params.cids.length,
      api: 'concept-graph',
      makeQueryString: params => {
        // params = {...params, hide_vocabs: 'null'};
        return createSearchParams(params);
      },
      protocols: ['get', 'post'],
      cacheSlice: 'concept-graph',
      // TODO: this can't be right. why no codeset_ids in key func?
      //   singleKeyFunc: concept_ids => compress(concept_ids.join('|')),
      singleKeyFunc: ({codeset_ids = [], cids = []}) =>
          compress(codeset_ids.join('|') + ';' + cids.join('|')),
      alertTitle: 'Get subgraph for all listed code sets plus additional concept_ids (cids)',
      apiResultShape: 'array of array [level, concept_id]',
      cacheShape: 'obj of array of array', // cache.edges[key] = [[src,tgt], [src,tgt], ....]
      // formatResultsFunc: edges => edges.map(edge => edge.map(String)), // might need this!!
    },
    concepts: {
      expectedParams: [],  // concept_ids
      api: 'concepts',
      makeQueryString: concept_ids => createSearchParams({id: concept_ids}),
      protocols: ['get', 'post'],
      cacheSlice: 'concepts',
      key: 'concept_id',
      alertTitle: 'Get concepts for selected concept_ids',
      apiResultShape: 'array of keyed obj',
      expectOneResultRowPerKey: true,
      createStubForMissingKey: key => ({
        concept_id: key,
        concept_name: 'Missing concept',
        domain_id: '',
        vocabulary_id: '',
        concept_class_id: '',
        standard_concept: '',
        concept_code: '',
        invalid_reason: null,
        domain_cnt: 0,
        domain: '',
        total_cnt: 0,
        distinct_person_cnt: '0',
      }),
    },
    concept_search: {
      expectedParams: '',
      api: 'concept-search',
      // makeQueryString: ({search_str, per_page}) => createSearchParams({search_str, per_page, session_id: sessionStorage.getItem('session_id')}),
      makeQueryString: search_str => createSearchParams({search_str}),
      singleKeyFunc: search_str => search_str,
      dataLengthFunc: () => 1,
      protocols: ['get'],
      cacheSlice: 'search_str',
      key: 'concept_id',
      alertTitle: 'Get concepts for search_str',
      apiResultShape: 'array of keyed obj',
      expectOneResultRowPerKey: true,
    },
    codeset_ids_by_concept_id: {
      expectedParams: [],  // concept_ids
      api: 'codeset-ids-by-concept-id',
      makeQueryString: concept_ids => createSearchParams(
          {concept_ids: concept_ids}),
      protocols: ['get', 'post'],
      cacheSlice: 'codeset_ids_by_concept_id',
      key: 'concept_id',
      alertTitle: 'Get list of codeset_ids for each concept_id',
      apiResultShape: 'obj of array',
    },
    concept_ids_by_codeset_id: {
      expectedParams: [],  // codeset_ids
      api: 'concept-ids-by-codeset-id',
      makeQueryString: codeset_ids => createSearchParams(
          {codeset_ids: codeset_ids}),
      protocols: ['get', 'post'],
      cacheSlice: 'codeset_ids_by_concept_id',
      key: 'codeset_id',
      alertTitle: 'Get list of concept_ids for each codeset_id',
      apiResultShape: 'obj of array',
    },
    researchers: {
      expectedParams: [],  // multipassIds
      api: 'researchers',
      cacheSlice: 'researchers',
      key: 'multipassId',
      makeQueryString: ids => createSearchParams({ids}),
      apiResultShape: 'obj of obj',
    },
    usage: {
      expectedParams: undefined,
      api: 'usage',
      protocols: ['get'],
      cacheSlice: 'usage',
      key: 'timestamp',
      alertTitle: 'Get usage log',
      apiResultShape: 'array of keyed obj',
    },
    n3c_comparison_rpt: {
      expectedParams: undefined,
      api: 'n3c-comparison-rpt',
      protocols: ['get'],
      cacheSlice: 'n3c_comparison_rpt',
      key: undefined,
      alertTitle: 'Get N3C comparison report',
      apiResultShape: 'array of keyed obj',
    },
    bundle_rpt: {
      expectedParams: '',
      api: 'bundle-report',
      protocols: ['get'],
      makeQueryString: bundle => createSearchParams({bundle}),
      cacheSlice: 'bundle_report',
      singleKeyFunc: ({bundle}) => bundle,
      alertTitle: 'Get N3C comparison report',
      apiResultShape: 'array of keyed obj',
    },
  };

  async fetchAndCacheItems(apiDef, params) {
    if (typeof (apiDef.expectedParams) !== typeof (params)) {
      // apiDef.expectedParams; can be undefined (all_csets) or array or string or obj
      //  for concept-graph: { codeset_ids: [], cids: [] }
      throw new Error('passed wrong type');
    }

    apiDef = {...apiDef, api_call_group_id: this.api_call_group_id};

    const dataCache = this.dataCache;

    dataCache.setCurrentEndpoint(apiDef.api);

    if (apiDef.api === 'concept-graph') {
      const {codeset_ids, cids} = params;
      let cacheKey = codeset_ids.join(',') + ';' + cids.join(',');

      let data = dataCache.cacheGet([apiDef.cacheSlice, cacheKey]);
      if (isEmpty(data)) {
        data = await this.axiosCall(apiDef.api,
            {...apiDef, data: params, backend: true});
        dataCache.cachePut([apiDef.cacheSlice, cacheKey], data);
      }
      return data;
    }
    if (typeof (apiDef.expectedParams) === 'undefined') {
      // handle no-param calls (all_csets, whoami) here; get from cache or fetch and cache
      let data = dataCache.cacheGet([apiDef.cacheSlice]);
      if (isEmpty(data)) {
        data = await this.axiosCall(apiDef.api,
            {...apiDef, data: params, backend: true});
        dataCache.cachePut([apiDef.cacheSlice], data);
      }
      return data;
    }
    if (apiDef.singleKeyFunc) {
      // handle single key per result queries
      const cacheKey = apiDef.singleKeyFunc(params);
      let data = dataCache.cacheGet([apiDef.cacheSlice, cacheKey]);
      if (isEmpty(data)) {
        data = await this.axiosCall(apiDef.api,
            {...apiDef, data: params, backend: true});
        dataCache.cachePut([apiDef.cacheSlice, cacheKey], data);
      }
      return data;
    }

    if (typeof (params) === 'object' && !Array.isArray(params)) {
      throw new Error('wasn\'t expecting a non-array object');
    }
    if (isEmpty(params)) {
      // what to do if params empty? like no codeset_ids? return undefined for now
      return apiDef.expectedParams;
    }

    // params = params.sort(); ok to get rid of sort? it's messing up codeset_id order
    params = params.map(String);
    if (params.length !== uniq(params).length) {
      throw new Error(`Why are you sending duplicate param values?`);
    }

    // use this for concepts and cset_members_items
    // TODO: FIX THIS. claude.ai got rid of getCacheForKey
    // let wholeCache = dataCache.getCacheForKey(apiDef.cacheSlice) || {};
    let wholeCache = {};
    let cachedItems = {};     // this will hold the requested items that are already cached
    let uncachedKeys = []; // requested items that still need to be fetched
    let uncachedItems = {};   // this will hold the newly fetched items
    let returnData;

    params.forEach(key => {
      if (wholeCache[key]) {
        cachedItems[key] = wholeCache[key];
      } else {
        uncachedKeys.push(key);
      }
    });
    if (uncachedKeys.length) {
      returnData = await this.axiosCall(apiDef.api,
          {...apiDef, data: uncachedKeys});
      if (!returnData) {
        throw new Error(`Error fetching from ${apiDef.api}`,
            {apiDef, uncachedKeys});
      }

      if (apiDef.expectOneResultRowPerKey) {
        if (returnData.length < uncachedKeys.length) {
          // if not getting rows for all keys, make stubs
          const stubRecords = difference(uncachedKeys,
              returnData.map(d => d[apiDef.key] + '')).map(
              key => apiDef.createStubForMissingKey(key),
          );
          returnData = returnData.concat(stubRecords);
        } else if (returnData.length !== uncachedKeys.length) {
          throw new Error('How can there be more return rows than keys?');
        }
      }

      if (apiDef.apiResultShape === 'array of keyed obj') {
        returnData.forEach(obj => {
          let keys = apiDef.key.split('.').map(k => obj[k]);
          setWith(uncachedItems, keys, obj, Object);
          dataCache.cachePut([apiDef.cacheSlice, ...keys], obj);
        });
      } else if (apiDef.apiResultShape === 'obj of array' ||
          apiDef.apiResultShape === 'obj of obj') {
        Object.entries(returnData).forEach(([key, obj]) => {
          setWith(uncachedItems, key, obj, Object);
          dataCache.cachePut([apiDef.cacheSlice, key], obj);
        });
      } else {
        throw new Error(`unexpected apiDef.apiResultShape: ${apiDef.apiResultShape}`);
      }
    }
    const results = {...cachedItems, ...uncachedItems};
    return results;
  }
}

export function getResearcherIdsFromCsets(csets) {
  return uniq(
      flatten(csets.map(cset => Object.keys((cset || {}).researchers || {}))));
}
