import React from 'react';
// import { test, expect, /*beforeAll, afterAll, beforeEach, afterEach */} from '@jest/globals';

import { render, screen } from '@testing-library/react';
import {AppWrapper} from './App';

test('renders learn react link', () => {
  render(<AppWrapper />);
  const linkElement = screen.getByText(/learn react/i);
  expect(linkElement).toBeInTheDocument();
});

test('anything at all', () => {
  expect(30 + 2).toBe(32);
})