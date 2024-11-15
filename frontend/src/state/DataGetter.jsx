import {createContext, useContext} from 'react';
import {createSearchParams} from 'react-router-dom';
import axios from 'axios';
import {flatten, isEmpty, setWith, once, uniq, difference} from 'lodash';

// import {useAlertsDispatch} from "./AppState";
import {API_ROOT} from '../env';
import {useDataCache, } from './DataCache';
import {compress} from 'lz-string';

export const backend_url = (path) => `${API_ROOT}/${path}`;

const DataGetterContext = createContext(null);

export function DataGetterProvider({children}) {
  // const alertsDispatch = useAlertsDispatch();
  const dataCache = useDataCache();
  const dataGetter = new DataGetter(dataCache /*alertsDispatch*/);

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
    protocols = ['get'], // could include get, post, or both
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
    let qs = path.match(/\?/) ? '' : '?';
    if (path !== 'next-api-call-group-id' && this.api_call_group_id &&
        !skipApiGroup) {
      qs = qs + 'api_call_group_id=' + this.api_call_group_id + '&';
    }
    try {
      if (protocols.length === 1) {
        request.method = protocols[0];
      } else if (typeof (data) === 'undefined') {
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
        } else {
          request.method = 'post';
        }
      }
      if (request.method === 'get') {
        if (makeQueryString) {
          qs += makeQueryString(data).toString();
        }
        request.url = url + qs;
      } else {
        request.data = data;
      }
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
      singleKeyFunc: ({codeset_ids = [], cids = []}) =>
          compress(codeset_ids.join('|') + ';' + cids.join('|')),
      alertTitle: 'Get subgraph for all listed code sets plus additional concept_ids (cids)',
      apiResultShape: 'array of array [level, concept_id]',
      // cacheShape: 'obj of array of array', // cache.edges[key] = [[src,tgt], [src,tgt], ....]
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
    /* concept_mappings: {
      expectedParams: [], // concept_ids array
      api: 'get-similar-concepts',
      protocols: ['post'],
      data: concept_ids => ({
        concept_ids,
        which: 'to'  // Use OHDSI standard mapping relationships
      }),
      cacheSlice: 'concept_mappings',
      key: 'source_concept_id',
      alertTitle: 'Get mapped concepts for concept IDs',
      apiResultShape: 'obj of array',  // matches your API's return format: {source_id: [mapped_concepts]}
    }, */
    related_cset_concept_counts: {
      expectedParams: [],  // concept_ids
      api: 'related-cset-concept_counts',
      makeQueryString: concept_ids => createSearchParams({concept_ids}),
      protocols: ['post'],
      cacheSlice: 'related_cset_concept_counts',
      key: 'concept_id',
      apiResultShape: 'obj',
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
      // apiResultShape: 'array of keyed obj',
    },
    n3c_comparison_rpt: {
      expectedParams: undefined,
      api: 'n3c-comparison-rpt',
      protocols: ['get'],
      cacheSlice: 'n3c_comparison_rpt',
      key: undefined,
      alertTitle: 'Get N3C comparison report',
      // apiResultShape: 'array of keyed obj',
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

    if (typeof (apiDef.expectedParams) === 'undefined') {
      // handle no-param calls (all_csets, whoami) here; get from cache or fetch and cache
      let data = await dataCache.cacheGet(apiDef.cacheSlice);
      if (isEmpty(data)) {
        data = await this.axiosCall(apiDef.api,
            {...apiDef, data: params, backend: true});
        dataCache.cachePut(apiDef.cacheSlice, data);
      }
      return data;
    }
    if (apiDef.singleKeyFunc) {
      // handle single key per result queries
      const cacheKey = apiDef.singleKeyFunc(params);
      let data = await dataCache.cacheGet([apiDef.cacheSlice, cacheKey]);
      if (isEmpty(data)) {
        data = await this.axiosCall(apiDef.api,
            {...apiDef, data: params, backend: true});
        dataCache.cachePut([apiDef.cacheSlice, cacheKey], data);
      }
      return data;
    }
    if (apiDef.api === 'concept-graph') {
      const {codeset_ids, cids} = params;
      let cacheKey = codeset_ids.join(',') + ';' + cids.join(',');

      let data = await dataCache.cacheGet([apiDef.cacheSlice, cacheKey]);
      if (isEmpty(data)) {
        data = await this.axiosCall(apiDef.api,
            {...apiDef, data: params, backend: true});
        dataCache.cachePut([apiDef.cacheSlice, cacheKey], data);
      }
      return data;
    }
    if (isEmpty(params)) {
      // what to do if params empty? like no codeset_ids? return undefined for now
      return apiDef.expectedParams;
    }

    if ( ! [ 'array of keyed obj',
          'obj of array',
          'obj of obj'].includes(apiDef.apiResultShape)) {
      throw new Error(`not sure how to handle apiDef ${apiDef.api}`);
    }

    if (typeof (params) === 'object' && !Array.isArray(params)) {
      throw new Error('wasn\'t expecting a non-array object');
    }

    params = params.map(String);
    if (params.length !== uniq(params).length) {
      throw new Error(`Why are you sending duplicate param values?`);
    }

    // 2024-11-13. Trying new strategy.
    //  Don't put individual keyed items in cache, put the whole slice at once.
    //  Only fetch keys not already in cache.
    //  But then get rid of all keys not in the current request.
    //  As long as the app doesn't use the same cache slice for different purposes,
    //    any time a key is no longer present, there's a good chance they aren't
    //    interested in it anymore.
    //  This might mean that cache pruning is barely necessary anymore.
    //  Previously, with, e.g., tens of thousands of concepts or cset_members_items,
    //    the cache would fill up with metadata.

    // let wholeCache = await dataCache.getWholeSlice(apiDef.cacheSlice) || {};
    let wholeCache = dataCache.cacheGet(apiDef.cacheSlice) || {};
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
        throw new Error(`Error fetching from ${apiDef.api}`); // {apiDef, uncachedKeys});
      }

      if (apiDef.expectOneResultRowPerKey) {
        if (returnData.length < uncachedKeys.length) {
          console.warn("why do we need stubs?");
          debugger;
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

      if (apiDef.apiResultShape === 'obj of array' ||
          apiDef.apiResultShape === 'obj of obj') {
        uncachedItems = returnData;
      } else {
        let keyNames = apiDef.key.split('.');
        returnData.forEach(obj => {
          let keys = keyNames.map(k => obj[k]);
          setWith(uncachedItems, keys, obj, Object);
        });
      }

      const results = {...cachedItems, ...uncachedItems};
      await dataCache.cachePut(apiDef.cacheSlice, results);
      return results;
    }
    return cachedItems;
  }
}

export function getResearcherIdsFromCsets(csets) {
  return uniq(
      flatten(csets.map(cset => Object.keys((cset || {}).researchers || {}))));
}
