import React, {useLayoutEffect, useState,} from "react";
import {debounce, isEqual, reduce,} from "lodash";
import Papa from "papaparse";
import {saveAs} from 'file-saver';

export const pct_fmt = (num) =>
  Number(num).toLocaleString(undefined, {
    style: "percent",
    minimumFractionDigits: 2,
  });
export const fmt = (num) => Number(num).toLocaleString();
// cfmt = conditional format -- as number if number, otherwise no change
export const cfmt = (v) =>
  parseInt(v) === v || parseFloat(v) === v ? Number(v).toLocaleString() : v;

// from https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/Set#implementing_basic_set_operations
export function isSuperset(set, subset) {
  for (const elem of subset) {
    if (!set.has(elem)) {
      return false;
    }
  }
  return true;
}

export function union(setA, setB) {
  const _union = new Set(setA);
  for (const elem of setB) {
    _union.add(elem);
  }
  return _union;
}

export function intersection(setA, setB) {
  const _intersection = new Set();
  for (const elem of setB) {
    if (setA.has(elem)) {
      _intersection.add(elem);
    }
  }
  return _intersection;
}

export function symmetricDifference(setA, setB) {
  const _difference = new Set(setA);
  for (const elem of setB) {
    if (_difference.has(elem)) {
      _difference.delete(elem);
    } else {
      _difference.add(elem);
    }
  }
  return _difference;
}

export function difference(setA, setB) {
  const _difference = new Set(setA);
  for (const elem of setB) {
    _difference.delete(elem);
  }
  return _difference;
}
export function toRadians(angle) {
  return angle * (Math.PI / 180);
}

export function useWindowSize() {
  const [size, setSize] = useState([0, 0]);
  useLayoutEffect(() => {
    const updateSize = debounce(function () {
      setSize([window.innerWidth, window.innerHeight]);
    }, 300);
    window.addEventListener("resize", updateSize);
    updateSize();
    return () => window.removeEventListener("resize", updateSize);
  }, []);
  return size;
}

export function ShowWindowDimensions(props) {
  const [width, height] = useWindowSize();
  return (
    <span>
      Window size: {width} x {height}
    </span>
  );
}

export function oneSidedObjectDifference(a ,b) {
  return reduce(b, function(acc, val, key, col) {
    if ( !isEqual(a[key], val )) {
        acc[key] = val;
    }
    return acc;
  }, {})
}

export function saveCsv(rows, columns, filename, config, tsv = false) {

  config = config || {
    delimiter: tsv ? "\t" : ",",
    newline: "\n",
    // defaults
    quotes: tsv ? false : (c => {
      c = c.toString();
      return c.includes(",") || c.includes("\n");
    }),
    error: (error, file) => {
      console.error(error);
      console.log(file);
    },
    // header: true,
    // skipEmptyLines: false, //other option is 'greedy', meaning skip delimiters, quotes, and whitespace.
    columns: columns, //or array of strings
  }
  const dataString = Papa.unparse(rows, config);
  const blob = new Blob([dataString], {
    type: tsv ? 'text/tab-separated-values;charset=utf-8' : 'text/csv;charset=utf-8'
  });
  saveAs(blob, filename);
}