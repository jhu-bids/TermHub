# TermHub
[![Test - Frontend - Unit tests and QC](https://github.com/jhu-bids/TermHub/actions/workflows/test_frontend_unit_and_qc.yml/badge.svg)](https://github.com/jhu-bids/TermHub/actions/workflows/test_frontend_unit_and_qc.yml)
[![Test - Backend - E2E and unit tests and QC](https://github.com/jhu-bids/TermHub/actions/workflows/test_backend_e2e_and_unit_and_qc.yml/badge.svg)](https://github.com/jhu-bids/TermHub/actions/workflows/test_backend_e2e_and_unit_and_qc.yml)
[![Test, Frontend Prod, Playwright E2E](https://github.com/jhu-bids/TermHub/actions/workflows/test_frontend_e2e_live_prod.yml/badge.svg)](https://github.com/jhu-bids/TermHub/actions/workflows/test_frontend_e2e_live_prod.yml)
[![Test, Frontend Dev, Playwright E2E](https://github.com/jhu-bids/TermHub/actions/workflows/test_frontend_e2e_live_dev.yml/badge.svg)](https://github.com/jhu-bids/TermHub/actions/workflows/test_frontend_e2e_live_dev.yml)

<details><summary>More badges</summary>
<p>

### More test statuses
Failure on this doesn't necessarily indicate an issue. It could just mean that the deployed instance has an older UI that is not compatible with new tests:  
[![Test, Frontend Dev (local changes), Playwright E2E](https://github.com/jhu-bids/TermHub/actions/workflows/test_frontend_e2e_live_dev_running_local.yml/badge.svg)](https://github.com/jhu-bids/TermHub/actions/workflows/test_frontend_e2e_live_dev_running_local.yml)

</p>
</details> 

TermHub is a user interface and collection of analytic tools for working with concept sets. Its goal is to ease the process of concept set authoring and to facilitate the creation of higher-quality concept sets by providing users with immediate information and viasualization capabilities to understand their concept set and take advantage of existing concept sets that can aid their use case.

Allows comparison of overlapping concept sets, display of cset metadata, display of concept hierarchy, term usage and concept set patient counts, and modification and upload of concept sets to the N3C Enclave. Will interface with other code set repositories over time.

## Docs index
- [TermHub home page](./README.md)
- [Developer](./docs/developer.md)
- [Backend](./backend/README.md)
  - [DB counts](./docs/backend/db/analysis.md) 
- [Frontend](./frontend/README.md)
    - [Testing](./frontend/tests/README.md)
- [Enclave Wrangler](./enclave_wrangler/README.md)
- [Stuff about graph algorithms](./docs/graph.md)

## [Features under development / consideration](https://docs.google.com/spreadsheets/d/19_eBv0MIBWPcXMTw3JJdcfPoEFhns93F-TKdODW27B8/edit#gid=0)
More info: [Requirements](https://github.com/jhu-bids/TermHub/issues/72)

### Uploading CSVs to create/edit concept sets
TermHub can take a CSV and create/edit concepts and concept sets. [Read more](./enclave_wrangler/README.md)

### Enclave Wrangler: CLI for the enclave API
Includes links to the API docs.
[Read more](./enclave_wrangler/README.md)

### Vocabulary management (a single concept, subsets of or an entire vocabulary)
The simple concept vocabulary mapping, SNOMED, etc.

### One concept set (cset)
A grouping of vocabularies (single concepts) that make up a particular value set. This entails user-based tagging. 

(Siggie?) The vocabulary that deals with just concept IDs and terminologies but also there is a part that deals with presence of these terminologies within your data source. 

Description of API needed outside enclave in order to do cset analysis:
(see Siggie's spreadsheet: https://roamresearch.com/#/app/jhu-bids/page/RsLm1drBI)

### multiple csets
--includes single cset to a revised single cset (version compare)
--similar/related csets
--combination of csets

managing multiple csets may include single cset comparisons, either one cset compared to another, or a single cset version comparison. It can include neighborhods or similar, related csets. Or, it can be a combination of csets for a broader category.

### Documentation and associated metadata
Source, Limitations, Intention

Identifying/labeling sets of csets: 
--bundles, 
--approved
--reviewed 
--published 
--externally curated, etc.

### Neighborhood analysis
Documentation and visualization;
reviewing, understanding, what is in the sets

Identifying neighborhoods
--what is similar/different
-- properties (articulating why they are different)
User Interactions
--select, relabel, groupings, 

### Review Process of cset(s)

### Validation
(is this the same as Review? maybe not)

### Choosing concept sets for Logic Liaison templates

### Archiving

### Editing Concepts & Concept Sets

## [Developer docs](./docs/developer.md)
Some of the important parts of [developer documentation](./docs/developer.md) are below, but for more thorough information on development for frontend/backend, follow these 2 links.
- [Frontend](./frontend/README.md)  
- [Backend](./backend/README.md)

### Local setup
#### 1. Clone repository
```shell
$ git clone  git@github.com:jhu-bids/TermHub.git
$ cd TermHub
```

#### 2. Get data from submodules
If git lfs hasn't been installed yet on your system, first run: `git lfs install`  

Then, update get the submodules:
```shell
$ git submodule init
$ git submodule update
```

At this point, check and see if files are there and have been pulled properly. For example, you can do 
`less termhub-csets/datasets/prepped_files/concept_relationship.csv`. If all you see there are a few lines lines which 
include text like `oid sha256:LONG_HASH` and `size SOME_NUMBER`, this means that `git submodule update` was unable to 
fetch the files, and you should run the git LFS commands below and check again.

```shell
$ git lfs pull
$ git submodule foreach git lfs pull
```

#### 3. Create [virtual environment](https://docs.python.org/3/library/venv.html) and activate it 
```shell
$ venv venv
$ source venv/bin/activate
```

#### 4. Install backend dependencies 
```shell
$ pip install -r requirements.txt
```

#### 5. Install frontend dependencies
```shell
$ cd frontend
$ npm install
$ cd ..
```

#### 6. Set environmental variables 
```shell
$ mkdir env
$ cp .env.example env/.env
``` 

Then, edit `.env` and set any variables that haven't been filled out. You'll likely need to reach out to @joeflack4 or 
@Sigfried. In terms of Postgres variables: `PGHOST`, `PGUSER`, `PGPASSWORD`, `PGPORT`, and `PGDATABASE`, and despite 
using shell syntax for those variables, the values have to be constants, not shell variables
```
TERMHUB_DB_SERVER=postgresql
TERMHUB_DB_DRIVER=psycopg2
TERMHUB_DB_HOST=$PGHOST
TERMHUB_DB_USER=$PGUSER
TERMHUB_DB_DB=$PGDATABASE
TERMHUB_DB_SCHEMA=n3c
TERMHUB_DB_PASS=$PGPASSWORD
TERMHUB_DB_PORT=$PGPORT
```

#### 7. Optional: Local database setup
You should have everything you need at this point to use TermHub. At this point, it will be connected to the same 
PostgreSQL database that is used in production. If you want to use a local database, follow the steps below.

##### 7.1. Install and start PostgreSQL
Postgres.app makes this a breeze on macos: https://postgresapp.com/ 
Variables are initially set to the values below. Note that `PGDATABASE` and `TERMHUB_DB_DB` will need to change to termhub in the steps below.
```
PGHOST=localhost
PGUSER=postgres
PGPASSWORD=
PGPORT=5432
PGDATABASE=postgres
```

##### 7.2. Basic DB setup
```shell
# create new db:
$ createdb termhub
# connect to new db:
$ psql termhub
# connected to postgres. run:
CREATE SCHEMA n3c;
SET search_path TO n3c;
```

##### 7.3. Create DB structure and load data
```shell
$ python backend/db/initialize.py
```

### Deployment
- [Backend](./backend/README.md): `uvicorn backend.app:APP --reload`
- [Frontend](./frontend/README.md): `cd frontend; npm run start`


### Database management
Refer to the [developer docs](./docs/developer.md) for more information.

## Using TermHub
### How to make changes to a codeset (via Atlas JSON)
1. Go to the "Cset Search" page.
2. Search for the codeset.
3. Select the codeset from the dropdown menu.
4. Optional: Select any additional codesets that might also be helpful in the process, e.g. to compare to the one we are editing.
5. Go to the "Cset Comparison" page.
6. Click on the column header for codeset you want to change.
  - Click <b>+</b> to add a concept
  - Click the <b>cancel sign</b> to remove a concept
  - Click <b>D</b> to toggle <code>inludeDescendants</code>
  - Click <b>M</b> to toggle <code>includeMapped</code>
  - Click <b>X</b> to toggle <code>isExcluded</code>
7. You will see two boxes at the top. The left box has some metadata about the codeset. The right box shows your <em>staged changes</em>. Click the <b>Export JSON</b> link in that <em>staged changes</em> box.
8. A new browser tab will up with just the JSON. Copy or save it.
9. Go back to the "Cset Comparison" page, and click the "Open in Enclave" link.
10. A new tab for the N3C data enclave will open. Log in if needed.
11. Click the "Versions" tab at the top left.
12. Click the blue "Create new version" button at the bottom left.
13. Fill out the information in the "Create New Draft OMOP Concept Set Version" popup, and click "Submit".
14. Your new draft version should appear on the left (may require a page refresh). Click it.
15. On the right hand side, there is a blue button called "Add Concepts". Click the down arrow, then select "Import ATLAS Concept Set Expression JSON" from the menu.
16. Copy/paste the JSON obtained from TermHub earlier into the box, and click "Import Atlas JSON".
17. Click the version on the left again.
18. On the right, click the green "Done" button.

### Database management
Refer to the [developer docs](./docs/developer.md) for more information.
