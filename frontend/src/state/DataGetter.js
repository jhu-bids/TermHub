import {flatten, isEmpty, keyBy, uniq} from 'lodash';
import {createSearchParams} from "react-router-dom";
import axios from "axios";

import {formatEdges} from "../components/ConceptGraph";
import {API_ROOT} from "../env";

export async function fetchItems(itemType, paramList, dataCache) {
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
			data = await oneToOneFetchAndCache(itemType, api, paramList, paramList, useGetForSmallData, apiGetParamName, dataCache);
			data.forEach((group, i) => {
				dataCache.cachePut([itemType, paramList[i]], group);
			})
			return data;

		case 'csets':
			url = 'get-csets?codeset_ids=' + paramList.join('|');
			data = await oneToOneFetchAndCache(itemType, url, undefined, paramList, null, null, dataCache);
			return data;

		case 'cset_members_items':
			data = await Promise.all(
					paramList.map(
							async codeset_id => {
								url = backend_url(`get-cset-members-items?codeset_ids=${codeset_id}`);
								data = await axiosCall(url);

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
				data = await axiosCall('subgraph',
															 {backend: true, data: paramList, useGetForSmallData: true, apiGetParamName: 'id'});
				data = formatEdges(data);
				dataCache.cachePut([itemType, cacheKey], data);
			}
			return data;

		case 'all_csets':
			data = dataCache.cacheGet([itemType]);
			if (isEmpty(data)) {
				url = backend_url('get-all-csets');
				data = await axiosCall(url);
				// data = keyBy(data, 'codeset_id');
				dataCache.cachePut([itemType], data);
			}
			return data;

		default:
			throw new Error(`Don't know how to fetch ${itemType}`);
	}
}

async function oneToOneFetchAndCache(itemType, api, postData, paramList, useGetForSmallData, apiGetParamName, dataCache) {
	// We expect a 1-to-1 relationship between paramList items (e.g., concept_ids)
	//  and retrieved items (e.g., concepts)
	let data = await axiosCall(api, {backend: true, data: postData, useGetForSmallData, apiGetParamName});

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

export function getResearcherIdsFromCsets(csets) {
	return uniq(flatten(csets.map(cset => Object.keys(cset.researchers))));
}

export const backend_url = (path) => `${API_ROOT}/${path}`;

export async function axiosCall(path, {
	backend = false, data, returnDataOnly = true, useGetForSmallData = false,
	apiGetParamName, verbose = true,
} = {}) {
	let url = backend ? backend_url(path) : path;
	try {
		let results;
		if (typeof (data) === 'undefined') {
			verbose && console.log("axios.get url: ", url);
			results = await axios.get(url);
		} else {
			if (useGetForSmallData && data.length <= 1000) {
				let qs = createSearchParams({[apiGetParamName]: data});
				url = url + '?' + qs;
				verbose && console.log("axios.get url: ", url);
				results = await axios.get(url);
			} else {
				verbose && console.log("axios.post url: ", url, 'data', data);
				results = await axios.post(url, data);
			}
		}
		return returnDataOnly ? results.data : results;
	} catch (error) {
		console.log(error.toJSON());
	}
}

export function pathToArray(path) {
	if (isEmpty(path)) {
		return [];
	}
	if (Array.isArray(path)) {
		return path;
	}
	if (typeof (path) === 'string') {
		return path.split('.');
	}
	throw new Error(`pathToArray expects either array of keys or period-delimited string of keys, not ${path}`);
}

export function prefetch(props) {
	const {itemType, codeset_ids} = props;
	switch (itemType) {
		case 'all_csets':
			fetchItems(itemType);
			break;
		default:
			throw new Error(`Don't know how to prefetch ${itemType}`);
	}
}