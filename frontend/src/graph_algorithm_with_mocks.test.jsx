import React from 'react';
import { render, act } from '@testing-library/react';
import '@testing-library/jest-dom';
import {AppWrapper} from './App';
import { CsetComparisonPage } from './components/CsetComparisonPage';
import { DataCacheProvider } from './state/DataCache';
import * as DataGetterModule from './state/DataGetter';
import {
  SearchParamsProvider,
  SessionStorageProvider,
} from './state/StorageProvider';
import {
  CidsProvider,
  CodesetIdsProvider,
  GraphOptionsProvider, NewCsetProvider,
} from './state/AppState';
import {DataGetterProvider} from './state/DataGetter';

// Mock the DataGetter
jest.mock('./state/DataGetter', () => ({
  useDataGetter: jest.fn(),
}));

// Mock localStorage
const localStorageMock = (function() {
  let store = {};
  return {
    getItem: jest.fn(key => store[key]),
    setItem: jest.fn((key, value) => {
      store[key] = value.toString();
    }),
    clear: jest.fn(() => {
      store = {};
    }),
  };
})();
Object.defineProperty(window, 'localStorage', { value: localStorageMock });

describe('CsetComparisonPage', () => {
  beforeEach(() => {
    // Reset mocks before each test
    jest.clearAllMocks();
    localStorageMock.clear();
  });

  it('fetches data and updates state correctly', async () => {
    // Mock the dataGetter
    const mockDataGetter = {
      getCsetComparison: jest.fn().mockResolvedValue({
        // Mock return value for getCsetComparison
      }),
      // Add other methods as needed
    };
    DataGetterModule.useDataGetter.mockReturnValue(mockDataGetter);

    // Render the component wrapped in necessary providers
    let component;
    await act(async () => {
      component = render(
          /*
          <AppWrapper>
            <CsetComparisonPage />
          </AppWrapper>

        <SearchParamsProvider>
        </SearchParamsProvider>
          */
          <SessionStorageProvider>
            <CodesetIdsProvider>
              <CidsProvider>
                <GraphOptionsProvider>
                  <NewCsetProvider>
                    <DataCacheProvider>
                      <DataGetterProvider>
                        <CsetComparisonPage />
                      </DataGetterProvider>
                    </DataCacheProvider>
                  </NewCsetProvider>
                </GraphOptionsProvider>
              </CidsProvider>
            </CodesetIdsProvider>
          </SessionStorageProvider>
      );
    });

    // Add your assertions here
    // For example:
    expect(mockDataGetter.getCsetComparison).toHaveBeenCalled();
    // Check if the component updated as expected
  });
});