# Understanding the call graph
How code is called in certain parts of the backend

### [refresh.py](../backend/db/refresh.py)
- [refresh.py(): refresh_db](../backend/db/refresh.py#L28-L65)
  - [`update_db_status_var('last_refresh_request', t0_str, local)`](../backend/db/utils.py#L152)
  - ...
  - [csets_and_members_enclave_to_db()](../../enclave_wrangler/objects_api.py#L291)

 
