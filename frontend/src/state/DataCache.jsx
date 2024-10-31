import { LRUCache } from 'lru-cache';
import { compress, decompress } from "lz-string";
import { isEmpty } from 'lodash';
import {createContext, useContext, useEffect, useRef, useState} from 'react';
import {useCids, useCodesetIds} from './AppState';

const CACHE_CONFIG = {
  MAX_STORAGE_SIZE: 50 * 10**6,
  WARN_STORAGE_SIZE: 20 * 10**6,
  DEFAULT_TTL: 24 * 60 * 60 * 1000,
};

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
      /* dataCacheRef.current = new DataCache({
        optimization_experiment: OPTIMIZATION_EXPERIMENT,
        selectState: initialSelectState
      }); */

      dataCacheRef.current = new MonitoredCache();

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

class CacheStats {
  constructor() {
    this.reset();
  }

  reset() {
    this.operations = {
      get: { count: 0, timeTotal: 0, hits: 0, misses: 0, sizes: [] },
      put: { count: 0, timeTotal: 0, sizes: [] },
      compress: { count: 0, timeTotal: 0, ratios: [] },
      decompress: { count: 0, timeTotal: 0 }
    };

    // Track by API endpoint and cache slice
    this.byEndpoint = new Map();
    this.bySlice = new Map();
  }

  trackOperation(opType, details) {
    const { slice, endpoint, size, time, hit } = details;
    const startTime = performance.now();

    // Update general stats
    const opStats = this.operations[opType];
    opStats.count++;
    opStats.timeTotal += time;
    if (size) opStats.sizes.push(size);

    if (opType === 'get') {
      if (hit) opStats.hits++;
      else opStats.misses++;
    }

    // Track by endpoint
    if (endpoint) {
      if (!this.byEndpoint.has(endpoint)) {
        this.byEndpoint.set(endpoint, {
          gets: { count: 0, hits: 0, misses: 0 },
          puts: { count: 0 },
          totalSize: 0,
          avgTime: 0,
          totalTime: 0
        });
      }

      const endpointStats = this.byEndpoint.get(endpoint);
      endpointStats.totalTime += time;
      endpointStats.avgTime = endpointStats.totalTime / (endpointStats.gets.count + endpointStats.puts.count);

      if (opType === 'get') {
        endpointStats.gets.count++;
        if (hit) endpointStats.gets.hits++;
        else endpointStats.gets.misses++;
      } else if (opType === 'put') {
        endpointStats.puts.count++;
        if (size) endpointStats.totalSize += size;
      }
    }

    // Track by cache slice
    if (slice) {
      if (!this.bySlice.has(slice)) {
        this.bySlice.set(slice, {
          itemCount: 0,
          totalSize: 0,
          gets: { count: 0, hits: 0, misses: 0 },
          puts: { count: 0 }
        });
      }

      const sliceStats = this.bySlice.get(slice);
      if (opType === 'get') {
        sliceStats.gets.count++;
        if (hit) sliceStats.gets.hits++;
        else sliceStats.gets.misses++;
      } else if (opType === 'put') {
        sliceStats.puts.count++;
        if (size) {
          sliceStats.totalSize += size;
          sliceStats.itemCount++;
        }
      }
    }
  }

  getReport() {
    const report = {
      operations: {},
      byEndpoint: {},
      bySlice: {},
      summary: {
        totalSize: 0,
        hitRate: 0,
        mostAccessedEndpoints: [],
        largestSlices: []
      }
    };

    // Process operations stats
    for (const [opType, stats] of Object.entries(this.operations)) {
      report.operations[opType] = {
        count: stats.count,
        avgTime: stats.count ? stats.timeTotal / stats.count : 0,
        totalTime: stats.timeTotal
      };

      if (opType === 'get') {
        report.operations[opType].hitRate = stats.count ? stats.hits / stats.count : 0;
      }
    }

    // Process endpoint stats
    for (const [endpoint, stats] of this.byEndpoint.entries()) {
      report.byEndpoint[endpoint] = {
        hitRate: stats.gets.count ? stats.gets.hits / stats.gets.count : 0,
        avgTime: stats.avgTime,
        totalSize: stats.totalSize,
        gets: stats.gets,
        puts: stats.puts
      };
    }

    // Process slice stats
    for (const [slice, stats] of this.bySlice.entries()) {
      report.bySlice[slice] = {
        itemCount: stats.itemCount,
        totalSize: stats.totalSize,
        hitRate: stats.gets.count ? stats.gets.hits / stats.gets.count : 0
      };
      report.summary.totalSize += stats.totalSize;
    }

    return report;
  }
}

class MonitoredCache {
  constructor() {
    this.storage = new Map();
    this.stats = new CacheStats();
    this.loadFromStorage();
  }

    constructor() {
    this.storage = new Map();
    this.stats = new CacheStats();

    // Configure which slices should be stored as collections
    this.collectionSlices = new Set([
      'codeset_ids_by_concept_id',
      'concept_ids_by_codeset_id',
      'concepts',
      'cset_members_items'
    ]);

    this.loadFromStorage();
  }

  isCollectionSlice(path) {
    const slice = Array.isArray(path) ? path[0] : path.split(':')[0];
    return this.collectionSlices.has(slice);
  }

