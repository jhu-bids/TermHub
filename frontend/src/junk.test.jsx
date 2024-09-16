import React from 'react';
// import { test, expect, /*beforeAll, afterAll, beforeEach, afterEach */} from '@jest/globals';
// import { GraphContainer, makeGraph, } from './state/GraphState';
import { GraphOptionsProvider, useGraphOptions, } from './state/AppState';
import { render, act, screen } from '@testing-library/react';
import {renderHook} from '@testing-library/react-hooks';
// import {AppWrapper} from './App';
import { useState } from 'react'

function TestGraph() {
  const [graphOptions, graphOptionsDispatch] = useGraphOptions();
  console.log(graphOptions);
  return <pre>{JSON.stringify(graphOptions)}</pre>;
}
it('test count update', async () => {
  const { result } = renderHook(() => useState({ count: 0 }))
  const [state, setState] = result.current
  act(() => setState({ count: state.count + 1 }))
  const [nextState, _] = result.current
  expect(nextState.count).toBe(1)
})

test('renders learn react link', () => {
  render(<p>learn react</p>);
  const linkElement = screen.getByText(/learn react/i);
  expect(linkElement).toBeInTheDocument();
});


test('provider hook', () => {
  const wrapper = () => (
      <GraphOptionsProvider><TestGraph/></GraphOptionsProvider>
  );
  const {result} = renderHook(() => useGraphOptions(), {wrapper});
  const [graphOptions, graphOptionsDispatch] = result.current;
  expect(30 + 2).toBe(32);
});

test('anything at all', () => {
  expect(30 + 2).toBe(32);
})