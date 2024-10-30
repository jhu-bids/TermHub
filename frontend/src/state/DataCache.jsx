import {createContext, useContext, useEffect, useState, useRef, } from "react";
import {LRUCache} from 'lru-cache'; // https://isaacs.github.io/node-lru-cache
import {debounce, get, isEmpty, setWith, } from 'lodash';
import {compress, decompress} from "lz-string";
import {useCids, useCodesetIds} from './AppState';

const STOP_CACHING = 50 * 10**6;
const START_EMPTYING_CACHE = 20 * 10**6;
const OPTIMIZATION_EXPERIMENT = ''; // 'no_cache';

/*
    TODO: get LRU cache working, one cache for each itemType, probably
    // running out of space at around 18,000,000 compressed characters;
 */

const DataCacheContext = createContext(null);

export function DataCacheProvider({children}) {
  const [codeset_ids] = useCodesetIds();
  const [cids] = useCids();
  const dataCacheRef = useRef(null);
  const [isInitialized, setIsInitialized] = useState(false);

  // Initialize the DataCache instance once
  useEffect(() => {
    if (!dataCacheRef.current) {
      const initialSelectState = codeset_ids.join(',') + ';' + cids.join(',');
      dataCacheRef.current = new DataCache({
        optimization_experiment: OPTIMIZATION_EXPERIMENT,
        selectState: initialSelectState
      });

      // Only add event listener if window is defined
      if (typeof window !== 'undefined') {
        window.addEventListener("beforeunload", dataCacheRef.current.saveCache);
        window.dataCacheW = dataCacheRef.current; // for debugging
      }

      setIsInitialized(true);
    }
  }, []); // Empty dependency array ensures this runs once

  // Update the cache when dependencies change
  useEffect(() => {
    if (dataCacheRef.current) {
      const newSelectState = codeset_ids.join(',') + ';' + cids.join(',');
      dataCacheRef.current.setSelectState(newSelectState);
    }
  }, [codeset_ids, cids]);

  // Cleanup event listener
  useEffect(() => {
    return () => {
      if (typeof window !== 'undefined' && dataCacheRef.current) {
        window.removeEventListener("beforeunload", dataCacheRef.current.saveCache);
      }
    };
  }, []);

  if (!isInitialized) {
    return null; // or a loading indicator if preferred
  }

  return (
    <DataCacheContext.Provider value={dataCacheRef.current}>
      {children}
    </DataCacheContext.Provider>
  );
}

export function useDataCache() {
  return useContext(DataCacheContext);
}

class DataCache {
  #cache = {};
  cacheTooBig = false;

  constructor(opts) {
    this.optimization_experiment = opts.optimization_experiment;
    this.selectState = opts.selectState;  // will be codeset_ids;cids
    this.loadCache();
  }

  setSelectState(selectState) {
    this.selectState = selectState;
  }

  getWholeCache() {
    return this.#cache;
  }

  getKeys() {
    return Object.keys(this.getWholeCache());
  }
  getCacheForKey(key) {
    return this.getWholeCache()[key];
  }