  async cacheGet(path) {
    const startTime = performance.now();
    const key = Array.isArray(path) ? path.join(':') : path;
    const slice = Array.isArray(path) ? path[0] : path.split(':')[0];

    let value;
    let hit = false;

    if (this.isCollectionSlice(path)) {
      // For collection slices, get the whole collection and extract the needed item
      const collectionKey = `cache:${slice}`;
      try {
        // Try memory first
        let collection = this.storage.get(slice);

        if (!collection) {
          // Try localStorage
          const compressed = localStorage.getItem(collectionKey);
          if (compressed) {
            const decompressStart = performance.now();
            collection = JSON.parse(decompress(compressed));
            this.stats.trackOperation('decompress', {
              time: performance.now() - decompressStart,
              slice
            });

            // Store in memory
            this.storage.set(slice, collection);
          }
        }

        if (collection) {
          hit = true;
          // Extract the specific item if a longer path was provided
          if (path.length > 1) {
            value = path.slice(1).reduce((obj, key) => obj?.[key], collection);
          } else {
            value = collection;
          }
        }
      } catch (error) {
        console.error(`Failed to retrieve cached collection for ${slice}:`, error);
      }
    } else {
      // For non-collection slices, use the original direct item storage
      try {
        // Try memory first
        value = this.storage.get(key);
        if (value !== undefined) {
          hit = true;
        } else {
          // Try localStorage
          const compressed = localStorage.getItem(`cache:${key}`);
          if (compressed) {
            const decompressStart = performance.now();
            value = JSON.parse(decompress(compressed));
            this.stats.trackOperation('decompress', {
              time: performance.now() - decompressStart,
              slice
            });

            // Store in memory
            this.storage.set(key, value);
            hit = true;
          }
        }
      } catch (error) {
        console.error(`Failed to retrieve cached value for ${key}:`, error);
      }
    }

    this.stats.trackOperation('get', {
      slice,
      endpoint: this.getCurrentEndpoint(),
      size: value ? JSON.stringify(value).length : 0,
      time: performance.now() - startTime,
      hit
    });

    return value;
  }

  async cachePut(path, value) {
    const startTime = performance.now();
    const key = Array.isArray(path) ? path.join(':') : path;
    const slice = Array.isArray(path) ? path[0] : path.split(':')[0];

    try {
      if (this.isCollectionSlice(path)) {
        // For collection slices, update the item in the collection
        let collection = this.storage.get(slice) || {};

        if (path.length > 1) {
          // Update specific item in collection
          let current = collection;
          for (let i = 1; i < path.length - 1; i++) {
            current[path[i]] = current[path[i]] || {};
            current = current[path[i]];
          }
          current[path[path.length - 1]] = value;
        } else {
          // Update entire collection
          collection = value;
        }

        // Store updated collection
        const serialized = JSON.stringify(collection);
        const compressStart = performance.now();
        const compressed = compress(serialized);

        this.stats.trackOperation('compress', {
          time: performance.now() - compressStart,
          slice,
          ratio: compressed.length / serialized.length
        });

        // Store in memory and localStorage
        this.storage.set(slice, collection);
        localStorage.setItem(`cache:${slice}`, compressed);
      } else {
        // For non-collection slices, use direct item storage
        const serialized = JSON.stringify(value);
        const compressStart = performance.now();
        const compressed = compress(serialized);

        this.stats.trackOperation('compress', {
          time: performance.now() - compressStart,
          slice,
          ratio: compressed.length / serialized.length
        });

        // Store in memory and localStorage
        this.storage.set(key, value);
        localStorage.setItem(`cache:${key}`, compressed);
      }

      this.stats.trackOperation('put', {
        slice,
        endpoint: this.getCurrentEndpoint(),
        size: JSON.stringify(value).length,
        time: performance.now() - startTime
      });

      return true;
    } catch (error) {
      console.error(`Failed to cache value for ${key}:`, error);
      return false;
    }
  }

  // Helper to track current API endpoint
  getCurrentEndpoint() {
    // This could be set by DataGetter when making API calls
    return this._currentEndpoint;
  }

  setCurrentEndpoint(endpoint) {
    this._currentEndpoint = endpoint;
  }

  // Get statistics
  getStats() {
    return this.stats.getReport();
  }

  // Reset statistics
  resetStats() {
    this.stats.reset();
  }

  // Load initial data from localStorage
  loadFromStorage() {
    for (let i = 0; i < localStorage.length; i++) {
      const key = localStorage.key(i);
      if (key.startsWith('cache:')) {
        try {
          const compressed = localStorage.getItem(key);
          const value = JSON.parse(decompress(compressed));
          this.storage.set(key.replace('cache:', ''), value);
        } catch (error) {
          console.error(`Failed to load cached value for ${key}:`, error);
        }
      }
    }
  }
}


// Usage example
export function monitorCachePerformance(dataGetter) {
  setInterval(() => {
    const stats = dataGetter.dataCache.getStats();
    console.log('Cache Performance Report:', stats);

    // Example stats output:
    console.log('Most accessed endpoints:',
      Object.entries(stats.byEndpoint)
        .sort((a, b) => b[1].gets.count - a[1].gets.count)
        .slice(0, 5)
    );

    console.log('Largest cache slices:',
      Object.entries(stats.bySlice)
        .sort((a, b) => b[1].totalSize - a[1].totalSize)
        .slice(0, 5)
    );

    console.log('Overall hit rate:',
      stats.operations.get.hitRate
    );

    dataGetter.dataCache.resetStats(); // Start fresh for next period
  }, 10000); // Every ten seconds
}