## Developer docs
### [Frontend](../frontend/README.md)  
### [Backend](../backend/README.md)
### Database
#### Refreshing the database
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

### Deployment
#### Deploying to Dev
Use the GitHub actions. Click these links for [backend]([url](https://github.com/jhu-bids/TermHub/actions/workflows/backend_dev.yml)) and [frontend]([url](https://github.com/jhu-bids/TermHub/actions/workflows/frontend_dev.yml)) actions, and then click "Run Workflow".
After both are deployed, test the app here: http://bit.ly/termhub-dev

#### Deploying to production
Use the GitHub actions. Click these links for [backend]([url](https://github.com/jhu-bids/TermHub/actions/workflows/backend_prod.yml)) and [frontend]([url](https://github.com/jhu-bids/TermHub/actions/workflows/frontend_dprod.yml)) actions, and then click "Run Workflow".
After both are deployed, the app app will be usable here: http://bit.ly/termhub
