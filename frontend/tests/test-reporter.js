// @ts-check

const fs = require('fs');
const {isEmpty} = require('lodash');
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
    fs.appendFileSync(fname, content);
    /*
    fs.appendFile(fname, content,
        (err) => {
        if (err) throw err;
        console.log('appended result to test log');
    });
    */
}
function stripAnsiCodes(text) { // Remove ANSI escape codes
  // return text.replace(/\x1B[[(?);]*[0-9A-Za-z]/g, '');
  // got that from chatgpt, doesn't work here...trying a variation
  return text.replace(/\x1B\[[0-9]+m/g, '');
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
      duration = duration / 1000; // convert from milliseconds to seconds
      if (status !== 'passed') {
        console.log(result);
      }
      errors = errors.map(e => stripAnsiCodes(e.message)).join('; ');
      errors.replaceAll('"', "'");
      errors = `"${errors}"`;
      console.log(`Finished test ${test.title}: ${result.status}`);
      let reportLine = {name: test.title, status, duration, errors};
      // for (const a of result.attachments) { }
      let attachmentJson = '', attachmentObj = {};
      if ( (result.attachments || []).length > 0) {
        const a = result.attachments[result.attachments.length - 1];
        attachmentJson = (a.body && a.body.toString());
        attachmentObj = attachmentJson && JSON.parse(attachmentJson) || {};
      }
      if (isEmpty(attachmentObj)) {
        console.log("why no attachments?");
        // debugger;
      }
      reportLine = {...reportLine, ...attachmentObj};

      if (!this.headerWritten) {
          this.cols = Object.keys(reportLine);
          let csvHeader = this.cols.join('\t') + '\n';
          writeToLog(this.logName, csvHeader);
          this.headerWritten = true;
      }
      let csvLine = '';
      csvLine += this.cols.map(c => reportLine[c]).map(d => typeof(d) === 'undefined' ? '' : d.toLocaleString()).join('\t') + '\n';
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