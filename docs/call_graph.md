# Understanding the call graph
How code is called in certain parts of the backend
Most of the links don't work in pycharm but they work when used in GitHub.

### [refresh.py](../backend/db/refresh.py)
- [refresh.py()](../backend/db/refresh.py#L28-L65)
  - [`update_db_status_var('last_refresh_request', t0_str, local)`](../backend/db/utils.py#L152)
  - ...
  - [all_new_objects_enclave_to_db()](../enclave_wrangler/objects_api.py#L284)
    - not yet ready, current using [csets_and_members_enclave_to_db()](../enclave_wrangler/objects_api.py#L291)
  -[`counts_update('DB refresh.', schema, local)`](../backend/db/analysis.py#L134)
  - ... update documentation, error handling.

### [initialize.py](../backend/db/initialize.py)
- [initialize()](../backend/db/initialize.py#L55-L77)
  - ```
    if test_schema_only:
        return initialize_test_schema(con, schema, local=local)
    ```
    [initialize_test_schema()](../backend/db/load.py#L66-113)
    - [`run_sql(con_initial, f'CREATE SCHEMA IF NOT EXISTS {test_schema};')`](../backend/db/load.py#72)
    - ... creating a schema with concepts and code_sets
    - ends the function
  - ```
    if create_db:
      # Apparently this caused an error the last time on a fresh DB, but didn't write down why.
      create_database(con, schema)
    ```
    [create_database()](../backend/db/initialize.py#L26-56)
    - [database_exists()](../backend/db/utils.py#L161-165) returns boolean
    - ... creates an empty schema
  - ```
    if download:
        download_artefacts(force_download_if_exists=download_force_if_exists)
    ```
    [download_artefacts()](../backend/db/load.py#L56-63)
    - [download_favorite_datasets()](../enclave_wrangler/datasets.py#386-396)
      - selects data sets that are part of the favorite dataset ordered dictionary
        [FAVORITE_DATASETS](../enclave_wrangler/config.py#75-165)
    - downloads csets, objects, vocab
  - [indexes_and_derived_tables()](../backend/db/load.py#L136-193)
    - uses SQL querys to create indices and derived tables :)
  - [initialize_test_schema()](../backend/db/load.py#L66-113)
    - [`run_sql(con_initial, f'CREATE SCHEMA IF NOT EXISTS {test_schema};')`](../backend/db/load.py#72)
    - ... creating a schema with concepts and code_sets



### [dataset.py](../enclave_wrangler/datasets.py)
