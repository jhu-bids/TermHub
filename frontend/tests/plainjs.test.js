/* eslint-disable */

import {test, expect} from 'jest';


// const { test, expect } = require('@playwright/test');

import {getIndentedTreeNodes} from "../src/components/CsetComparisonPage";

test('getIndentedTreeNodes()', () => {
  // TODO: get 'graph' from backend call or declare it here
  const graph = ''
  const results = getIndentedTreeNodes(graph)  // pass graph
  expect(results).toBe(true);  // TODO: make an assertion
})
