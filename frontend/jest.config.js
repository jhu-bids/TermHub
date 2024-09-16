/*
module.exports = {
  testEnvironment: 'jsdom',
  transform: {
    // '^.+\\.jsx?$': 'vite-jest',
    '^.+\\.(js|jsx|ts|tsx)$': 'vite-jest',
  },
  setupFilesAfterEnv: ['<rootDir>/jest.setup.js'],
};

module.exports = {
  testEnvironment: 'jsdom',
  transform: {
    '^.+\\.(js|jsx|ts|tsx)$': '@swc/jest',
  },
  setupFilesAfterEnv: ['<rootDir>/jest.setup.js'],
};
 */

module.exports = {
  testEnvironment: 'jsdom',
  transform: {
    '^.+\\.(js|jsx|ts|tsx)$': ['@swc/jest', {
      jsc: {
        parser: {
          syntax: 'ecmascript',
          jsx: true,
        },
        transform: {
          react: {
            runtime: 'automatic',
          },
        },
      },
    }],
  },
  setupFilesAfterEnv: ['<rootDir>/jest.setup.js'],
  moduleDirectories: ['node_modules', 'src'],
  moduleFileExtensions: ['js', 'jsx', 'ts', 'tsx', 'json', 'node'],
  transformIgnorePatterns: [
    'node_modules/(?!(react-merge-refs|@floating-ui/react-dom-interactions)/)',
  ],
  moduleNameMapper: {
    '^react-merge-refs$': '<rootDir>/src/__mocks__/react-merge-refs.js',
    '^@floating-ui/react-dom-interactions$': '<rootDir>/src/__mocks__/@floating-ui/react-dom-interactions.js',
    '^react-markdown$': '<rootDir>/src/__mocks__/react-markdown.js',
    '\\.(jpg|jpeg|png|gif|eot|otf|webp|svg|ttf|woff|woff2|mp4|webm|wav|mp3|m4a|aac|oga)$':
    'jest-transform-stub',
    '\\.(css|less|scss|sass)$': 'jest-transform-stub',
  },
};
