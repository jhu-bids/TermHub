import { render, screen } from "@testing-library/react";
import { BrowserRouter } from "react-router-dom";
import { AppWrapper } from "./App";
// import { shallow } from 'enzyme';
import { createMemoryHistory } from 'history';
import { Router } from 'react-router-dom';
import '@testing-library/jest-dom/extend-expect';

describe('App tests', () => {
  let getByTestId;

  /*
  beforeAll(() => {
    // render TermHub landing page
    getByTestId = render(
        <BrowserRouter>
          <AppWrapper />
        </BrowserRouter>
    ).getByTestId;
  });
  */

  test('component has the correct title prop', () => {
    const getByTestId = render(
        <BrowserRouter>
          <AppWrapper />
        </BrowserRouter>
    ).getByTestId;
    const element = screen.getByTestId('app-name'); // Adjust this to your actual test ID or query method
    expect(element).toHaveTextContent('TermHub');
  });

  test('component has a version', () => {
    const getByTestId = render(
        <BrowserRouter>
          <AppWrapper />
        </BrowserRouter>
    ).getByTestId;
    const appv = screen.getByTestId('app-version');
    expect(appv).toHaveTextContent('v');
  });

  test('autocomplete value corresponds with url codeset_ids', () => {
    // const element = screen.getByText('Welcome to TermHub! Beta version ');
    // expect(element).toBeInTheDocument();
    // const history = createMemoryHistory();
    // Replace '/your-route' with the URL you want to test
    // history.push('OMOPConceptSets?codeset_ids=413507552');

    // const element = screen.getByTestId('autocomplete'); // Adjust this to your actual test ID or query method
    // since working on DOM, not components, I can't check for autocomplete.value, so check for MuiChip-root
    // const element = screen.getByText('413507552 - asthma (v1)'); // Adjust this to your actual test ID or query method
    // expect(element).toHaveTextContent('413507552 - asthma (v1)');
  });

  // todo: shallow test?: chatgpt doesn't recommend
  // test('shallow test', () => {
  //   const wrapper = shallow(BrowserRouter);
  //   const renderedText = wrapper.find('div').text();
  //   expect(renderedText).toEqual('testing');
  // });

  /*
  test("renders the app starting with BrowserRouter and AppWrapper", () => {
    // let linkElement = screen.getAllByText(/TermHub/i)[0];
    // expect(linkElement).toBeInTheDocument();
    // linkElement = screen.getByText(/CSet Search/i);
    // expect(linkElement).toBeInTheDocument();
  });
   */

  // Additional tests here
});


/*
test("renders the app starting with BrowserRouter and AppWrapper", () => {
  // BrowserRouter=>AppWrapper is set up in setupTests.js
  let linkElement = screen.getAllByText(/TermHub/i)[0];
  expect(linkElement).toBeInTheDocument();
  // linkElement = screen.getByText(/CSet Search/i);
  // expect(linkElement).toBeInTheDocument();
});

 */
