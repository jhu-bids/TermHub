import {createContext, useContext,} from "react";
import {createSearchParams} from "react-router-dom";
import axios from "axios";
import {flatten, isEmpty, keyBy, uniq} from 'lodash';

import {useAppState, useStateSlice} from "./AppState";
import {formatEdges} from "../components/ConceptGraph";
import {API_ROOT} from "../env";
import {useDataCache} from "./DataCache";
import {compress} from "lz-string";

export const backend_url = (path) => `${API_ROOT}/${path}`;

const DataGetterContext = createContext(null);

export function DataGetterProvider({children}) {
	const dataCache = useDataCache();
	const [alerts, alertsDispatch] = useStateSlice('alerts');
	const dataGetter = new DataGetter(dataCache, alertsDispatch);
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
	async axiosCall(path, { backend = false, data, returnDataOnly = true, useGetForSmallData = false,
		apiGetParamName, verbose = false, sendAlert = true, title,
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
					let qs = createSearchParams({[apiGetParamName]: data});
					request.url = url + '?' + qs;
				} else {
					request.method = 'post';
					request.data = data;
				}
			}
			verbose && console.log("axios request", request);

			alertAction.id = compress(JSON.stringify(request));

			console.log(request);
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
	async fetchAndCacheItems(itemType, paramList, keyName) {
		const dataCache = this.dataCache;
		const alertsDispatch = this.alertsDispatch;
		if (isEmpty(paramList)) {
			return [];
			throw new Error(`fetchAndCacheItems for ${itemType} requires paramList`);
		}
		let url,
				data,
				cacheKey,
				api,
				apiGetParamName,
				useGetForSmallData;

		switch (itemType) {
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
				/*
				oneToOneFetchAndCache already does the caching
				data.forEach((group, i) => {
					// dataCache.cachePut([itemType, paramList[i]], group);
					dataCache.cachePut([itemType, keyName], group);
				})
				 */
				return data;

			case 'csets':
				url = 'get-csets?codeset_ids=' + paramList.join('|');
				data = await this.oneToOneFetchAndCache({api: url, itemType, paramList, dataCache, alertsDispatch, keyName});
				return data;

			case 'cset_members_items':
				data = await Promise.all(
						paramList.map(
								async codeset_id => {
									url = backend_url(`get-cset-members-items?codeset_ids=${codeset_id}`);
									data = await this.axiosCall(url);
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
				return data;

			case 'edges': // expects paramList of concept_ids
				// TODO: @sigfried -- fix to include additional concepts
				// each unique set of concept_ids gets a unique set of edges
				// check cache first (because this request won't come from fetchAndCacheItemsByKey)
				// TODO: maybe don't have to key by entire concept_id list -- front end could check for possibly missing edges
				cacheKey = paramList.join('|');
				data = dataCache.cacheGet([itemType, cacheKey]);
				if (isEmpty(data)) {
					data = await this.axiosCall('subgraph', {title: 'Get edges for codeset_ids',
						backend: true, data: paramList, useGetForSmallData: true, apiGetParamName: 'id'});
					data = formatEdges(data);
					dataCache.cachePut([itemType, cacheKey], data);
				}
				return data;

			case 'all_csets':
				data = dataCache.cacheGet([itemType]);
				if (isEmpty(data)) {
					url = backend_url('get-all-csets');
					data = await this.axiosCall(url, {title: 'Get all concept sets for select list'});
					// data = keyBy(data, 'codeset_id');
					dataCache.cachePut([itemType], data);
				}
				return data;

			default:
				throw new Error(`Don't know how to fetch ${itemType}`);
		}
	}
	async oneToOneFetchAndCache({itemType, api, postData, paramList, useGetForSmallData,
																apiGetParamName, dataCache, keyName}) {
		// We expect a 1-to-1 relationship between paramList items (e.g., concept_ids)
		//  and retrieved items (e.g., concepts)
		console.warn('can we get rid of this function? too much indirection')
		let data = await this.axiosCall(api, {title: `Fetch and cache ${itemType}`, backend: true,
			data: postData, useGetForSmallData, apiGetParamName});

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
		return data;
	}
}


export function getResearcherIdsFromCsets(csets) {
	return uniq(flatten(csets.map(cset => Object.keys(cset.researchers))));
}