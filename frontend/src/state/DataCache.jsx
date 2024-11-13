import { createContext, useContext, useEffect, useState, useRef } from "react";
import {useCids, useCodesetIds} from './AppState';
import { LRUCache } from 'lru-cache'; // https://isaacs.github.io/node-lru-cache
// import { debounce, get, isEmpty, setWith } from 'lodash';
import {fromPairs, map} from 'lodash';
import { compress, decompress } from "lz-string";

const CACHE_CONFIG = {
  MAX_STORAGE_SIZE: 4 * 10**6,
  WARN_STORAGE_SIZE: 3.5 * 10**6,
  DEFAULT_TTL: 24 * 60 * 60 * 1000, // 24 hours in milliseconds
  OPTIMIZATION_EXPERIMENT: '', // 'no-cache',
};
// Use a key that won't conflict with our encoded keys
const MAPPER_STORAGE_KEY = 'mapper_state';
const CACHE_PREFIX = '_';


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
        optimization_experiment: CACHE_CONFIG.OPTIMIZATION_EXPERIMENT,
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
  /* useEffect(() => {
    if (dataCacheRef.current) {
      const newSelectState = codeset_ids.join(',') + ';' + cids.join(',');
      dataCacheRef.current.setSelectState(newSelectState);
    }
  }, [codeset_ids, cids]); */

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
  constructor(opts) {
    this.selectState = opts.selectState;
    this.lruCaches = new Map(); // Create separate LRU caches for each slice
    this.memoryCache = new Map(); // Main memory cache for frequently accessed data
    this.sizeTracker = new Map(); // Keep track of compressed sizes
    this.accessTimes = new Map();
    this.writeTimes = new Map();
    this.initializeCache();
  }

  initializeCache() {
    try {
      // Load existing keys and their metadata from localStorage
      for (let i = 0; i < localStorage.length; i++) {
        const key = localStorage.key(i);
        if (key.startsWith(CACHE_PREFIX)) { // Using your encoded slice prefix
          const compressed = localStorage.getItem(key);
          const size = compressed.length;
          this.sizeTracker.set(key, size);

          // Try to load metadata
          try {
            const meta = localStorage.getItem(`${key}:meta`);
            if (meta) {
              const { writeTime, accessTime } = JSON.parse(meta);
              if (writeTime) this.writeTimes.set(key, writeTime);
              if (accessTime) this.accessTimes.set(key, accessTime);
            }
          } catch (error) {
            console.error(`Failed to load metadata for ${key}:`, error);
          }
        }
      }
    } catch (error) {
      console.error('Failed to initialize cache:', error);
    }
  }

  cacheGet(path) {
    const {slice, sliceCode, key} = this.pathToKey(path);
    return this.cacheGetSliceKey(slice, key);
  }

  cacheGetSliceKey(slice, key) {
    const now = Date.now();
    let value;

    // Try memory cache first
    if (this.memoryCache.has(key)) {
      value = this.memoryCache.get(key);
    } else {
      // Try LRU cache next
      const lruCache = this.getLRUCache(slice);
      value = lruCache.get(key);

      if (value === undefined) {
        // Finally, try localStorage
        try {
          const compressed = localStorage.getItem(key);
          if (compressed) {
            value = JSON.parse(decompress(compressed));

            // Store in memory cache if it's small enough
            if (compressed.length < 1000) {
              this.memoryCache.set(key, value);
            }

            // Store in LRU cache
            lruCache.set(key, value);
          }
        } catch (error) {
          console.error(`Failed to retrieve cached value for ${key}:`, error);
        }
      }
    }

    // Update access time if we found a value
    if (value !== undefined) {
      this.accessTimes.set(key, now);
      // Update metadata in localStorage
      this.updateMetadata(key);
    }

    return value;
  }


  async cachePut(path, value, options = {}) {
    const {slice, sliceCode, key} = this.pathToKey(path);
    const now = Date.now();

    try {
      // Compress the value
      const serialized = JSON.stringify(value);
      const compressed = compress(serialized);
      const size = compressed.length;

      // Calculate total size including new item
      const totalSize = Array.from(this.sizeTracker.values()).reduce((a, b) => a + b, 0) + size;

      // If the new item is very large (>500KB), be more aggressive with pruning
      const isLargeItem = size > 500 * 1024; // 500KB threshold
      const targetThreshold = isLargeItem ?
        CACHE_CONFIG.WARN_STORAGE_SIZE * 0.5 : // 50% for large items
        CACHE_CONFIG.WARN_STORAGE_SIZE * 0.8;  // 80% for normal items

      // Always try to prune before adding new items
      await this.proactivePrune(size, targetThreshold);

      try {
        // Attempt to store the item
        localStorage.setItem(key, compressed);
      } catch (error) {
        if (error.name === 'QuotaExceededError') {
          // For quota errors, do increasingly aggressive pruning
          const pruneTargets = [0.5, 0.3, 0.2].map(factor =>
            CACHE_CONFIG.WARN_STORAGE_SIZE * factor
          );

          for (const targetSize of pruneTargets) {
            try {
              await this.emergencyPrune(size, targetSize);
              localStorage.setItem(key, compressed);
              break; // If successful, exit the loop
            } catch (retryError) {
              if (retryError.name !== 'QuotaExceededError') throw retryError;
              // If it's still a quota error, continue to next iteration
              if (targetSize === pruneTargets[pruneTargets.length - 1]) {
                // If we've tried all targets and still failing, give up
                console.error('Failed to store item even after aggressive pruning');
                return false;
              }
            }
          }
        } else {
          throw error;
        }
      }

      // Update tracking maps
      this.sizeTracker.set(key, size);
      this.writeTimes.set(key, now);
      this.accessTimes.set(key, now);
      this.updateMetadata(key);

      // Update memory cache if small enough
      if (size < 1000) {
        this.memoryCache.set(key, value);
      }

      // Update LRU cache
      const lruCache = this.getLRUCache(slice);
      lruCache.set(key, value);

      return true;
    } catch (error) {
      console.error(`Failed to cache value for ${key}:`, error);
      return false;
    }
  }

  async proactivePrune(incomingSize, targetSize) {
    const currentTotal = Array.from(this.sizeTracker.values()).reduce((a, b) => a + b, 0);

    if (currentTotal > targetSize) {
      await this.pruneToSize(targetSize - incomingSize);
    }
  }

  async emergencyPrune(incomingSize, targetSize) {
    await this.pruneToSize(targetSize - incomingSize);

    // Clear memory cache entirely in emergency situations
    this.memoryCache.clear();

    // Clear all LRU caches
    for (const cache of this.lruCaches.values()) {
      cache.clear();
    }
  }

  async pruneToSize(targetSize) {
    // Get all items across all slices
    const allItems = [];
    const now = Date.now();
    const CURRENT_ACTION_THRESHOLD = 60 * 1000; // 1 minute

    for (const [key, size] of this.sizeTracker.entries()) {
      const accessTime = this.accessTimes.get(key) || 0;
      const writeTime = this.writeTimes.get(key) || 0;
      const [sliceCode] = key.split(':');
      const slice = mapper.decode(sliceCode);

      // Calculate item score (higher score = more likely to keep)
      const isCurrent = (now - writeTime) <= CURRENT_ACTION_THRESHOLD;
      const ageScore = (now - accessTime) / (24 * 60 * 60 * 1000); // Age in days
      const sizeScore = size / (100 * 1024); // Size penalty (100KB units)

      // Special handling for different slices
      const slicePriority = slice === 'concepts' ? 0.5 : 1; // Lower priority for concepts

      const score = (isCurrent ? 1000 : 0) + // High bonus for current items
                   (10 / (ageScore + 1)) * slicePriority - // Age factor
                   sizeScore; // Size penalty

      allItems.push({ key, size, score, slice });
    }

    // Sort by score (lower scores removed first)
    allItems.sort((a, b) => a.score - b.score);

    let currentSize = Array.from(this.sizeTracker.values()).reduce((a, b) => a + b, 0);
    let itemsRemoved = 0;

    // Remove items until we're under target size
    for (const item of allItems) {
      if (currentSize <= targetSize) break;

      // Remove from all caches
      localStorage.removeItem(item.key);
      localStorage.removeItem(`${item.key}:meta`);
      this.memoryCache.delete(item.key);
      this.sizeTracker.delete(item.key);
      this.accessTimes.delete(item.key);
      this.writeTimes.delete(item.key);

      // Clear from LRU cache
      const lruCache = this.getLRUCache(item.slice);
      lruCache.delete(item.key);

      currentSize -= item.size;
      itemsRemoved++;
    }

    console.log(`Pruned ${itemsRemoved} items, new size: ${(currentSize / 1024 / 1024).toFixed(2)}MB`);
  }

  updateMetadata(key) {
    const meta = {
      writeTime: this.writeTimes.get(key),
      accessTime: this.accessTimes.get(key)
    };
    localStorage.setItem(`${key}:meta`, JSON.stringify(meta));
  }

  delete(path) {
    const {slice, sliceCode, key} = this.pathToKey(path);

    // Clear from all caches and tracking
    this.memoryCache.delete(key);
    this.getLRUCache(slice).delete(key);
    localStorage.removeItem(key);
    localStorage.removeItem(`${key}:meta`);
    this.sizeTracker.delete(key);
    this.accessTimes.delete(key);
    this.writeTimes.delete(key);
  }

  clear() {
    this.memoryCache.clear();
    this.lruCaches.clear();
    this.sizeTracker.clear();
    this.accessTimes.clear();
    this.writeTimes.clear();

    // Clear cache items from localStorage
    for (let i = localStorage.length - 1; i >= 0; i--) {
      const key = localStorage.key(i);
      if (key && key.startsWith(CACHE_PREFIX)) { // Using your encoded slice prefix
        localStorage.removeItem(key);
        localStorage.removeItem(`${key}:meta`);
      }
    }
  }

  // setSelectState(selectState) { this.selectState = selectState; }


  // Get or create an LRU cache for a specific data type
  getLRUCache(slice, options = {}) {
    if (!this.lruCaches.has(slice)) {
      this.lruCaches.set(slice, new LRUCache({
        max: options.max || 1000,
        ttl: options.ttl || CACHE_CONFIG.DEFAULT_TTL,
        updateAgeOnGet: true
      }));
    }
    return this.lruCaches.get(slice);
  }

  // Convert path to storage key, return slice (first bit) and whole key
  pathToKey(path) {
    if (!Array.isArray(path)) {
      throw new Error("cache path should always be given as array");
    }
    let [slice, ...keys] = path;
    let sliceCode = mapper.encode(slice);
    let key = [sliceCode, ...keys].join(':');
    return {slice, sliceCode, key};
  }

  getWholeSlice(slice) {
    const sliceCode = mapper.encode(slice);
    const keys = this.getSliceKeys(sliceCode);
    return fromPairs(map(keys, key => [key.replace(`${sliceCode}:`,''), this.cacheGetSliceKey(slice, key)]));
  }

  getSliceKeys(sliceCode) {
    return Object.keys(localStorage)
      .filter(key => key.startsWith(sliceCode) && !key.match(':meta'));
  }

  getSlices() {
    return mapper.strings;
  }

  // Add this method to the DataCache class
  getStats() {
    const stats = {
      totalSize: 0,
      slices: {},
      summary: {
        totalItems: 0,
        sizeMB: 0,
        currentAction: { items: 0, sizeMB: 0 },
        previousActions: { items: 0, sizeMB: 0 },
        largestItems: []
      }
    };

    // First find the most recent timestamp to identify current action
    let mostRecentTime = 0;
    for (let i = 0; i < localStorage.length; i++) {
      const key = localStorage.key(i);
      // Skip non-cache keys and mapper state
      if (!key || !key.startsWith(CACHE_PREFIX) || key === MAPPER_STORAGE_KEY) continue;
      const writeTime = this.writeTimes.get(key) || 0;
      mostRecentTime = Math.max(mostRecentTime, writeTime);
    }

    const CURRENT_ACTION_THRESHOLD = 60 * 1000; // 1 minute
    const allItems = []; // collect all items for sorting by size

    // Collect stats
    for (let i = 0; i < localStorage.length; i++) {
      const key = localStorage.key(i);
      // Skip non-cache keys and mapper state
      if (!key || !key.startsWith(CACHE_PREFIX) || key === MAPPER_STORAGE_KEY) continue;

      const size = this.sizeTracker.get(key) || 0;
      const writeTime = this.writeTimes.get(key) || 0;
      const value = localStorage.getItem(key);

      if (!value) continue;

      // Extract slice from key
      const [sliceCode, ...rest] = key.split(':');
      let slice;
      try {
        slice = mapper.decode(sliceCode);
      } catch (e) {
        console.warn(`Invalid slice code ${sliceCode} for key ${key}`);
        continue;
      }

      // Track item for size sorting
      allItems.push({ key, size, slice, writeTime });

      // Initialize slice stats if needed
      if (!stats.slices[slice]) {
        stats.slices[slice] = {
          totalSize: 0,
          itemCount: 0,
          currentAction: { items: 0, sizeMB: 0 },
          previousActions: { items: 0, sizeMB: 0 },
          largestItems: []
        };
      }

      const isCurrentAction = (mostRecentTime - writeTime) <= CURRENT_ACTION_THRESHOLD;

      // Update slice stats
      const sliceStats = stats.slices[slice];
      sliceStats.totalSize += size;
      sliceStats.itemCount++;

      if (isCurrentAction) {
        sliceStats.currentAction.items++;
        sliceStats.currentAction.sizeMB += size;
        stats.summary.currentAction.items++;
        stats.summary.currentAction.sizeMB += size;
      } else {
        sliceStats.previousActions.items++;
        sliceStats.previousActions.sizeMB += size;
        stats.summary.previousActions.items++;
        stats.summary.previousActions.sizeMB += size;
      }

      stats.totalSize += size;
      stats.summary.totalItems++;
    }

    // Sort all items by size and get top 5 largest
    allItems.sort((a, b) => b.size - a.size);
    stats.summary.largestItems = allItems.slice(0, 5).map(item => ({
      key: item.key,
      slice: item.slice,
      sizeMB: (item.size / (1024 * 1024)).toFixed(2),
      isCurrentAction: (mostRecentTime - item.writeTime) <= CURRENT_ACTION_THRESHOLD
    }));

    // Get per-slice largest items
    for (const slice in stats.slices) {
      const sliceItems = allItems.filter(item => item.slice === slice);
      stats.slices[slice].largestItems = sliceItems.slice(0, 5).map(item => ({
        key: item.key,
        sizeMB: (item.size / (1024 * 1024)).toFixed(2),
        isCurrentAction: (mostRecentTime - item.writeTime) <= CURRENT_ACTION_THRESHOLD
      }));
    }

    // Convert accumulated sizes to MB
    stats.summary.sizeMB = (stats.totalSize / (1024 * 1024)).toFixed(2);
    stats.summary.currentAction.sizeMB = (stats.summary.currentAction.sizeMB / (1024 * 1024)).toFixed(2);
    stats.summary.previousActions.sizeMB = (stats.summary.previousActions.sizeMB / (1024 * 1024)).toFixed(2);

    for (const slice in stats.slices) {
      const sliceStats = stats.slices[slice];
      sliceStats.sizeMB = (sliceStats.totalSize / (1024 * 1024)).toFixed(2);
      sliceStats.currentAction.sizeMB = (sliceStats.currentAction.sizeMB / (1024 * 1024)).toFixed(2);
      sliceStats.previousActions.sizeMB = (sliceStats.previousActions.sizeMB / (1024 * 1024)).toFixed(2);
    }

    return stats;
  }
}

