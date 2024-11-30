# Developer docs
## [Frontend](../frontend/README.md)
## [Backend](../backend/README.md)

## Testing
### Backend tests
Can be run locally via `python -m unittest discover`. There is also a GitHub action to run them.
### Frontend tests
We currently don't have a unit test suite.
We do have some end-to-end test workflows. Can run them locally via `make test-frontend`, but if you check the makefile,
you can see alternative commands (e.g. debugging). There is also a GitHub action for this.

## Database
### Refresh: Concept set tables (`code_sets`, `concept_set_container`, `concept_set_version_item` `concept_set_members`)
There are several database refreshes, which synchronize TermHub with its data source, the N3C data enclave. The most 
important of these is for the concept set tables. After these tables are synchronized, any dependent tables or views 
are also regenerated.

A refresh is done nightly via [GitHub action](https://github.com/jhu-bids/TermHub/actions/workflows/db_refresh.yml), 
but this can also be run manually, either by (a) using the [GitHub action](https://github.com/jhu-bids/TermHub/actions/workflows/db_refresh.yml), or (b) running the Python script 
manually via `python backend/db/full_data_refresh.py`, which supports the following CLI parameters.

| Parameter                              | Default | Description                                                                                                                                                                                                                                  |
|----------------------------------------|---------|----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `-t` / `--hours-threshold-for-updates` | 24      | Threshold for how many hours since last update before we require refreshes. If last update time was less than this, nothing will happen. Will evaluate this separately for downloads of local artefacts as well as uploading data to the DB. |
| `-o` / `--objects`                     | False   | Download objects.                                                                                                                                                                                                                            |
| `-c` / `--datasets-csets`              | False   | Download datasets from the "cset" group.                                                                                                                                                                                                     |
| `-v` / `--datasets-vocab`              | False   | Download datasets from the "vocab" group                                                                                                                                                                                                     |
| `-f` / `--force-download-if-exists`    | True    | If the dataset/object already exists as a local file, force a re-download. This is moot if the last update was done within --hours-threshold-for-updates.                                                                                    |
| `-l` / `--use-local-db`                | False   | Use local database instead of server.                                                                                                                                                                                                        |

### Refresh: Counts tables
Patient and record counts are updated in the N3C data enclave routinely, typically every few weeks or months. There is 
a [GitHub action](https://github.com/jhu-bids/TermHub/actions/workflows/refresh_counts.yml) that checks nightly for 
any changes and updates if so.

This refresh updates the `concept_set_counts_clamped` and `deidentified_term_usage_by_domain_clamped` tables, as well 
as their derived tables and views.

This can also be run manually via `make refresh-counts`, or `python backend/db/refresh_dataset_group_tables.py 
--dataset-group counts`.

### Refresh: Vocabulary tables
OMOP vocabulary tables are updated typically every 6 months. There is 
a [GitHub action](https://github.com/jhu-bids/TermHub/actions/workflows/refresh_voc.yml) that checks nightly for 
any changes and updates if so. 

**Warning**: As of November 2024, the GitHub action for this no longer works 100% of the time. Inexplicably, even with 
the same inputs, sometimes it only takes ~4.5 hours, and sometimes it takes >6 hours, which is greater than the maximum 
allowable time for GitHub actions. If it fails, then we can do the following: (i) perhaps just try running the action 
again; maybe it will take <6 hours the second time, or (ii) just run the refresh locally. 

This refresh updates the `concept`, `concept_ancestor`, `concept_relationship`, `relationship` tables, as well 
as their derived tables and views.

Additionally, whenever this refresh occurs, the `networkx` graph `term-vocab/relationship_graph.pickle` needs updating. 
Presently this does not happen as part of the refresh runs, but afterward. The next time that the app starts, if it 
sees that the pickle is out of date, it will regenerate it. This takes about 5 minutes.

This can also be run manually via `make refresh-vocab`, or `python backend/db/refresh_dataset_group_tables.py 
--dataset-group vocab`.

### Standard Operating Procedure (SOP) for vocabulary refresh
Every 6 months or so, whenever the vocab tables are updated:
1. Run the vocab refresh locally.
2. Go to https://portal.azure.com/ and restart the TermHub server(s).
3. After 15 minutes or so, face check the app in the browser to make sure it's working.
4. It's also a good idea to run the frontend [Playwright E2E tests](https://github.com/jhu-bids/termhub/actions), 
though these do run nightly.

### Allowing remote access
To allow a new user to access the database remotely, their IP address must be added to Azure: (i) select 
[DB resource](https://portal.azure.com/#@live.johnshopkins.edu/resource/subscriptions/fe24df19-d251-4821-9a6f-f037c93d7e47/resourceGroups/JH-POSTGRES-RG/providers/Microsoft.DBforPostgreSQL/flexibleServers/termhub/overview), (ii) [select 'Networking'](https://portal.azure.com/#@live.johnshopkins.edu/resource/subscriptions/fe24df19-d251-4821-9a6f-f037c93d7e47/resourceGroups/JH-POSTGRES-RG/providers/Microsoft.DBforPostgreSQL/flexibleServers/termhub/networking), (iii) add IP address.

### Creating backups
**Prerequisites**
You should have an environmental variable called `psql_conn`, set as follows:
`psql_conn="host=$TERMHUB_DB_HOST port=$TERMHUB_DB_PORT dbname=$TERMHUB_DB_DB user=$TERMHUB_DB_USER 
password=$TERMHUB_DB_PASS sslmode=require"`

If you run `./db_backup.sh`, it will generate commands that you can directly copy/paste into the terminal to (i) 
create the backup, and (ii) restore it.

**Optional steps**
- [Google Drive](https://drive.google.com/drive/folders/1Nc2ZVzjT62q__wrNRfKfFsstaMvrG3Rm): Uploading the backup there as well can be helpful because it has happened in the past that our 
- backup schemas on PostgreSQL have gotten corrupted.

### Adding new tables / views
If any new views or derived tables are added, there are some additional steps that need to be followed in order to avoid
breaking the database refresh and ensuring that these tables stay up-to-date when refreshes happen.
1. **Create a DDL file**
This needs to be added to `backend/db/`. The standard file naming is `ddl-N-MODULE.jinja.sql`, where `N` is the position
in which it should run relative to other such files, and `MODULE` is the module name, e.g. the name of the table(s) or
other operations done by the DDL. When choosing the position of the file (`N`), you should put it after any / all other
DDL which is used to create any of the tables/views that it is derived from.
2. Update `backend/db/config.py:DERIVED_TABLE_DEPENDENCY_MAP`.
3. Update `backend/db/config.py:DERIVED_TABLE_DEPENDENCY_MAP` if it is a view.

Additional rules:
- Each table and view should be in their own DDL, not part of another DDL, even if they only depend on one table. 
- Otherwise there will be errors.
- The Jinja `{{optional_suffix}}` should only go on the table/view being created itself, not what it's selecting from:
  - E.g. you want like: `CREATE OR REPLACE VIEW {{schema}}all_csets_view{{optional_suffix}} ...` and 
  - `... FROM {{schema}}all_csets);`


### Troubleshooting specific issues
#### `ERROR: cannot execute <COMMAND> in a read-only transaction`
Or, you may see: `WARNING:  transaction read-write mode must be set before any query`
This seems to result from situations where we're running commands after the database recently ran out of memory. It
seems like it goes into read only mode at that point and these commands need to be ran to reset it.
```sql
BEGIN;
SET transaction read write;
ALTER DATABASE termhub SET transaction_read_only = off;
ALTER DATABASE termhub SET default_transaction_read_only = off;
COMMIT;
```

#### `FATAL:  remaining connection slots are reserved for non-replication superuser connections`
If you see seomthing like this...
```
psql -d $psql_conn
psql: error: connection to server at "termhub.postgres.database.azure.com" (20.62.151.251), port 5432 failed: FATAL:
remaining connection slots are reserved for non-replication superuser connections
```
...This can be resolved by opening up the [DB management page in Azure](https://portal.azure.com/#@live.johnshopkins.edu/resource/subscriptions/fe24df19-d251-4821-9a6f-f037c93d7e47/resourceGroups/JH-POSTGRES-RG/providers/Microsoft.DBforPostgreSQL/flexibleServers/termhub/overview) and clicking the "Restart" button near the top.

### Emergency handbook: Recovering from corrupted databases
#### 1. Reinstate working database
##### a. Restore from a backup
You likely will already have a schema called `n3c` which is corrupted in some way, hence why you want to restore from backup.
Step 1: Remove/rename corrupted `n3c` scema

1.a. Back up corrupted `n3c` schema: If you want to keep that schema for whateve reason, you can create a new backup 
for it as in step (1), or simply give it a new schema name:
`ALTER SCHEMA n3c RENAME TO <new name>;`

1.b. Drop up corrupted `n3c` schema: But there's a good chance you just want to drop it instead, like so:
`DROP n3c WITH CASCADE;`

Step 2: Rename `n3c_backup_YYYYMMDD` as `n3c`
`ALTER SCHEMA <backup schema name> RENAME TO n3c;`

##### b. Run "DB Reset/Refresh (Datasets API)"
This script/workflow will download datasets from the N3C data enclave and perform the necessary steps to remake all of 
the database tables.
It can be run via (a) [its GitHub Action](https://github.com/jhu-bids/TermHub/actions/workflows/refresh_from_datasets.yml), or (b) directly via `python backend/db/refresh_from_datasets.py`.

#### 2. Quality control checks
Some things you might want to try to make sure that the restoration worked.
1. Run `make counts-update`. Then, run `make counts-table`, `make counts-compare-schemas`, or `make counts-docs`, 
2. depending on the situation, and check that the counts/deltas look good.
2. Restart local backend/frontend, load frontend in browser, clear `localStorage` (from console: 
`localStorage.clear()`), and face check various application features.
3. Load [dev deployment](http://bit.ly/termhub-dev), clear `localStorage` in the same way, and face check various application features.
4. Face check `n3c` schema. Just look at the tables and make sure they don't look weird.

## Deployment
Many of these steps are specific to the JHU BIDS team, which deploys on JHU's Azure infrastructure.

### Prerequisite steps
**Update environmental variables for GitHub actions when necessary**:
Every once in a while, will need to update the [ENV_FILE GitHub Secret](https://github.com/jhu-bids/TermHub/settings/secrets/actions/ENV_FILE)
with a copy/paste of `env/.env`. This is only necessary whenever environmental variables have changed, such as 
`PALANTIR_ENCLAVE_AUTHENTICATION_BEARER_TOKEN` getting refreshed, which happens every few months. If you're confident 
that the environment is still up to date, this step can be skipped, but to be safe, it can be done every tie. _You can 
read more about this in the related "Periodic maintenance > Updating auth token" section._

### Do for both dev and prod
First, make replace the current `dev` or `prod` git tag with the commit that you are deploying from. The reason for this 
is because the Playright tests are set to run on those tagged commits, so that the tests that run are in sync with the 
actual deployment. That way, we'll know if some problem has occurred with our infrastructure. Playwright tests using the
latest code should only be run on local.

Example using `dev`:
```sh
# Optional: back up old tag
git checkout dev
git tag dev-YYYY-MM-DD  # The date the commit was made. There might already be such a tag.
# Make new tags
git checkout BRANCH_OR_COMMIT_TO_DEPLOY 
git tag -d dev  # delete locally
git tag dev
git tag dev-YYYY-MM-DD  # This is a backup. YYYY-MM-DD: The date the commit was made.
# Push updates
git push --tags -f  # -f (force) overwrites the previous `dev` tag
```

### Deploying to Dev
Use the GitHub actions. Click these links for [backend](https://github.com/jhu-bids/TermHub/actions/workflows/backend_dev.yml) and [frontend](https://github.com/jhu-bids/TermHub/actions/workflows/frontend_dev.yml) actions, and then click "Run Workflow".
After both are deployed, test the app here: http://bit.ly/termhub-dev

### Deploying to production
Use the GitHub actions. Click these links for [backend](https://github.com/jhu-bids/TermHub/actions/workflows/backend_prod.yml) and [frontend](https://github.com/jhu-bids/TermHub/actions/workflows/frontend_dprod.yml) actions, and then click "Run Workflow".
After both are deployed, the app app will be usable here: http://bit.ly/termhub

### Manual QA
After deploying, do some manual quality assurance.
**I. Clear cache**
Start by clearing the cache. Right now the best way to do that is by opening the console and doing `localStorage.clear()`.
As of 2023/08, we're in the process of fixing the clear cache button in the  "Help / About" page. And we're also in the
process of automatically clearing the cache on version, code, and data changes.

**II. Checks**
Face-check the app. Some ideas of things to try:
1. Does the example comparison page load?
2. Can you select some concept sets from the cset search page?
3. After doing (2), can you go to the comparison page and see the concept sets you selected?
4. Do the controls on the comparison page work correctly?

### Rollbacks
If you notice something wrong with a deployment, follow these steps to roll back to the last stable deployment.
1. Go to the [GitHub actions](https://github.com/jhu-bids/TermHub/actions) page.
2. From the left sidebar, click the action that corresponds to the broken deployment (e.g. Backend dev, Frontend dev, 
Backend prod, or Frontend prod).
3. Find the workflow that you think produced the last stable deployment, and click it to open its logs.
4. If you're looking at a backend workflow, under the "Jobs" section of the left sidebar, select the job with the name 
"build". If you're looking at a frontend workflow, select the job with the name "Build and Deploy".
5. It will scroll you to the bottom of the logs page. Scroll to the top, and you should see a step called "Print commit 
hash & branch for rollbacks & troubleshooting". Click that.
6. You should now see the commit hash. Copy it.
7. In your terminal, run `git checkout <commit hash>`. This will checkout the code at the commit hash you copied.
8. Create a new branch & push it; for example, `git checkout -b ROLLBACK; git push -u origin ROLLBACK`.
9. Go to the [GitHub actions](https://github.com/jhu-bids/TermHub/actions) page.
10. From the left sidebar, click the action that corresponds to the broken deployment (e.g. Backend dev, Frontend dev, 
Backend prod, or Frontend prod).
11. Click the "Run workflow" button on the right, and in the popup that appears, where it says "Use workflow from", 
click the dropdown menu and select the branch you just created (e.g. ROLLBACK). Then, click "Run workflow".
12. Finally, after the deployment has been successful, you can delete that branch (e.g. `ROLLBACK`) locally and on GitHub.

After the action finishes, your deployment should be rolled back to the last stable deployment.

You will also want to separately figure out what went wrong and fix it separately (i.e. in the `develop` branch), and 
make a new deployment again when things are stable and ready for a new release.

Note that for the _backend only_ instead of steps 2 - 4, you can also find the commit hash by going to the 
[deployments](https://github.com/jhu-bids/TermHub/deployments) page.

### Applying patches to existing deployments
Sometimes you may want to redeploy an existing deployment with only minor changes. For example, you may have updated
the `ENV_FILE` as discussed in the "Periodic maintenance > Updating auth token" section. Or, you may have noticed a
small bug and want to deploy the fix on top of the currently deployed commit, rather than deploying further updates
from `develop` or `main`.
What you want to do here is follow basically the same steps as in the "Deployment > Rollbacks" section. If all you did
was update `ENV_FILE`, you can follow those steps exactly. If you are mading additional changes, then you would
basically modify step (8). Instead of `git checkout -b BRANCH; git push -u origin BRANCH`, you would do
`git checkout -b BRANCH`, make your changes and do a new commit, and then `git push -u origin ROLLBACK`.

### Troubleshooting
#### _Logs_
**Special case: Failed deployments**: Below are steps to find general logs. In order to find the azure log for failed 
deployments, [go here](https://portal.azure.com/#@live.johnshopkins.edu/resource/subscriptions/fe24df19-d251-4821-9a6f-f037c93d7e47/resourceGroups/jh-termhub-webapp-rg/providers/Microsoft.Web/sites/termhub/slots/dev/vstscd) 
, select "Logs" and then select the one that failed.

Logs for the backend can be opened via the following steps.
Option A: Log stream
Advantages of log stream vs granular: (i) easier to get to, (ii) combines multiple logs into 1. Disadvantages: (i) when
it refreshes, you will have to scroll back down to the bottom, (ii) can be harder to find what you're looking for.
1. Log into https://portal.azure.com.
2. From the list of _Resources_, select the deployment. For production, its "Name" is "termhub" and its "Type" is "App 
Service". For development, its "Name" is "dev / (termhub/dev)", and its "Type" is "App Service (Slot)".
3. There is a "Log stream" option in the left sidebar. Click it.

Option B: Granular logs
1. Log into https://portal.azure.com.
2. From the list of _Resources_, select the deployment. For production, its "Name" is "termhub" and its "Type" is "App 
Service". For development, its "Name" is "dev / (termhub/dev)", and its "Type" is "App Service (Slot)".
3. From the left sidebar, select "Advanced Tools" (unfortunately, none of "Logs", "App Service Logs", or "Log stream" 
are what you want).
4. Click "Go ->".
5. Click "Current Docker logs".
6. Find the log: A JSON list of log references will appear. Each log ref has an "href" field with a URL. It seems like 
there's always about a dozen or so refs. Unfortunately, there doesn't seem to be a way to tell which one is the one 
7. that we're usually going to want; that is, the one which will show things like stacktraces from server errors. 
8. You'll have to open each and scroll to the bottom until you find what you are looking for.

Option C: Less recent logs
1. Log into https://portal.azure.com.
2. From the list of _Resources_, select the deployment. For production, its "Name" is "termhub" and its "Type" is "App 
3. Service". For development, its "Name" is "dev / (termhub/dev)", and its "Type" is "App Service (Slot)".
3. From the left sidebar, select "Advanced Tools" (unfortunately, none of "Logs", "App Service Logs", or "Log stream" 
are what you want).
4. Click "Go ->".
5. Click "Bash" at the top.
6. There will be a logs folder that you can `cd` into which has a history of logs which include dates in the names.

#### SSH
Note that if the app is not starting, SSH will not work.
Also, it's helpful to know the difference between "Bash" and "SSH" in the "Advanced Tools" console. "Bash" is for
accessing the machine that manages deployments. "SSH" is for accessing the machine where the app source code is located.
1. Log into https://portal.azure.com.
2. From the list of _Resources_, select the deployment. For production, its "Name" is "termhub" and its "Type" is "App 
Service". For development, its "Name" is "dev / (termhub/dev)", and its "Type" is "App Service (Slot)".
3. From the left sidebar, select "Advanced Tools" (unfortunately, none of "Logs", "App Service Logs", or "Log stream" 
are what you want).
4. Click "Go ->".
5. Click "SSH" at the top.

#### Backend not working but logs not helpful?
It may be that the app has run out of memory. In https://portal.azure.com there is a way to check memory usage. You can
find this by opening the "App Service" ([example: develop](https://portal.azure.com/#@live.johnshopkins.edu/resource/subscriptions/fe24df19-d251-4821-9a6f-f037c93d7e47/resourceGroups/jh-termhub-webapp-rg/providers/Microsoft.Web/sites/termhub/slots/dev/appServices)
) and selecting "App Service Plan" ([example: develop](https://portal.azure.com/#@live.johnshopkins.edu/resource/subscriptions/fe24df19-d251-4821-9a6f-f037c93d7e47/resourceGroups/JH-TERMHUB-WEBAPP-RG/providers/Microsoft.Web/serverfarms/ASP-JHTERMHUBWEBAPPRG-8dbf/webHostingPlan)
). If it looks like it's maxed and/or of the logs say something about no memory, try increasing the memory to see if
that solves. If the memory must be increased, let a BIDS administrator (e.g. Tricia) know.

### Changing app config
Example use case: Changing Python version.
Steps: Stop app service, change config, start the service, and run the GH action to re-deploy.

## Versioning
### Semantic versioning
TermHub uses [semver (semantic versioning)](https://semver.org/). That is, Given a version number `MAJOR.MINOR.PATCH`,
increment the:
- `MAJOR` version when making incompatible API changes
- `MINOR` version when adding functionality in a backward compatible manner
- `PATCH` version when making backward compatible bug fixes

For example, if we add a new feature or make an update to an existing UI / user facing feature, but don't change
anything that breaks functionality for users or systems that depend on TermHub, that would be a `MINOR` version update.
So if the version was 1.10.2 before, it would be 1.11.0 after.

### How to do a version update
1. Update the version in `frontend/src/env.js`
2. Tag the version in GitHub: `git tag VERSION; git push --tags`

## Periodic maintenance
### Updating environmental variables
If any environmental variables are created/updated/deleted, follow these steps.

1. **Local `.env`:** All devs need to update their `env/.env` file. Each dev's `.env` should be exactly the same.
2. **GitHub settings**: Then the `.env` file should be copied and pasted into the `ENV_FILE` variable on GitHub. To do
this, go to the [GitHub actions secrets page](https://github.com/jhu-bids/TermHub/settings/secrets/actions), scroll down
to "repository secrets", edit `ENV_FILE`, paste the contents there, and save. _You can read more about this in the
related "Deployment > Prerequisite steps" section._
3. **Deployment**: Note that after the `ENV_FILE` is up to date, the currently deployed apps will not have access to its
new contents. _In order to deploy these changes, follow the instructions in "Deployment > Applying patches to existing
deployments"._

#### Updating auth token, if necessary
Not necessary if using OAuth, but we were not able to [finish setting that up](
https://github.com/jhu-bids/TermHub/issues/863).

The environmental variable `PALANTIR_ENCLAVE_AUTHENTICATION_BEARER_TOKEN` needs to be updated every 6 months. To do so,
contact Mariam Deacy, or another member of the enclave's IT team.
After doing so, set a reminder on your calendar before the expiry date.

Note that when close to expiring, messages will start to appear in the logs about that.