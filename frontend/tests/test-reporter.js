// @ts-check

const fs = require('fs');
const LOGDIR = process.cwd() + '/tests/performance';

/*
let cols = [  // from testInfo.attach in large-cset test
    'testName', 'testType', 'run_how', 'envName', 'page', 'codeset_ids', 'searchLoaded',
    'startLimit', 'startTotal', 'startUsed', 'searchLoadedUsed',
];
cols.concat([   // available in onTestEnd
    'status', 'duration', 'errors'
]);
*/

function writeToLog(fname, content) {
    fs.appendFile(fname, content,
        (err) => {
        if (err) throw err;
        console.log('appended result to test log');
    });
}

// /** @implements {import('@playwright/test/reporter').Reporter} */
class MyReporter {
    reportData = [];
    logName = `${LOGDIR}/performance-tests-${(new Date()).toISOString().substr(0,16)}.csv`;
    headerWritten = false;
    cols = [];

    constructor(options) {
        console.log(process.cwd());
        console.log(`Starting tests. Logging results to ${this.logName}`);
        // console.log(`my-awesome-reporter setup with customOption set to ${options.customOption}`);
    }

    onBegin(config, suite) {
      console.log(`Starting the run with ${suite.allTests().length} tests`);
    }

    onTestBegin(test) {
      console.log(`Starting test ${test.title}`);
    }

    onTestEnd(test, result) {
      let {status, duration, errors} = result;
      if (status !== 'passed') {
        console.log(result);
      }
      errors = errors.map(e => e.message).join('; ');
      console.log(`Finished test ${test.title}: ${result.status}`);
      let reportLine = {name: test.title, status, duration, errors};
      for (const a of result.attachments) {
        reportLine = {...reportLine, ...JSON.parse(a.body.toString())};

        if (!this.headerWritten) {
            this.cols = Object.keys(reportLine);
            let csvHeader = this.cols.join('\t') + '\n';
            writeToLog(this.logName, csvHeader);
            this.headerWritten = true;
        }
      }
      let csvLine = '';
      csvLine += this.cols.map(c => reportLine[c]).filter(d => typeof(d) !== 'undefined').map(d => d.toLocaleString()).join('\t') + '\n';
      console.log(csvLine);
      writeToLog(this.logName, csvLine);
    }

    onError(error) {
        console.log('\nError in onError!!!!');
        console.log(error);
        debugger;
    }

    onEnd(result) {
        console.log(`Finished the run: ${result.status}`);
    }

    /*
    onStdOut(chunk, test, result) {
        console.log(`${test} output: ${chunk}`);
    }
    */
    onStdErr(chunk, test, result) {
        console.log(`${test} error: ${chunk}`);
        debugger;
    }
  }

  module.exports = MyReporter;