// jest-dom adds custom jest matchers for asserting on DOM nodes.
// allows you to do things like:
// expect(element).toHaveTextContent(/react/i)
// learn more: https://github.com/testing-library/jest-dom
import "@testing-library/jest-dom";
import { render, screen } from "@testing-library/react";
import { BrowserRouter } from "react-router-dom";
import { AppWrapper } from "./App";

/*
render(<p>TermHub</p>)
export const setupLandingPage = (props) => {
  // return render(<MyComponent {...props} />);
  return render(
      <BrowserRouter>
        <AppWrapper />
      </BrowserRouter>
      );
};
render(
    <BrowserRouter>
      <AppWrapper />
    </BrowserRouter>
);
 */
