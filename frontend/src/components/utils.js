import React, { useLayoutEffect, useState } from "react";
import {debounce} from "lodash";

const pct_fmt = (num) =>
  Number(num).toLocaleString(undefined, {
    style: "percent",
    minimumFractionDigits: 2,
  });
const fmt = (num) => Number(num).toLocaleString();
// cfmt = conditional format -- as number if number, otherwise no change
const cfmt = (v) =>
  parseInt(v) === v || parseFloat(v) === v ? Number(v).toLocaleString() : v;

// from https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/Set#implementing_basic_set_operations
function isSuperset(set, subset) {
  for (const elem of subset) {
    if (!set.has(elem)) {
      return false;
    }
  }
  return true;
}

function union(setA, setB) {
  const _union = new Set(setA);
  for (const elem of setB) {
    _union.add(elem);
  }
  return _union;
}

function intersection(setA, setB) {
  const _intersection = new Set();
  for (const elem of setB) {
    if (setA.has(elem)) {
      _intersection.add(elem);
    }
  }
  return _intersection;
}

function symmetricDifference(setA, setB) {
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

function difference(setA, setB) {
  const _difference = new Set(setA);
  for (const elem of setB) {
    _difference.delete(elem);
  }
  return _difference;
}
function toRadians(angle) {
  return angle * (Math.PI / 180);
}

function useWindowSize() {
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

function ShowWindowDimensions(props) {
  const [width, height] = useWindowSize();
  return (
    <span>
      Window size: {width} x {height}
    </span>
  );
}

export {
  pct_fmt,
  fmt,
  cfmt,
  isSuperset,
  union,
  intersection,
  symmetricDifference,
  difference,
  useWindowSize,
};
