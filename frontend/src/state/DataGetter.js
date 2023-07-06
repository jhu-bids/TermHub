import {createContext, useContext,} from "react";
import {createSearchParams} from "react-router-dom";
import axios from "axios";
import {flatten, isEmpty, keyBy, uniq} from 'lodash';

import {useAppState, useStateSlice} from "./AppState";
import {formatEdges} from "../components/ConceptGraph";
import {API_ROOT} from "../env";
import {useDataCache} from "./DataCache";

export const backend_url = (path) => `${API_ROOT}/${path}`;

const DataGetterContext = createContext(null);

export function DataGetterProvider({children}) {
	const dataCache = useDataCache();
	const [, alertsDispatch] = useStateSlice('alerts');
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
	async fetchItems(itemType, paramList, ) {
		const dataCache = this.dataCache;
		const alertsDispatch = this.alertsDispatch;
		if (isEmpty(paramList)) {
			return [];
			throw new Error(`fetchItems for ${itemType} requires paramList`);
		}
		let url,
				data,
				cacheKey,
				api,
				apiGetParamName,
				useGetForSmallData;

		switch (itemType) {
			case 'concepts':
			case 'codeset_ids_by_concept_id':
			case 'researchers':
				apiGetParamName = 'id';
			case 'concept_ids_by_codeset_id':
				apiGetParamName = apiGetParamName || 'codeset_ids';
				useGetForSmallData = true;  // can use this for api endpoints that have both post and get versions
				api = itemType.replaceAll('_', '-');
				url = backend_url(api);
				data = await this.oneToOneFetchAndCache(itemType, api, paramList, paramList, useGetForSmallData, apiGetParamName, dataCache, alertsDispatch);
				data.forEach((group, i) => {
					dataCache.cachePut([itemType, paramList[i]], group);
				})
				return data;

			case 'csets':
				url = 'get-csets?codeset_ids=' + paramList.join('|');
				data = await this.oneToOneFetchAndCache(itemType, url, undefined, paramList, null, null, dataCache, alertsDispatch);
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
					dataCache.cachePut([itemType, paramList[i]], keyBy(group, 'concept_id'));
				})
				return data;

			case 'edges': // expects paramList of concept_ids
				// each unique set of concept_ids gets a unique set of edges
				// check cache first (because this request won't come from getItemsByKey)
				cacheKey = paramList.join('|');
				data = dataCache.cacheGet([itemType, cacheKey]);
				if (isEmpty(data)) {
					data = await this.axiosCall('subgraph',
																						{backend: true, data: paramList, useGetForSmallData: true, apiGetParamName: 'id'});
					data = formatEdges(data);
					dataCache.cachePut([itemType, cacheKey], data);
				}
				return data;

			case 'all_csets':
				data = dataCache.cacheGet([itemType]);
				if (isEmpty(data)) {
					url = backend_url('get-all-csets');
					data = await this.axiosCall(url);
					// data = keyBy(data, 'codeset_id');
					dataCache.cachePut([itemType], data);
				}
				return data;

			default:
				throw new Error(`Don't know how to fetch ${itemType}`);
		}
	}
	prefetch(props) {
		const {itemType, codeset_ids} = props;
		switch (itemType) {
			case 'all_csets':
				this.fetchItems(itemType);
				break;
			default:
				throw new Error(`Don't know how to prefetch ${itemType}`);
		}
	}
	async axiosCall(path, { backend = false, data, returnDataOnly = true, useGetForSmallData = false,
										apiGetParamName, verbose = true, sendAlert = true,
	} = {}) {
		let url = backend ? backend_url(path) : path;
		let alertAction = {
			type: 'create',
			payload: { type: 'axiosCall', path, data, },
		};
		let axPromise, dispReturn;
		try {
			if (typeof (data) === 'undefined') {
				verbose && console.log("axios.get url: ", url);
				axPromise = axios.get(url);
			} else {
				if (useGetForSmallData && data.length <= 1000) {
					let qs = createSearchParams({[apiGetParamName]: data});
					url = url + '?' + qs;
					verbose && console.log("axios.get url: ", url);
					axPromise = axios.get(url);
				} else {
					verbose && console.log("axios.post url: ", url, 'data', data);
					axPromise = axios.post(url, data);
				}
			}
			if (sendAlert) {
				alertAction.payload.url = url;
				alertAction.payload.axiosCall = axPromise;
				dispReturn = this.alertsDispatch(alertAction);
			}
			let results = await axPromise;
			console.log(alertAction, results, dispReturn);
			debugger;
			return returnDataOnly ? results.data : results;
		} catch (error) {
			console.log(error.toJSON());
		}

	}
	async oneToOneFetchAndCache(itemType, api, postData, paramList, useGetForSmallData, apiGetParamName, dataCache) {
		// We expect a 1-to-1 relationship between paramList items (e.g., concept_ids)
		//  and retrieved items (e.g., concepts)
		let data = await this.axiosCall(api, {backend: true, data: postData, useGetForSmallData, apiGetParamName});

		if (!Array.isArray(data)) {
			data = Object.values(data);
		}
		if (data.length !== paramList.length) {
			throw new Error(`oneToOneFetchAndCache for ${itemType} requires matching result data and paramList lengths`);
		}
		data.forEach((item, i) => {
			dataCache.cachePut([itemType, paramList[i]], item);
		});
		return data;
	}
}


export function getResearcherIdsFromCsets(csets) {
	return uniq(flatten(csets.map(cset => Object.keys(cset.researchers))));
}