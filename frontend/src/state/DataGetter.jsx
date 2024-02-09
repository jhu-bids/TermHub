import {createContext, useContext,} from "react";
import {createSearchParams} from "react-router-dom";
import axios from "axios";
import {flatten, isEmpty, setWith, once, uniq, difference} from 'lodash';

import {useAlertsDispatch} from "./AppState";
import {API_ROOT} from "../env";
import {useDataCache} from "./DataCache";
import {compress} from "lz-string";

export const backend_url = (path) => `${API_ROOT}/${path}`;

const DataGetterContext = createContext(null);

export function DataGetterProvider({children}) {
	const alertsDispatch = useAlertsDispatch();
	const dataCache = useDataCache();
	const dataGetter = new DataGetter(dataCache, alertsDispatch);

	return (
			<DataGetterContext.Provider value={dataGetter}>
				{children}
			</DataGetterContext.Provider>
	);
}

export function useDataGetter() {
	return useContext(DataGetterContext);
}

class DataGetter {
	constructor(dataCache, alertsDispatch) {
		this.dataCache = dataCache;
		this.alertsDispatch = alertsDispatch;
	}
	async getApiCallGroupId() {
		const getid = once(() => {
			return this.axiosCall('next-api-call-group-id', {sendAlert: false});
		});
		this.api_call_group_id = await getid();
		console.log('api_call_group_id', this.api_call_group_id);
		return this.api_call_group_id;
	}
	async axiosCall(path, { backend = true, data, returnDataOnly = true, useGetForSmallData = true,
		verbose = false, sendAlert = true, title, makeQueryString, dataLengthFunc, skipApiGroup,
	} = {}) {
		let url = backend ? backend_url(path) : path;
		let request = { url };
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
				} else if (Array.isArray(data)) {
					dataLength = data.length;
				} else {
					throw new Error("dataLengthFunc or data.length is required");
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
			verbose && console.log("axios request", request);

			// alertAction.id = compress(JSON.stringify(request));

			let response = axios(request);

			if (sendAlert) {
				alertAction.axiosCall = response;
				this.alertsDispatch(alertAction);
				// debugger;
				response = await response;
				alertAction = {...alertAction, response, type: 'resolve', };
				delete alertAction.axiosCall;
				this.alertsDispatch(alertAction);
			}
			response = await response;
			return returnDataOnly ? response.data : response;
			// debugger;
		} catch (error) {
			if (sendAlert) {
				alertAction = {...alertAction, error, type: 'error', };
				this.alertsDispatch(alertAction);
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
			expectedParams: [],	// codeset_ids
			api: 'get-csets',
			makeQueryString: codeset_ids => 'codeset_ids=' + codeset_ids.join('|'), // pipe-delimited list
			protocols: ['get'],
			cacheSlice: 'csets',
			key: 'codeset_id',
			alertTitle: 'Get concept sets (full) for selected codeset_ids',
			apiResultShape: 'array of keyed obj',
			/* url = 'get-csets?codeset_ids=' + paramList.join('|');
				data = await this.oneToOneFetchAndCache({api: url, itemType, paramList, dataCache, alertsDispatch, keyName});
				return data; */
		},
		cset_members_items: {
			expectedParams: [],	// codeset_ids
			api: 'get-cset-members-items',
			makeQueryString: codeset_ids => 'codeset_ids=' + codeset_ids.join('|'),
			protocols: ['get'],
			cacheSlice: 'cset_members_items',
			key: 'codeset_id.concept_id', // multipart key, requires splitting
			alertTitle: 'Get definition and expansion concepts (concept_set_members_items) for selected codeset_ids',
			apiResultShape: 'array of keyed obj',	 //	[ {csmi}, {csmi}, ... ]
			cacheShape: 'obj of obj of obj', // cache.cset_members_items[codeset_id][concept_id] = csmi obj
			/* data = await Promise.all(
						paramList.map(
								async codeset_id => {
									url = backend_url(`get-cset-members-items?codeset_ids=${codeset_id}`);
									data = await this.axiosCall(url, {verbose: true, });
									return data;
								}
						)
				);
				if (isEmpty(data)) {
					debugger;
				}
				data.forEach((group, i) => {
					// this one is safe; groups will be in same order as paramList
					// structure will be:    cache.cset_members_items[codeset_id][concept_id]
					dataCache.cachePut([itemType, paramList[i]], keyBy(group, 'concept_id'));
				})
				return data; */
		},
		/*
		edges: { // expects paramList of concept_ids
			// TODO: break up cache so each slice gets its own LRU cache -- especially
			//			 because every unique set of concept_ids gets its own subgraph
			//			 and the keys and vals can be big, so old items should go away
			expectedParams: [],	// concept_ids
			api: 'subgraph',
			makeQueryString: concept_ids => createSearchParams({id: concept_ids}),
			protocols: ['get', 'post'],
			cacheSlice: 'edges',
			singleKeyFunc: concept_ids => compress(concept_ids.join('|')),
			alertTitle: 'Get subgraph for all listed concept_ids',
			apiResultShape: 'array of array [src, tgt]',
			cacheShape: 'obj of array of array', // cache.edges[key] = [[src,tgt], [src,tgt], ....]
			formatResultsFunc: edges => edges.map(edge => edge.map(String)),
			/* // TODO: @sigfried -- fix to include additional concepts
				// each unique set of concept_ids gets a unique set of edges
				// check cache first (because this request won't come from fetchAndCacheItemsByKey)
				// TODO: maybe don't have to key by entire concept_id list -- front end could check for possibly missing edges
				cacheKey = paramList.join('|');
				data = dataCache.cacheGet([itemType, cacheKey]);
				if (isEmpty(data)) {
					data = await this.axiosCall('subgraph', {title: 'Get edges for codeset_ids', verbose: true,
						backend: true, data: paramList, useGetForSmallData: true, apiGetParamName: 'id'});
					data = formatEdges(data);
					dataCache.cachePut([itemType, cacheKey], data);
				}
				return data; * /
		}, */
		concept_graph: { // expects paramList of concept_ids
			expectedParams: [],	// concept_ids
			api: 'concept-graph',
			makeQueryString: concept_ids => createSearchParams({id: concept_ids}),
			protocols: ['get', 'post'],
			cacheSlice: 'graph-and-layout',
			singleKeyFunc: concept_ids => compress(concept_ids.join('|')),
			alertTitle: 'Get subgraph and layout for all listed concept_ids',
			// apiResultShape: 'array of array [level, concept_id]',
			// cacheShape: 'obj of array of array', // cache.edges[key] = [[src,tgt], [src,tgt], ....]
			// formatResultsFunc: edges => edges.map(edge => edge.map(String)), // might need this!!
		},
		indented_concept_list: {	// expects codeset_ids plus extra concept_ids (cids) if any requested
			expectedParams: {},
			dataLengthFunc: params => params.codeset_ids.length + params.cids.length,
			api: 'concept-graph',
			// api: 'indented-concept-list',	# TODO: this is the same as concept-graph, but with indented=true
			makeQueryString: params => createSearchParams({...params, indented: true}),
			protocols: ['get', 'post'],
			cacheSlice: 'concept-graph',
			// TODO: this can't be right. why no codeset_ids in key func?
			// 	singleKeyFunc: concept_ids => compress(concept_ids.join('|')),
			singleKeyFunc: ({codeset_ids=[], cids=[]}) =>
				compress(codeset_ids.join('|') + ';' + cids.join('|') + ';indented'),
			alertTitle: 'Get subgraph for all listed code sets plus additional concept_ids (cids)',
			apiResultShape: 'array of array [level, concept_id]',
			cacheShape: 'obj of array of array', // cache.edges[key] = [[src,tgt], [src,tgt], ....]
			// formatResultsFunc: edges => edges.map(edge => edge.map(String)), // might need this!!
		},
		concept_graph_new: {	// expects codeset_ids plus extra concept_ids (cids) if any requested
			// was indented_concept_list
			expectedParams: {},
			dataLengthFunc: params => params.codeset_ids.length + params.cids.length,
			// api: 'indented-concept-list',
			api: 'concept-graph',
			makeQueryString: params => createSearchParams(params),
			protocols: ['get', 'post'],
			cacheSlice: 'concept-graph',
			// TODO: this can't be right. why no codeset_ids in key func?
			// 	singleKeyFunc: concept_ids => compress(concept_ids.join('|')),
			singleKeyFunc: ({codeset_ids=[], cids=[]}) =>
					compress(codeset_ids.join('|') + ';' + cids.join('|')),
			alertTitle: 'Get subgraph for all listed code sets plus additional concept_ids (cids)',
			apiResultShape: 'array of array [level, concept_id]',
			cacheShape: 'obj of array of array', // cache.edges[key] = [[src,tgt], [src,tgt], ....]
			// formatResultsFunc: edges => edges.map(edge => edge.map(String)), // might need this!!
		},
		/* everything else

			case 'concepts':
			case 'codeset-ids-by-concept-id':
			case 'researchers':
				apiGetParamName = 'id';
			case 'concept-ids-by-codeset-id':
				apiGetParamName = apiGetParamName || 'codeset_ids';
				useGetForSmallData = true;  // can use this for api endpoints that have both post and get versions
				api = itemType;
				url = backend_url(api);
				data = await this.oneToOneFetchAndCache({itemType, keyName, api, postData: paramList, paramList,
																									useGetForSmallData, apiGetParamName, dataCache, alertsDispatch});
				return data;

		 */
		concepts: {
			expectedParams: [],	// concept_ids
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
				distinct_person_cnt: '0'
			})
		},
		codeset_ids_by_concept_id: {
			expectedParams: [],	// concept_ids
			api: 'codeset-ids-by-concept-id',
			makeQueryString: concept_ids => createSearchParams({concept_ids: concept_ids}),
			protocols: ['get', 'post'],
			cacheSlice: 'codeset_ids_by_concept_id',
			key: 'concept_id',
			alertTitle: 'Get list of codeset_ids for each concept_id',
			apiResultShape: 'obj of array',
		},
		concept_ids_by_codeset_id: {
			expectedParams: [],	// codeset_ids
			api: 'concept-ids-by-codeset-id',
			makeQueryString: codeset_ids => createSearchParams({codeset_ids: codeset_ids}),
			protocols: ['get', 'post'],
			cacheSlice: 'codeset_ids_by_concept_id',
			key: 'codeset_id',
			alertTitle: 'Get list of concept_ids for each codeset_id',
			apiResultShape: 'obj of array',
		},
		researchers: {
			expectedParams: [],	// multipassIds
			api: 'researchers',
			cacheSlice: 'researchers',
			key: 'multipassId',
			makeQueryString: ids => createSearchParams({ids}),
			apiResultShape: 'obj of obj',
		},
	}
	async fetchAndCacheItems(apiDef, params) {
		if (typeof(apiDef.expectedParams) !== typeof(params)) {
			// apiDef.expectedParams, for now, can be undefined (all_csets) or
			// array (everything else).
			// for indented_concept_list: { codeset_ids: [], additional_concept_ids: [] }
			throw new Error("passed wrong type");
		}

		apiDef = {...apiDef, api_call_group_id: this.api_call_group_id};

		const dataCache = this.dataCache;

		if (apiDef.api === 'concept-graph') { // indented_concept_list: { codeset_ids: [], additional_concept_ids: [] }
			const {codeset_ids, cids, indented} = params;
			let cacheKey = codeset_ids.join(',') + ';' + cids.join(',') + `${indented ? ';indented' : ''}`;

			let data = dataCache.cacheGet([apiDef.cacheSlice, cacheKey]);
			if (isEmpty(data)) {
				data = await this.axiosCall(apiDef.api, {...apiDef, data: params, backend: true, });
				dataCache.cachePut([apiDef.cacheSlice, cacheKey], data);
			}
			return data;
		}
		if (typeof(apiDef.expectedParams) === 'undefined') {
			// handle no-param calls (all_csets, whoami) here; get from cache or fetch and cache
			let data = dataCache.cacheGet([apiDef.cacheSlice]);
			if (isEmpty(data)) {
				data = await this.axiosCall(apiDef.api, {...apiDef, data: params, backend: true, });
				dataCache.cachePut([apiDef.cacheSlice], data);
			}
			return data;
		}
		if(apiDef.singleKeyFunc) {
			// handle single key per result queries
			const cacheKey = apiDef.singleKeyFunc(params);
			let data = dataCache.cacheGet([apiDef.cacheSlice, cacheKey]);
			if (isEmpty(data)) {
				data = await this.axiosCall(apiDef.api, {...apiDef, data: params, backend: true, });
				dataCache.cachePut([apiDef.cacheSlice, cacheKey], data);
			}
			return data;
		}

		if (typeof(params) === 'object' && !Array.isArray(params)) {
			throw new Error("wasn't expecting a non-array object")
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
		let wholeCache = dataCache.getCacheForKey(apiDef.cacheSlice) || {};
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
		})
		if (uncachedKeys.length) {
			returnData = await this.axiosCall(apiDef.api, {...apiDef, data: uncachedKeys});
			if (!returnData) {
				throw new Error(`Error fetching from ${apiDef.api}`, {apiDef, uncachedKeys});
			}

			if (apiDef.expectOneResultRowPerKey) {
				if (returnData.length < uncachedKeys.length) {
					// if not getting rows for all keys, make stubs
					const stubRecords = difference(uncachedKeys, returnData.map(d => d[apiDef.key]+'')).map(
							key => apiDef.createStubForMissingKey(key)
					);
					returnData = returnData.concat(stubRecords);
				} else if (returnData.length !== uncachedKeys.length) {
					throw new Error("How can there be more return rows than keys?");
				}
			}

			if (apiDef.apiResultShape === 'array of keyed obj') {
				returnData.forEach(obj => {
					let keys = apiDef.key.split('.').map(k => obj[k]);
					setWith(uncachedItems, keys, obj, Object);
					// setWith(..., Object) in order to create objects instead of arrays even with numeric keys
					dataCache.cachePut([apiDef.cacheSlice, ...keys], obj);
				});
			} else if (apiDef.apiResultShape === 'obj of array' || apiDef.apiResultShape === 'obj of obj') {
				Object.entries(returnData).forEach(([key, obj]) => {
					setWith(uncachedItems, key, obj, Object);
					dataCache.cachePut([apiDef.cacheSlice, key], obj);
				});
			} else {
				debugger;
			}
		}
		const results = {...cachedItems, ...uncachedItems};
		return results;
			// if (Array.isArray(data)) {}	get this code from oneToOneFetchAndCache
			/*
			if (keyName) {
				if (keyName.split('.').length > 1) {
					throw new Error("write code to handle this");
				}
				// this doesn't put stuff in the cache, just in uncachedItems (obviously, but I got confused about it at one point)
				data.forEach(item => set(uncachedItems, item[keyName], item));
			} else {
				// was doing this for everything before but ending up with items assigned to the wrong keys sometimes
				// 	going forward, the server should probably return everything in a keyed dict
				debugger;
				data.forEach((item, i) => uncachedItems[uncachedKeys[i]] = item);
			}

			 */



		/*
		// from oneToOneFetchAndCache
		if (Array.isArray(data)) {
			if (keyName) {
				data.forEach(item => {
					dataCache.cachePut([itemType, item[keyName]], item);
				});
			} else {
				throw new Error("don't be getting arrays back: get stuff back with keys...maybe?");
			}
		} else {
			Object.entries(data).map(([key, val]) => {
				dataCache.cachePut([itemType, key], val);
			});
		}
		*/

		/*
		const not_found = uncachedKeys.filter(key => !(key in results));
		if (not_found.length) {
			// TODO: let user see warning somehow
			console.warn(`Warning in DataCache.fetchAndCacheItemsByKey: failed to fetch ${itemType}s for ${not_found.join(', ')}`);
		}
		if (returnFunc) {
			return returnFunc(results);
		}
		if (shape === 'array') {
			let vals = Object.values(results);
			if (keyName) {	// this was an attempt to fix things assigned to wrong keys, not sure if it's needed
				vals = sortBy(vals, d => d[keyName]);
			}
			return vals;
		}
		return results;

		 */
	}
}

export function getResearcherIdsFromCsets(csets) {
	return uniq(flatten(csets.map(cset => Object.keys(cset.researchers))));
}
