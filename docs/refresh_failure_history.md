# History of GitHub action errors out of our control
These errors typically resulted from the DB refresh or drafts finalization (fetch failures, 0 members) actions, mainly 
because these errors run by far the most frequently.

This section is organized in sections, with each section representing the failing system.

Information has been saved about each error. Not all errors documented here contain the same level of detail, but most errors will contain the following information:
- Dates when the error occurred
- A link to a GitHub Action log where one of the instances occurred
- A copy/paste of the perceived most important part of the error message
- Possibly some additional comments.

## GitHub
#### GitHub Actions has encountered an internal error when running your job
* 2024/02/07,7/30,10/25,10/30x2,12/24
- `The hosted runner encountered an error while running your job. (Error Type: Failure).`
- https://github.com/jhu-bids/TermHub/actions/runs/7810475007
- No further error messages. Not even any logs.

#### Internal server error occurred while resolving "actions/checkout@v2"
* 2024/01/01,2025/01/13
- https://github.com/jhu-bids/TermHub/actions/runs/7461546468/job/20301896684

#### We couldn't respond to your request in time
* 2025/02/06x2
- https://github.com/jhu-bids/TermHub/actions/runs/13175701795/job/36774403460

RuntimeError: Error calling GitHub action resolve_fetch_failures_0_members.yml with params:
Response: {'message': "We couldn't respond to your request in time. Sorry about that. Please try resubmitting your request and contact us if the problem persists."}
```

#### Timeout err
* 2024/08/09
- https://github.com/jhu-bids/TermHub/actions/runs/10318159122
- Got to the main job, but then got err message outside of the job log, in the front area of the action log:
```
refresh-db
Failed to download action 'https://api.github.com/repos/stefanzweifel/git-auto-commit-action/tarball/3ea6ae190baf489ba007f7c92608f33ce20ef04a'. Error: The request was canceled due to the configured HttpClient.Timeout of 100 seconds elapsing.
```

#### We couldn't respond to your request in time
* 2024/08/13
- https://github.com/jhu-bids/TermHub/actions/runs/10370337473/job/28707981632
- I'm guessing there is a 4xx status code associated with this, but I don't print the status code in the error message so I don't know what it was.
```
Response: {'message': "We couldn't respond to your request in time. Sorry about that. Please try resubmitting your request and contact us if the problem persists."}
```

#### Error: Name or service not known (internal-api.service.iad.github.net:443)
* 2024/09/25
- https://github.com/jhu-bids/TermHub/actions/runs/11039479094/job/30665124435
- `Warning: Failed to download action`

#### Error: The log was not found. It may have been deleted based on retention settings.
* 2024/11/25
- https://github.com/shadow-bids/TermHub/actions/runs/12017315954/job/33499365061

#### Error: error: RPC failed; HTTP 502 curl 22 The requested URL returned error: 502
* 2024/12/17
- Vocab refresh: https://github.com/jhu-bids/TermHub/actions/runs/12368789201/job/34519399736
```
"Fetching submodules
Error: error: RPC failed; HTTP 502 curl 22 The requested URL returned error: 502
Error: fatal: expected flush after ref listing
Error: fatal: clone of 'git@github.com:jhu-bids/termhub-csets.git' into submodule path '/home/runner/work/TermHub/TermHub/termhub-csets' failed
Error: The process '/usr/bin/git' failed with exit code 1"
```

#### An unexpected error has occurred
* 2024/06/25
- https://github.com/jhu-bids/TermHub/actions/runs/9668652016
- The job didn't even begin to run.
```
An unexpected error has occurred and we've been automatically notified. Errors are sometimes temporary, so please try again. If the problem persists, please check whether the Actions service is operating normally at https://githubstatus.com. If not, please try again once the outage has been resolved. Should you need to contact Support, please visit https://support.github.com/contact and include request ID: 64C0:31E3CC:1953584:2EBB2F4:667B1E6C
```

#### make: error: unable to locate xcodebuild
- https://github.com/jhu-bids/TermHub/actions/runs/8099792377/job/22136364489
```
Run make test-missing-csets
make: error: unable to locate xcodebuild, please make sure the path to the Xcode folder is set correctly!
make: error: You can set the path to the Xcode folder using /usr/bin/xcode-select -switch
```

#### Error: The operation was canceled. - (But we didn't do it~)
* 2024/02/03
- ~At least I don't think so. I didn't ask Siggie, but it would seem very strange that they would cancel multiple jobs 2-3 hours apart like this, right at the very end, after it had done the whole refresh except for the final test.
- After running "refresh db" and "fetch missing csets", it was on the test part of the job, shows it running the python file, but then shows the operation was canceled. Happened 4x across several hours.
- https://github.com/jhu-bids/TermHub/actions/runs/7765408567/job/21180022267

## N3C Data Enclave
#### Enclave error 403
* 2024/02/26
- https://github.com/jhu-bids/TermHub/actions/runs/8055329291/job/22001919042
- `{'status_code': 403, 'text': '{"errorCode":"PERMISSION_DENIED","errorName":"ThirdPartyApplication:PermissionDenied`
- This issue lasted 12 hours from 3pm to 3am

#### Enclave error 406
* 2024/04/25,26,27x2,28(3),7/25,7/26x2
- example logs
  - refresh: https://unite.nih.gov/api/v1/ontologies/ri.ontology.main.ontology.00000000-0000-0000-0000-000000000000/objects/OMOPConceptSet?properties.createdAt.gt=TIMESTAMP
    - 4/25 https://github.com/jhu-bids/TermHub/actions/runs/8837564379/job/24266706288
  - fetch_failures: https://unite.nih.gov/api/v1/ontologies/ri.ontology.main.ontology.00000000-0000-0000-0000-000000000000/objects/OMOPConceptSet?properties.codesetId.eq=913137668
    - 4/27 1 https://github.com/jhu-bids/TermHub/actions/runs/8858240178/job/24326641369
```
enclave_wrangler.utils.EnclaveWranglerErr: {'status_code': 406, 'text': '', 'error_report': {'request': 'https://unite.nih.gov/api/v1/ontologies/ri.ontology.main.ontology.00000000-0000-0000-0000-000000000000/objects/OMOPConceptSet?properties.createdAt.gt=2024-04-25T14%3A05%3A33.408301-04%3A00', 'response': b'', 'msg': 'Error: response error: 406 Not Acceptable', 'curl': 'curl -H "Content-type: application/json" -H "Authorization: *" https://unite.nih.gov/api/v1/ontologies/ri.ontology.main.ontology.00000000-0000-0000-0000-000000000000/objects/OMOPConceptSet?properties.createdAt.gt=2024-04-25T14%3A05%3A33.408301-04%3A00'}}
```

#### Enclave error 500
* 2024/02/01,03/22,05/02,06/27x2,08/10,11,9/30
- https://github.com/jhu-bids/TermHub/actions/runs/7747397477/job/21127759535#step:11:26
```
Error: response error: 500 Internal Server Error
enclave_wrangler.utils.EnclaveWranglerErr: {'status_code': 500, 'text': '{"errorCode":"INTERNAL","errorName":"Default:Internal"
```

#### Enclave error 503
* 2024/04/22,29,05/08,20,06/10,14,08/06,11,13x2,17,20,21,28,10/16,2025/02/11
- `503 Service Unavailable`
- example: fetch failures: https://github.com/jhu-bids/TermHub/actions/runs/8787257036/job/24112039983

#### ERROR: No matching distribution found for vshub_sdk
* 2024/08/23
- https://github.com/jhu-bids/TermHub/actions/runs/10524380900/job/29160990028
- FYI: The vshub_sdk is a pip install error. However, this is not hosted on PyPi and is hosted by the enclave.

#### ConnectionError
* 2025/01/15,02/10,21,24
- https://github.com/jhu-bids/TermHub/actions/runs/12793714488/job/35667172114
```
Enclave ConnectionError
requests.exceptions.ConnectionError: HTTPSConnectionPool(host='unite.nih.gov', port=443): Max retries exceeded with url: /api/v1/ontologies/ri.ontology.main.ontology.00000000-0000-0000-0000-000000000000/objects/OMOPConceptSet?... 
Failed to establish a new connection: [Errno 111] Connection refused'))
```


## PyPi
#### pip - unknown package
* 2024/03/23
- https://github.com/jhu-bids/TermHub/actions/runs/8397866020/job/23001892223
```
ERROR: THESE PACKAGES DO NOT MATCH THE HASHES FROM THE REQUIREMENTS FILE. If you have updated the package versions, please update the hashes. Otherwise, examine the package contents carefully; someone may have tampered with them.
unknown package:
Expected sha256 173f289...
Got        a4d474...
```

#### Error: Version #.# with arch arm64 not found
* 2024/04/24
- arm64: This applies to macos runner
- 4/24: 3.9.7 and 3.9 was an issue.
  - https://github.com/jhu-bids/TermHub/actions/runs/8824265442/job/24226367832

#### pip subprocess to install build dependencies did not run successfully
* 2024/03/16
- https://github.com/jhu-bids/TermHub/actions/runs/8310142795/job/22742308234
- note: This error originates from a subprocess, and is likely not a problem with pip.
- `error: subprocess-exited-with-error`

#### ERROR: THESE PACKAGES DO NOT MATCH THE HASHES FROM THE REQUIREMENTS FILE
* 2024/05/04,09,13,26,29,06/02,08,26
- https://github.com/jhu-bids/TermHub/actions/runs/8950592638/job/24586096342

#### ERROR: Could not find a version that satisfies the requirement pip (from versions: none)
* 2024/02/13,08/21
- Errored during "Setup Python version". I think a network error.
- https://github.com/jhu-bids/TermHub/actions/runs/10496400325/job/29076953715
```
ERROR: No matching distribution found for pip
The process '/bin/bash' failed with exit code 1
```
```
ERROR: Could not find a version that satisfies the requirement pydantic_core==2.20.1 (from versions: none)
```

#### JSONDecodeError on pip install
* 2024/05/17
- https://github.com/jhu-bids/TermHub/actions/runs/9126779615/job/25095724555

#### ERROR: Could not install packages due to an OSError
* 2024/06/25
- https://github.com/jhu-bids/TermHub/actions/runs/9658209391/job/26638925119
```
ERROR: Could not install packages due to an OSError: HTTPSConnectionPool(host='files.pythonhosted.org', port=443): Max retries exceeded with url: /packages/67/67/4bca5a595e2f89bff271724ddb1098e6c9e16f7f3d018d120255e3c30313/arrow-1.2.3-py3-none-any.whl.metadata (Caused by ResponseError('too many 503 error responses'))
```

#### SetupTools err
* 2024/07/29
- https://github.com/jhu-bids/TermHub/actions/runs/10137245725/job/28027212168
- For like 12 hours, after setuptools 72.0, things broke because they removed a command. then they released 72.1 which added it back

## Python
#### Error: Version 3.9.7 with arch x64 not found
* 2024/01/01~,03/17
- `Version 3.9.7 was not found in the local cache`
- https://github.com/jhu-bids/TermHub/actions/runs/7461878587/job/20302925236

## Postgres on Azure (probably within our control, actually)
#### FATAL: remaining connection slots are reserved for non-replication superuser connections
* 2024/03/07,8,9
- (This one is within our jurisdiction, I think. It should be under our control / preventable once we figure out what causes it. As of 2024/03/09, I still don't know what's causing it. I know it's resolved by restarting our DB, but it also looks like it spontaneously disappears as well.
- https://github.com/jhu-bids/TermHub/actions/runs/8216278947/job/22470679860
- https://github.com/jhu-bids/TermHub/issues/723
- `FATAL: remaining connection slots are reserved for non-replication superuser connections`
```
sqlalchemy.exc.OperationalError: (psycopg2.OperationalError) connection to server at "termhub.postgres.database.azure.com" (20.62.151.251), port 5432 failed: FATAL: remaining connection slots are reserved for non-replication superuser connections
```

#### Connection refused
* 2024/05/06,10/21,26
- `(psycopg2.OperationalError) connection to server at "termhub.postgres.database.azure.com" (20.62.151.251), port 5432 failed: Connection refused`
- https://github.com/jhu-bids/TermHub/actions/runs/8964137696/job/24615457286

## Uncategorized Connection Errors or similar
#### The job running on runner GitHub Actions 3 has exceeded the maximum execution time of 360 minutes
* 2024/01/14,29,03/02,14
- https://github.com/jhu-bids/TermHub/actions/runs/7517889397
- It doesn't even look like it ran. Open the job log and nothing there. Additionally if it had been running, then the next GitHub action that ran 20 minutes later would have said something like "refresh currently running; that refresh will run again when it completes. exiting". But it didn't say that. It ran normally.

#### requests.exceptions.ChunkedEncodingError
* 2024/08/30
- https://github.com/jhu-bids/TermHub/actions/runs/10632991073/job/29477074919
```
requests.exceptions.ChunkedEncodingError: ("Connection broken: InvalidChunkLength(got length b'', 0 bytes read)", InvalidChunkLength(got length b'', 0 bytes read))
ValueError: invalid literal for int() with base 16: b''
```
- stack
  - `find_missing_csets_within_threshold(age_minutes)`
  - `requests.get(url, headers=headers, args)`

#### pip._vendor.urllib3.exceptions.ReadTimeoutError: HTTPSConnectionPool(host='files.pythonhosted.org', port=443): Read timed out.
* 2024/01/17
- https://github.com/jhu-bids/TermHub/actions/runs/7556146504/job/20572540639

#### ConnectionResetError
* 2024/08/21,12/13,02/10
- https://github.com/jhu-bids/TermHub/actions/runs/10512004633/job/29124292223
- `urllib3.exceptions.ProtocolError: ('Connection aborted.', ConnectionResetError(104, 'Connection reset by peer'))`
- `requests.exceptions.ConnectionError: ('Connection aborted.', ConnectionResetError(104, 'Connection reset by peer'))`
- While connecting to DB?

#### ConnectionError: Remote end closed connection without response
* 2025/05/29,31,08/30,10/01,16
```
http.client.RemoteDisconnected
requests.exceptions.ConnectionError: ('Connection aborted.', RemoteDisconnected('Remote end closed connection without response'))
```

#### NewConnectionError: Failed to establish a new connection
* 2024/06/04x7,06,11/06,12/06,2025/01/13
- https://github.com/jhu-bids/TermHub/actions/runs/9335104728/job/25694120914
- `ConnectionError: HTTPSConnectionPool(host='unite.nih.gov', port=443): Max retries exceeded`
- `NewConnectionError: Failed to establish a new connection: [Errno -3] Temporary failure in name resolution'))`

#### SSL SYSCALL error: Operation timed out
* 2024/01/17,18,02/01,04/16,17,18
- `sqlalchemy.exc.DatabaseError: (psycopg2.DatabaseError) could not receive data from server: Operation timed out`
- https://github.com/jhu-bids/TermHub/actions/runs/7549883615/job/20554642054

#### The hosted runner: GitHub Actions 4 lost communication with the server. Anything in your workflow that terminates the runner process, starves it for CPU/Memory, or blocks its network access can cause this error.
* 2024/01/17,26
- https://github.com/jhu-bids/TermHub/actions/runs/7561159304

#### unable to access 'https://github.com/jhu-bids/TermHub/': Could not resolve host: github.com
* 2024/01/29,2/2
- https://github.com/jhu-bids/TermHub/actions/runs/7704450503/job/20996766883

#### Error: nodename nor servname provided, or not known (api.github.com:443)
* 2024/01/12,23,25(x2),28,2/02,3,6
- or: `(codeload.github.com:443)`
- https://github.com/jhu-bids/TermHub/actions/runs/7502550492/job/20425408067
```
Failed to download action
Timed out
```

#### Enclave ConnectionError

#### ConnectionError: Failed to establish a new connection: [Errno 8] nodename nor servname provided, or not known'))
* 2024/01/01~,03/29x2,4/17
- `requests.exceptions.ConnectionError`
- Looks like some page at the enclave was down
- https://github.com/jhu-bids/TermHub/actions/runs/7480555512/job/20360226112
- https://github.com/jhu-bids/TermHub/actions/runs/8723315835/job/23931257588