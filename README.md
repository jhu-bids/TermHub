# TermHub

TermHub is a user interface and collection of analytic tools for working with concept sets. Its goal is to ease the process of concept set authoring and to facilitate the creation of higher-quality concept sets by providing users with immediate information and viasualization capabilities to understand their concept set and take advantage of existing concept sets that can aid their use case.

Allows comparison of overlapping concept sets, display of cset metadata, display of concept hierarchy, term usage and concept set patient counts, and modification and upload of concept sets to the N3C Enclave. Will interface with other code set repositories over time.


## [Features under development / consideration](https://docs.google.com/spreadsheets/d/19_eBv0MIBWPcXMTw3JJdcfPoEFhns93F-TKdODW27B8/edit#gid=0)
More info: [Requirements](https://github.com/jhu-bids/TermHub/issues/72)

### Uploading CSVs to create/edit concept sets
TermHub can take a CSV and create/edit concepts and concept sets. [Read more](./enclave_wrangler/README.md)

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

## Developer docs
- [Frontend](./frontend/README.md)  
- [Backend](./backend/README.md)

### Local setup
1. Clone the repository.
```shell
$ git clone  git@github.com:jhu-bids/TermHub.git
$ cd TermHub
```
2. Get Data
```shell
$ git submodule init
$ git submodule update
```
2. Run: `pip install -r requirements.txt`
3. Install PostgreSQL and make sure it is running
  - Postgres.app makes this a breeze on macos: https://postgresapp.com/ 
  - variables are initially set to the values below. Note that  PGDATABASE and TERMHUB_DB_DB will need to change to termhub in the steps below.
    - PGHOST=localhost
    - PGUSER=postgres
    - PGPASSWORD=
    - PGPORT=5432
    - PGDATABASE=postgres
4. Set environmental variables. Run: `mkdir env; cp .env.example env/.env`. Then, edit `.env` and set any variables that haven't been filled out. You'll likely need to reach out to @joeflack4 or @Sigfried.
  1. In terms of Postgres variables: PGHOST, PGUSER, PGPASSWORD, PGPORT, and PGDATABASE, and despite using shell syntax for those variables, the values have to be constants, not shell variables
    - TERMHUB_DB_SERVER=postgresql
    - TERMHUB_DB_DRIVER=psycopg2
    - TERMHUB_DB_HOST=$PGHOST
    - TERMHUB_DB_USER=$PGUSER
    - TERMHUB_DB_DB=$PGDATABASE
    - TERMHUB_DB_SCHEMA=n3c
    - TERMHUB_DB_PASS=$PGPASSWORD
    - TERMHUB_DB_PORT=$PGPORT
6. Basic DB setup (assuming PostgreSQL)
```shell
# create new db:
$ createdb termhub
# connect to new db:
$ psql termhub
# connected to postgres. run:
CREATE SCHEMA n3c;
SET search_path TO n3c;
```
6. Create DB structure and load data
7. Run: `python backend/db/initialize.py`

### Deployment
#### Deploying the backend
```shell
# Clone the repository.
$ git clone  git@github.com:jhu-bids/TermHub.git
$ cd TermHub
# get python dependencies
$ pip install -r requirements.txt
# get data
$ git submodule init
$ git submodule update
# start backend
$ uvicorn backend.app:APP --reload
```

#### Deploying the frontend, starting from the same repository
1. `cd frontend; npm run build`
2. When that process completes, you should now have an updated `frontend/build` directory. This can be deployed as a static site. The entry point is `index.html`.

