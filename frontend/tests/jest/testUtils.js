// testUtils.js

let shouldContinue = true;

export const resetTestSuite = () => {
  shouldContinue = true;
};

export const safeTest = (name, testFn) => {
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