const createStringMapper = () => {
  // trying strategy of not caching individual small items, so don't
  //  need to abbreviate slice keys anymore. if this strategy works,
  //  can get rid of all this mapper stuff

  // oh, except relying on cache keys to start with underscore

  const encode = (str) => CACHE_PREFIX + str;
  const decode = (str) => {
    if (str[0] !== '_') {
      throw new Error(`expected slice code to start with underscore, got ${str}`);
    }
    return str.slice(1);
  }


  let stringToNum = new Map();
  let numToString = [];

  // Try to load existing mappings from localStorage
  try {
    const savedMapper = localStorage.getItem(MAPPER_STORAGE_KEY);
    if (savedMapper) {
      const { strings } = JSON.parse(savedMapper);
      numToString = strings;
      stringToNum = new Map(strings.map((str, i) => [str, i + 1]));
    }
  } catch (error) {
    console.error('Failed to load string mapper:', error);
  }

  const saveMapper = () => {
    try {
      localStorage.setItem(MAPPER_STORAGE_KEY, JSON.stringify({
        strings: numToString
      }));
    } catch (error) {
      console.error('Failed to save string mapper:', error);
    }
  };

  const encodeOLD = (str) => {
    if (stringToNum.has(str)) {
      return `_${stringToNum.get(str)}`;
    }

    const num = numToString.length + 1;
    stringToNum.set(str, num);
    numToString.push(str);
    saveMapper(); // Save whenever we add a new mapping
    return `_${num}`;
  };

  const decodeOLD = (encoded) => {
    if (!encoded.startsWith(CACHE_PREFIX)) {
      throw new Error('Invalid encoded string: must start with underscore');
    }

    const num = parseInt(encoded.slice(1));
    // Convert to 0-based index for array access
    const index = num - 1;
    if (isNaN(num) || index < 0 || index >= numToString.length) {
      throw new Error(`Invalid encoded string: ${encoded}`);
    }
    return numToString[index];
  };

  return {
    encode,
    decode,
    strings: [...numToString],
    debug: () => ({
      numToString,
      stringToNumEntries: Array.from(stringToNum.entries())
    })
  };
};

const mapper = createStringMapper();