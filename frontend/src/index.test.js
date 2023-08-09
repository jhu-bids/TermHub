import { render, screen } from "@testing-library/react";
import { BrowserRouter } from "react-router-dom";
import { QCProvider } from "./App";
import "./index.css";

/* from App.test.js
test('renders learn react link', () => {
  render(<App />);
  const linkElement = screen.getByText(/learn react/i);
  expect(linkElement).toBeInTheDocument();
});
*/

test("renders the app starting with BrowserRouter and QCProvider", () => {
  render(
    <BrowserRouter>
      <QCProvider />
    </BrowserRouter>
  );
  // const linkElement = screen.getByText(/learn react/i);
  // I can't figure out this simple example... it's complaining for various reasons
  let linkElement = screen.getAllByText(/TermHub/i);
  expect(linkElement).toBeInTheDocument();
  linkElement = screen.getByText(/CSet Search/i);
  expect(linkElement).toBeInTheDocument();
});
