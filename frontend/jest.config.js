/*
module.exports = {
  preset: 'ts-jest',
  testEnvironment: 'jest-environment-jsdom',
  transform: {
    '^.+\\.(js|jsx|ts|tsx)$': 'ts-jest',
    // "^.+\\.jsx?$": "babel-jest"
  },
  transformIgnorePatterns: [
    '/node_modules/(?!(@testing-library/jest-dom)/)',
  ],
  moduleFileExtensions: ['ts', 'tsx', 'js', 'jsx', 'json', 'node'],
  setupFilesAfterEnv: ['./jest.setup.js'],
};
 */
module.exports = {
  preset: 'ts-jest',

  // not sure this stuff is useful
  testEnvironment: 'jest-environment-jsdom',
  transform: {
    // '^.+\\.(js|jsx|ts|tsx)$': ['babel-jest', { rootMode: 'upward' }],
    '^.+\\.(js|jsx|ts|tsx)$': ['babel-jest', {
      configFile: '../babel.config.js'  // path to your root babel.config.js
    }],
  },
  // "transform": { "^.+\\.jsx?$": "babel-jest" },
  transformIgnorePatterns: [
    // '/node_modules/(?!(@testing-library/jest-dom)/)',
    // '/node_modules/(?!(@babel|@ngrx|(?!deck.gl)|ng-dynamic))',
    // "node_modules/(?!@ngrx|(?!deck.gl)|ng-dynamic)",
    // '/node_modules/(?!(@babel/runtime)/)'
    // https://stackoverflow.com/questions/49263429/jest-gives-an-error-syntaxerror-unexpected-token-export
    // - didn't work
  ],


  moduleFileExtensions: ['ts', 'tsx', 'js', 'jsx', 'json', 'node'],
  setupFilesAfterEnv: ['./jest.setup.js'],

  testMatch: ['.', '**/src/**/*.test.(ts|tsx|js|jsx)', '**/src/**/*.spec.(ts|tsx|js|jsx)'],
};