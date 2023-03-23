## Developer docs
### [Frontend](../frontend/README.md)  
### [Backend](../backend/README.md)
### Database
#### Refreshing database contents from sources
A refresh is done nightly via [GitHub action](https://github.com/jhu-bids/TermHub/actions/workflows/db_refresh.yml), but this can also be run manually, either by (a) using the [GitHub action](https://github.com/jhu-bids/TermHub/actions/workflows/db_refresh.yml), or (b) running the Python script manually via `python backend/db/full_data_refresh.py`, which supports the following CLI parameters.

| Parameter | Default | Description |
| -- | --- | --- |
| `-t` / `--hours-threshold-for-updates` | 24 | Threshold for how many hours since last update before we require refreshes. If last update time was less than this, nothing will happen. Will evaluate this separately for downloads of local artefacts as well as uploading data to the DB. |
| `-o` / `--objects` | False | Download objects. |
| `-c` / `--datasets-csets` | False | Download datasets from the "cset" group. |
| `-v` / `--datasets-vocab` | False | Download datasets from the "vocab" group |
| `-f` / `--force-download-if-exists` | True | If the dataset/object already exists as a local file, force a re-download. This is moot if the last update was done within --hours-threshold-for-updates. |
| `-l` / `--use-local-database` | False | Use local database instead of server. |

#### Allowing remote access
To allow a new user to access the database remotely, their IP address must be added to Azure: (i) select [DB resource](https://portal.azure.com/#@live.johnshopkins.edu/resource/subscriptions/fe24df19-d251-4821-9a6f-f037c93d7e47/resourceGroups/JH-POSTGRES-RG/providers/Microsoft.DBforPostgreSQL/flexibleServers/termhub/overview), (ii) [select 'Networking'](https://portal.azure.com/#@live.johnshopkins.edu/resource/subscriptions/fe24df19-d251-4821-9a6f-f037c93d7e47/resourceGroups/JH-POSTGRES-RG/providers/Microsoft.DBforPostgreSQL/flexibleServers/termhub/networking), (iii) add IP address.

#### Backups
**Prerequisites**  
You should have an environmental variable called `psql_conn`, set as follows:
`psql_conn="host=$TERMHUB_DB_HOST port=$TERMHUB_DB_PORT dbname=$TERMHUB_DB_DB user=$TERMHUB_DB_USER password=$TERMHUB_DB_PASS sslmode=require"`

If you run `./db_backup.sh`, it will generate commands (1) and (2) below so that you can directly copy/paste into the terminal to (i) create the backup, and (ii) restore it. The commands will look like this, except will replace `YYYYMMDD` with the current date:
**1. Create backup file**  
`pg_dump -d $psql_conn -n n3c | sed '/^[0-9][0-9]*\t/! s/[[:<:]]n3c[[:>:]]/n3c_backup_YYYYMMDD/' > n3c_backup_YYYYMMDD.dmp`

**2. Restore backup as schema `n3c_backup_YYYYMMDD`**  
`psql -d $psql_conn < n3c_backup_YYYYMMDD.dmp`

**3. Replace existing schema `n3c` with your restored backup**
You likely will already have a schema called `n3c` which is corrupted in some way, hence why you want to restore from backup.
3.1.a. Back up corrupted `n3c` schema: If you want to keep that schema for whateve reason, you can create a new backup for it as in step (1), or simply give it a new schema name:
`ALTER SCHEMA n3c RENAME TO <new name>;`

3.1.b. Drop up corrupted `n3c` schema: But there's a good chance you just want to drop it instead, like so:
`DROP n3c WITH CASCADE;`

3.2. Rename `n3c_backup_YYYYMMDD` as `n3c`:
`ALTER SCHEMA <backup schema name> RENAME TO n3c;`

#### Restoring from backup
1. Face check `n3c` schema
2. Restart local backend/frontend, load frontend in browser, clear `localStorage` (from console: `localStorage.clear()`), and face check various application features. 
3. Load [dev deployment](http://bit.ly/termhub-dev), clear `localStorage` in the same way, and face check various application features.

### Deployment
#### Deploying to Dev
Use the GitHub actions. Click these links for [backend](https://github.com/jhu-bids/TermHub/actions/workflows/backend_dev.yml) and [frontend](https://github.com/jhu-bids/TermHub/actions/workflows/frontend_dev.yml) actions, and then click "Run Workflow".
After both are deployed, test the app here: http://bit.ly/termhub-dev

#### Deploying to production
Use the GitHub actions. Click these links for [backend](https://github.com/jhu-bids/TermHub/actions/workflows/backend_prod.yml) and [frontend](https://github.com/jhu-bids/TermHub/actions/workflows/frontend_dprod.yml) actions, and then click "Run Workflow".
After both are deployed, the app app will be usable here: http://bit.ly/termhub

#### Rollbacks
If you notice something wrong with a deployment, follow these steps to roll back to the last stable deployment.
1. Go to the [GitHub actions](https://github.com/jhu-bids/TermHub/actions) page.
2. From the left sidebar, click the action that corresponds to the broken deployment (e.g. Backend dev, Frontend dev, Backend prod, or Frontend prod).
3. Find the workflow that you think produced the last stable deployment, and click it to open its logs.
4. If you're looking at a backend workflow, under the "Jobs" section of the left sidebar, select the job with the name "build". If you're looking at a frontend workflow, select the job with the name "Build and Deploy".
5. It will scroll you to the bottom of the logs page. Scroll to the top, and you should see a step called "Print commit hash & branch for rollbacks & troubleshooting". Click that.
6. You should now see the commit hash. Copy it.
7. In your terminal, run `git checkout <commit hash>`. This will checkout the code at the commit hash you copied.
8. Create a new branch & push it; for example, `git checkout -b rollback; git push -u origin rollback`.
9. Go to the [GitHub actions](https://github.com/jhu-bids/TermHub/actions) page.
10. From the left sidebar, click the action that corresponds to the broken deployment (e.g. Backend dev, Frontend dev, Backend prod, or Frontend prod).
11. Click the "Run workflow" button on the right, and in the popup that appears, where it says "Use workflow from", click the dropdown menu and select the branch you just created. Then, click "Run workflow". 

After the action finishes, your deployment should be rolled back to the last stable deployment.

You will also want to separately figure out what went wrong and fix it separately (i.e. in the `develop` branch), and make a new deployment again when things are stable and ready for a new release.

Note that for the _backend only_ instead of steps 2 - 4, you can also find the commit hash by going to the [deployments](https://github.com/jhu-bids/TermHub/deployments) page.

#### Logs
Logs for the backend can be opened via the following steps.
1. Log into https://portal.azure.com.
2. From the list of _Resources_, select the deployment. For production, its "Name" is "termhub" and its "Type" is "App Service". For development, its "Name" is "dev / (termhub/dev)", and its "Type" is "App Service (Slot)".
3. From the left sidebar, select "Advanced Tools" (unfortunately, none of "Logs", "App Service Logs", or "Log stream" are what you want).
4. Click "Go ->".
5. Click "Current Docker logs".
6. Find the log: A JSON list of log references will appear. Each log ref has an "href" field with a URL. It seems like there's always about a dozen or so refs. Unfortunately, there doesn't seem to be a way to tell which one is the one that we're usually going to want; that is, the one which will show things like stacktraces from server errors. You'll have to open each and scroll to the bottom until you find what you are looking for.   