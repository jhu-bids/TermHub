import React from 'react';
// import logo from './logo.svg';
import './App.css';

function App() {
  return (
    <div className="App">
      {/*<header className="App-header">*/}
      <header>
        {/*<img src={logo} className="App-logo" alt="logo" />*/}
        <p>
          Edit <code>src/App.js</code> and save to reload.
        </p>
        <a
          className="App-link"
          href="https://reactjs.org"
          target="_blank"
          rel="noopener noreferrer"
        >
          Learn React!
        </a>
      </header>
      <User/>
    </div>
  );
}

function User() {
  const [value, setValue] = React.useState(null);

  React.useEffect(() => {
    fetch('http://127.0.0.1:8000/ontocall/objectTypes')
      .then(results => results.json())
      .then(data => {
        setValue(data);
      });
  }, []); // <-- Have to pass in [] here!

  return (
    <div>
      {!value ? 'Loading...' : JSON.stringify(value)}
    </div>
  );
}

// ReactDOM.render(<User/>, document.querySelector('#app'));

export default App;
