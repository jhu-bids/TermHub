import {createContext, useContext,} from "react";
import {createSearchParams} from "react-router-dom";
import axios from "axios";
import {flatten, isEmpty, keyBy, uniq, set, sortBy, } from 'lodash';
import {useAppState, useStateSlice} from "./AppState";
// import {formatEdges} from "../components/ConceptGraph";
import {API_ROOT} from "../env";
import {useDataCache} from "./DataCache";
import {compress} from "lz-string";

export const backend_url = (path) => `${API_ROOT}/${path}`;

const DataGetterContext = createContext(null);

export function DataGetterProvider({children}) {
	const [alerts, alertsDispatch] = useStateSlice('alerts');

	// dataGetter needs dataCache to cache data, DataCacheProvider is invoked
	//	first so dataGetter can use it
	const dataCache = useDataCache();
	const dataGetter = new DataGetter(dataCache, alertsDispatch);
	// but dataCache (for checkCache) also needs dataGetter, the following
	//	line gives it access without requiring circular import
	dataCache.setDataGetter(dataGetter);

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
	async axiosCall(path, { backend = true, data, returnDataOnly = true, useGetForSmallData = true,
		apiGetParamName, verbose = true, sendAlert = true, title, makeQueryString,
	} = {}) {
		let url = backend ? backend_url(path) : path;
		let request = { url };
		let alertAction = {
			request,
			type: 'create',
			eventType: 'axiosCall',
			title: title || path,
		};
		try {
			if (typeof (data) === 'undefined') {
				request.method = 'get';
			} else {
				if (useGetForSmallData && data.length <= 1000) {
					request.method = 'get';
					let qs = makeQueryString(data);
					request.url = url + '?' + qs;
				} else {
					request.method = 'post';
					request.data = data;
				}
			}
			verbose && console.log("axios request", request);

			alertAction.id = compress(JSON.stringify(request));

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
			// cacheShape: 'array of obj',
			/* data = dataCache.cacheGet([itemType]);
          if (isEmpty(data)) {
            url = backend_url('get-all-csets');
            data = await this.axiosCall(url, {title: 'Get all concept sets for select list', verbose: true});
            dataCache.cachePut([itemType], data);
          }
          return data; */
		},
		csets: {
			expectedParams: [],	// codeset_ids
			api: 'get-csets',
			apiGetParamName: 'codeset_ids',
			makeQueryString: codeset_ids => 'codeset_ids=' + codeset_ids.join('|'), // pipe-delimited list
			protocols: ['get'],
			cacheSlice: 'csets',
			key: 'codeset_id',
			alertTitle: 'Get concept sets (full) for selected codeset_ids',
			apiResultShape: 'array of keyed obj',
			// cacheShape: 'array of obj',
			/* url = 'get-csets?codeset_ids=' + paramList.join('|');
				data = await this.oneToOneFetchAndCache({api: url, itemType, paramList, dataCache, alertsDispatch, keyName});
				return data; */
		},
		cset_members_items: {
			expectedParams: [],	// codeset_ids
			api: 'get-cset-members-items',
			apiGetParamName: 'codeset_ids',
			makeQueryString: codeset_ids => 'codeset_ids=' + codeset_ids.join('|'),
			protocols: ['get'],
			cacheSlice: 'cset_members_items',
			key: 'codeset_id.concept_id', //	lodash set will work with key path
			cachePutFunc: csmi => {
				// assuming if we ask for it, it's not cached already; still have to figure
				//	out how to check the cache for these
				this.dataCache.cachePut(['cset_members_items', csmi.codeset_id, csmi.concept_id], csmi);
			},
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
		edges: { // expects paramList of concept_ids
			// TODO: break up cache so each slice gets its own LRU cache -- especially
			//			 because every unique set of concept_ids gets its own subgraph
			//			 and the keys and vals can be big, so old items should go away
			expectedParams: [],	// concept_ids
			api: 'subgraph',
			apiGetParamName: 'id',
			makeQueryString: concept_ids => createSearchParams({id: concept_ids}),
			protocols: ['get', 'post'],
			cacheSlice: 'edges',
			singleKeyFunc: concept_ids => compress(concept_ids.join('|')),
			alertTitle: 'Get subgraph for all listed concept_ids',
			apiResultShape: 'array of array [src, tgt]',
			cacheShape: 'obj of array of array', // cache.edges[key] = [[src,tgt], [src,tgt], ....]
			formatResultsFunc: edges => edges.map(edge => edge.map(String)),
			/*// TODO: @sigfried -- fix to include additional concepts
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
				return data; */
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
			apiGetParamName: 'id',
			makeQueryString: concept_ids => createSearchParams({id: concept_ids}),
			protocols: ['get', 'post'],
			cacheSlice: 'concepts',
			key: 'concept_id',
			alertTitle: 'Get concepts for selected concept_ids',
			apiResultShape: 'array of keyed obj',
			// cacheShape: 'array of obj',
		},
		codeset_ids_by_concept_id: {
			expectedParams: [],	// concept_ids
			api: 'codeset-ids-by-concept-id',
			apiGetParamName: 'concept_ids',
			makeQueryString: concept_ids => createSearchParams({concept_ids}),
			protocols: ['get', 'post'],
			cacheSlice: 'codeset_ids_by_concept_id',
			key: 'concept_id',
			alertTitle: 'Get list of codeset_ids for each concept_id',
			apiResultShape: 'obj of array',
			// cacheShape: 'obj of array',
		},
		concept_ids_by_codeset_id: {
			expectedParams: [],	// codeset_ids
			api: 'concept-ids-by-codeset-id',
			apiGetParamName: 'codeset_ids',
			makeQueryString: codeset_ids => createSearchParams({codeset_ids}),
			protocols: ['get', 'post'],
			cacheSlice: 'codeset_ids_by_concept_id',
			key: 'codeset_id',
			alertTitle: 'Get list of concept_ids for each codeset_id',
			apiResultShape: 'obj of array',
			// cacheShape: 'obj of array',
		},
		researchers: {
			expectedParams: [],	// multipassIds
			api: 'researchers',
			cacheSlice: 'researchers',
			key: 'multipassId',
			apiGetParamName: 'id',
			makeQueryString: id => createSearchParams({id}),
			shape: 'obj of obj',
		},
	}
	async fetchAndCacheItems(apiDef, params) {
		if (typeof(apiDef.expectedParams) !== typeof(params)) {
			// apiDef.expectedParams, for now, can be undefined (all_csets) or
			// array (everything else). In future might have occasion to handle
			// objects or strings
			throw new Error("passed wrong type");
		}

		const dataCache = this.dataCache;

		if (typeof(apiDef.expectedParams) === 'undefined') {
			// handle no-param calls (all_csets) here; get from cache or fetch and cache
			let data = dataCache.cacheGet([apiDef.cacheSlice]);
			if (isEmpty(data)) {
				data = await this.axiosCall(apiDef.api, {...apiDef, data: params, backend: true, });
				dataCache.cachePut([apiDef.cacheSlice], data);
			}
			return data;
		}
		if(apiDef.singleKeyFunc) {
			// handle single key per result queries
			let data = dataCache.cacheGet([apiDef.cacheSlice]);
			if (isEmpty(data)) {
				data = await this.axiosCall(apiDef.api, {...apiDef, data: params, backend: true, });
				const cacheKey = apiDef.singleKeyFunc(params);
				dataCache.cachePut([apiDef.cacheSlice, cacheKey], data);
			}
			return data;
		}

		if (typeof(params) === 'object' && !Array.isArray(params)) {
			throw new Error("wasn't expecting a non-array object")
		}
		if (isEmpty(params)) {
			// what to do if params empty? like no codeset_ids? return undefined for now
			return;
		}

		params = params.sort();
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
			if (apiDef.apiResultShape === 'array of keyed obj') {
				returnData.forEach(obj => set(uncachedItems, obj[apiDef.key], obj));
			} else if (apiDef.apiResultShape === 'obj of array') {
				Object.entries(returnData).forEach(([key, obj]) => set(uncachedItems, key, obj));

			} else {
				debugger;
			}
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
		}



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
		const results = {...cachedItems, ...uncachedItems};
		return returnData;

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