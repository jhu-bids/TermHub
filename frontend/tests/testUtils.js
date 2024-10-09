// testUtils.js
const singleSmallTestData = require('./test-data/singleSmallGraph.json');
const manySmallGraphContainerGraphData = require('./test-data/manySmallGraphContainerGraphData.json');
const asthmaGraphData = require('./test-data/asthmaExampleGraphData.json');

export const csetTestData = [singleSmallTestData, manySmallGraphContainerGraphData, asthmaGraphData];

export function getSafeTestFunc() {
/* ----------------------------------------------------------------------------
 * A series of safeTests can be run until the first one fails
 * and then the remaining will be skipped.
 * Probably don't try this with Playwright.
 * Allows ordered tests to begin with the state left by the
 * previous test. So, e.g., ./jest/graph_algorithm.test.js can
 * expand a concept subtree in one test and then collapse it in
 * the next (without having to start from scratch and expand again.)
 * ---------------------------------------------------------------------------*/
  let shouldContinue = true;

  const safeTest = (name, testFn) => {
    test(name, () => {
      if (!shouldContinue) {
        throw new Error('Skipped due to previous test failure');
      }
      try {
        testFn();
      } catch (error) {
        shouldContinue = false;
        throw error;
      }
    });
  };

  return safeTest;
}

/* Used to convert input to be same as graphology serialization (all strings). */
export function convertToArrayOfStrings(matrix) {
  var stringMatrix = [];
  for (var i = 0; i < matrix.length; i++) {
    var stringRow = [];
    for (var j = 0; j < matrix[i].length; j++) {
      stringRow.push(matrix[i][j].toString());
    }
    stringMatrix.push(stringRow);
  }
  return stringMatrix;
}
