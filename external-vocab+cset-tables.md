
#### Request to Amin for access to concept set and vocabulary tables from outside enclave

You (Amin) had suggested that rather than stand up an API for us to inject cset
data into the enclave from VSAC (etc.), you could sync with an external
PostgreSQL database. What we would need would be:

  - For read-only (download) we need up-to-date copies of the enclave's 
    concept and concept_relationship tables. 
  - For upload and download, copies of concept set container, version, and 
    concept set members tables. I don't know how you would want to do it,
    maybe not by two-way sync, but we could add new concept sets (with all the
    data that goes into the container, version, and items tables), and -- 
    eventually maybe -- update existing ones. But for now, let's not worry 
    about the update.
