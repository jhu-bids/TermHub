module.exports = {
  // not sure this stuff is sueful
  testEnvironment: 'jest-environment-jsdom',
  transform: {
    '^.+\\.[t|j]sx?$': 'babel-jest',
    "node_modules\\/.+\\.(js)|(mjs)$": "@swc/jest",
    '\\.[tj]sx?$': ['babel-jest', { rootMode: 'upward' }]
  },
  
  
  // https://stackoverflow.com/questions/49263429/jest-gives-an-error-syntaxerror-unexpected-token-export
  // - didn't work
  transformIgnorePatterns: [
    "node_modules/(?!@ngrx|(?!deck.gl)|ng-dynamic)"
  ],
  
  setupFilesAfterEnv: ['./jest.setup.js'], // Optional, see Step 4
  testMatch: ['**/src/**/*.test.js', '**/src/**/*.spec.js'],
};