  saveCache = debounce(async () => {
    if (this.cacheTooBig) {
      return;
    }
    const uncompressed = JSON.stringify(this.#cache);
    if (uncompressed.length > 40 * 10**6) {
      // on my (sg) computer right now (2024-08-28) 60 million uncompressed
      //  is too big for the cache. so let's quit caching when we get to
      //  this point
      this.cacheTooBig = true;
      console.warn(`uncompressed cache size ${uncompressed.length.toLocaleString()}; giving up on caching`);
    }
    if (this.cacheTooBig) {
      return;
    }
    const startTime = performance.now();
    const duration = performance.now() - startTime;
    const before = (localStorage.getItem('dataCache') || '').length;
    this.addCacheHistoryEvent(`saving cache`);
    // TODO: use history to check if changed size *before* compressing
    const compressed = compress(uncompressed);
    const after = compressed.length;
    if (before === after) { // assume compressed cache after change will be different length
      return null;
    }
    // rounding suggestion: https://stackoverflow.com/a/11832950/1368860
    let pctIncr = Math.round(10000 * (after / before + Number.EPSILON)) / 100;
    let evtMsg = `saved cache: ${uncompressed.length.toLocaleString()} uncompressed, ${compressed.length.toLocaleString()} compressed, ${pctIncr}% incr`;
    this.addCacheHistoryEvent(evtMsg);

    try {
      this.setLocalStorageItem('dataCache', compressed);
    } catch(err) {
      alert("Can't save cache! (This shouldn't happen anymore. Tell Siggie.)");
      throw err;
    }
    try {
      localStorage.setItem('dataCache', compressed);
    } catch(err) {
  // TODO: probably fix alert message?
      alert("Can't save cache! (This shouldn't happen anymore. Tell Siggie.)");
      throw err;
    }
    // console.log(`saveCache took ${duration}ms`);
  }, 400);

    // Add these methods to make it easier to mock localStorage
  setLocalStorageItem(key, value) {
    localStorage.setItem(key, value);
  }

  getLocalStorageItem(key) {
    return localStorage.getItem(key);
  }

  addCacheHistoryEvent(evtMsg) {
    let evt = {
      ts: new Date(),
      evtMsg,
    };
    let cacheHistory = this.cacheGet('cacheHistory');
    if (!cacheHistory) {
      throw new Error('expected to find cacheHistory');
    }
    cacheHistory.push(evt);
    this.cachePut('cacheHistory', cacheHistory, false);
    // console.log(cacheHistory);
  }
  cacheAge() {
    if (this.#cache.cacheHistory.length > 0) {
      const cacheStart = new Date(this.#cache.cacheHistory[0].ts);
      const today = new Date();
      const daysOld = (today - cacheStart) / (1000*60*60*24);
      return daysOld;
    }
  }
  loadCache = () => {
    const startTime = performance.now();
    let cache;
    let evtMsg;
    try {
      let compressedCache = localStorage.getItem('dataCache');
      let decompressed = decompress(compressedCache);
      this.#cache = JSON.parse(decompressed);
      if (this.cacheAge() > 1) {
        this.emptyCache();
      }
      evtMsg = `loaded cache: ${compressedCache.length.toLocaleString()} compressed, ${decompressed.length.toLocaleString()} decompressed`;
      this.addCacheHistoryEvent(evtMsg);
    } catch (error) {
      evtMsg = 'new cache';
      this.#cache = {cacheHistory: []};
      this.addCacheHistoryEvent(evtMsg);
    }
    const duration = performance.now() - startTime;
    // console.log(`loadCache took ${duration}ms`);
  }
  async cacheCheck(dataGetter) {
    const url = 'last-refreshed';
    const dbRefreshTimestampStr = await dataGetter.axiosCall(url, {backend: true, verbose: false, sendAlert: false});
    const dbRefreshTimestamp = new Date(dbRefreshTimestampStr);
    if (isNaN(dbRefreshTimestamp.getDate())) {
      throw new Error(`invalid date from ${url}: ${dbRefreshTimestampStr}`);
    }
    const cacheRefreshTimestampStr = this.lastRefreshed();
    const cacheRefreshTimestamp = new Date(cacheRefreshTimestampStr);
    if (isNaN(cacheRefreshTimestamp.getDate()) || dbRefreshTimestamp > cacheRefreshTimestamp) {
      console.log(`previous DB refresh: ${cacheRefreshTimestampStr}; latest DB refresh: ${dbRefreshTimestamp}. Clearing localStorage.`);
      this.emptyCache();
      this.cachePut('lastRefreshTimestamp', dbRefreshTimestamp);
      await this.saveCache();
      const cacheRefreshTimestamp = this.lastRefreshed();
      // return this.#cache.lastRefreshTimestamp = dbRefreshTimestamp;
    } else {
      console.log(`no change since last refresh at ${cacheRefreshTimestamp}`);
      // return cacheRefreshTimestamp;
    }
  }

  lastRefreshed() {
    const cacheRefreshTimestamp = this.cacheGet('lastRefreshTimestamp');
    return typeof(cacheRefreshTimestamp) === 'string' ? new Date(cacheRefreshTimestamp) : cacheRefreshTimestamp;
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

  cachePut(path, value, save=true) {
    if (this.optimization_experiment === 'no_cache') {
      return;
    }

    // setWith(..., Object) in order to create objects instead of arrays even with numeric keys
    setWith(this.#cache, path, value, Object);
    if (save) {
      // this.addCacheHistoryEvent()
      this.saveCache();
    }
  }
  // cacheArrayPut(path, value, storeAsArray = false, appendToArray = false) {
  //   if (storeAsArray && appendToArray) {
  //     let val = get(this.#cache, path);
  //   }
  // }

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
    // this.#cache = {};
    localStorage.clear();
    this.cacheTooBig = false;
    this.loadCache();
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
