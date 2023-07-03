import {LRUCache} from 'lru-cache'; // https://isaacs.github.io/node-lru-cache
import {debounce, get, isEmpty, set, uniq} from 'lodash';
import {axiosCall, backend_url, fetchItems, pathToArray} from './State';
import {compress, decompress} from "lz-string";


class DataCache {
	#cache = {};

	async getItemsByKey({
												itemType,
												keyName,
												keys = [],
												shape = 'array', /* or obj */
												createFunc,
												returnFunc
											}) {
		if (isEmpty(keys)) {
			return shape === 'array' ? [] : {};
		}
		keys = keys.map(String);
		if (keys.length !== uniq(keys).length) {
			throw new Error(`Why are you sending duplicate keys?`);
		}
		// use this for concepts and cset_members_items
		let wholeCache = get(this.#cache, itemType, {});
		let cachedItems = {};     // this will hold the requested items that are already cached
		let uncachedKeys = []; // requested items that still need to be fetched
		let uncachedItems = {};   // this will hold the newly fetched items

		keys.forEach(key => {
			if (wholeCache[key]) {
				cachedItems[key] = wholeCache[key];
			} else {
				uncachedKeys.push(key);
			}
		})
		if (uncachedKeys.length) {
			const data = await fetchItems(
					itemType,
					uncachedKeys,
			);
			data.forEach((item, i) => uncachedItems[uncachedKeys[i]] = item);
		}
		const results = {...cachedItems, ...uncachedItems};
		const not_found = uncachedKeys.filter(key => !(key in results));
		if (not_found.length) {
			// TODO: let user see warning somehow
			console.warn(`Warning in DataCache.getItemsByKey: failed to fetch ${itemType}s for ${not_found.join(', ')}`);
		}
		if (returnFunc) {
			return returnFunc(results);
		}
		if (shape === 'array') {
			return Object.values(results);
		}
		return results;
	}

	constructor() {
		this.#cache = this.loadCache() ?? {};
	}

	getWholeCache() {
		return this.#cache;
	}

	getKeys() {
		return Object.keys(this.getWholeCache());
	}

	saveCache = debounce(async () => {
		const before = (localStorage.getItem('dataCache') || '').length;
		const compressed = compress(JSON.stringify(this.#cache));
		const after = compressed.length;
		if (before === after) { // assume compressed cache after change will be different length
			return null;
		}
		// rounding suggestion: https://stackoverflow.com/a/11832950/1368860
		console.log(`compressed cache just grew by ${Math.round(
				10000 * (after / before + Number.EPSILON)) / 100}% to ${after.toLocaleString()} chars`)

		localStorage.setItem('dataCache', compressed);
		return null;
	}, 400);
	loadCache = () => {
		try {
			return JSON.parse(decompress(localStorage.getItem('dataCache') || ''));
		} catch (error) {
			return {};
		}
	}

	cacheGet(path) {
		// uses lodash get, so path can be array of nested keys or a string with
		//  keys delimited by .
		// so dataCache.cacheGet('concept')
		//  gets an obj of all the concepts keyed by concept_id
		// dataCache.cacheGet('concept.12345') or
		// dataCache.cacheGet(['concept', '12345'])
		//  gets the concept with concept_id 12345
		path = pathToArray(path);
		return isEmpty(path) ? this.getWholeCache() : get(this.#cache, path);
	}

	cachePut(path, value, storeAsArray = false) {
		let [parentPath, parentObj,] = this.popLastPathKey(path);
		if (isEmpty(parentObj)) {
			if (storeAsArray) {
				set(this.#cache, parentPath, [])
			} else {
				// have to do this or numeric keys will force new obj to be an array
				set(this.#cache, parentPath, {})
			}
		}
		set(this.#cache, path, value);
		this.saveCache();
	}

	popLastPathKey(path) {
		path = [...pathToArray(path)];
		const lastKey = path.pop();
		return [path, this.cacheGet(path), lastKey];
	}

	cacheDelete(path) {
		let [, parentObj, lastKey] = this.popLastPathKey(path);
		delete parentObj[lastKey];
	}

	emptyCache() {
		this.#cache = {};
	}

	async cacheCheck() {
		const url = 'last-refreshed';
		const tsStr = await axiosCall(url, {backend: true, verbose: false,});
		const ts = new Date(tsStr);
		if (isNaN(ts.getDate())) {
			throw new Error(`invalid date from ${url}: ${tsStr}`);
		}
		const lrStr = this.lastRefreshed();
		const lr = new Date(lrStr);
		if (isNaN(lr.getDate()) || ts > lr) {
			console.log(`previous DB refresh: ${lrStr}; latest DB refresh: ${ts}. Clearing localStorage.`);
			localStorage.clear();
			return this.#cache.lastRefreshTimestamp = ts;
		} else {
			console.log(`no change since last refresh at ${lr}`);
			return lr;
		}
	}

	lastRefreshed() {
		const lr = get(this.#cache, 'lastRefreshTimestamp');
		return lr;
	}
}
export const dataCache = new DataCache();
window.addEventListener("beforeunload", dataCache.saveCache);
window.dataCacheW = dataCache; // for debugging


class DataAccessWithLRU {
	constructor() {
		this.cache = new LRUCache({
																max: 100, // number of items to keep
																maxAge: 1000 * 60 * 60, // 1 hour
															});
	}
	/*
	saveCache() {
		const data = JSON.stringify(this.cache.dump());
		localStorage.setItem('data-access-cache', data);
	}

	loadCache() {
		const data = localStorage.getItem('data-access-cache');
		if (data) {
			this.cache.load(JSON.parse(data));
		}
	}

	clearCache() {
		this.cache.reset();
		localStorage.removeItem('data-access-cache');
	}

	store_concepts_to_cache(concepts) {
		concepts.forEach(concept => {
			this.cache.set(`concepts.${concept.concept_id}`, concept);
		});
	}

	async getConcepts(concept_ids=[], shape="array") {
		let all_cached_concepts = this.cache.get('concepts');
		let cached_concepts = {};
		let uncachedConceptIds = [];
		let uncachedConcepts = {};
		concept_ids.forEach(concept_id => {
													if (all_cached_concepts && all_cached_concepts[concept_id]) {
														cached_concepts[concept_id] = all_cached_concepts[concept_id];
													} else {
														uncachedConceptIds.push(concept_id);
													}
												}
		);
		if (uncachedConceptIds.length) {
			const url = backend_url(
					"get-concepts?" + uncachedConceptIds.map(c=>`id=${c}`).join("&")
			);
		}
		const data = await fetch('concepts', url);
		data.forEach(concept => {
			uncachedConcepts[concept.concept_id] = concept;
		});
		const results = {...cached_concepts, ...uncachedConcepts};
		const not_found = concept_ids.filter(
				x => !Object.values(results).map(c=>c.concept_id).includes(x));
		if (not_found.length) {
			window.alert("Warning in dataAccess.getConcepts: couldn't find concepts for " +
											 not_found.join(', '))
		}
		if (shape === 'array') {
			return Object.values(results);
		}
		return results;
	}

	async getSubgraphEdges(concept_ids=[], format='array') {
		if (!concept_ids.length) {
			return [];
		}
		const url = backend_url(
				"subgraph?" + concept_ids.map(c=>`cid=${c}`).join("&")
		);
		const data = await fetch('subgraph', url);
		return data;
	}

	async fetch(type, url) {
		const response = await axiosCall(url);
		const data = get(response, 'data', []);
		if (type === 'concepts') {
			this.store_concepts_to_cache(data);
		}
		return data;
	}
	 */
}
