# Database refreshing
## Core (concept set) tables (`code_sets`, `concept_set_container`, `concept_set_version_item`, `concept_set_members`)
There are several database refreshes, which synchronize TermHub with its data source, the N3C data enclave. The most 
important of these is for the concept set tables. After these tables are synchronized, any dependent tables or views 
are also regenerated.

A refresh is done every 20 minutes via [GitHub action](
https://github.com/jhu-bids/TermHub/actions/workflows/db_refresh.yml), 
but this can also be run manually, either by (a) using the [GitHub action](https://github.com/jhu-bids/TermHub/actions/workflows/db_refresh.yml), or (b) running the Python script 
manually via `python backend/db/refresh.py`.

The refresh will check for anything since the last time it successfully ran, but you can also set your own date to 
fetch from using the `--since` param or fetch specific csets via `--csets-ids`.

There is also a second refresh for these tables that also runs every 20 minutes, specifically an [action for draft 
finalization](https://github.com/jhu-bids/TermHub/actions/workflows/resolve_fetch_failures_0_members.yml). It is called 
"Resolve fetch failures: New csets w/ 0 members".

To see when this refresh was last successfully run, consult the `last_refresh_success` variable in the `manage` table. 
There are also several other useful variables there, such as `last_intialized_DB` (the last time it was 
initialized from scratch), `last_refresh_result` ("success" or "error"), and `last_refresh_error`. Another way to see 
the datetime of the last successful run, you can open up VS-Hub and look at the console; it prints this on app 
initialization. 

## Counts tables
Patient and record counts are updated in the N3C data enclave routinely, typically every few weeks or months. There is 
a [GitHub action](https://github.com/jhu-bids/TermHub/actions/workflows/refresh_counts.yml) that checks nightly for 
any changes and updates if so.

This refresh updates the `concept_set_counts_clamped` and `deidentified_term_usage_by_domain_clamped` tables, as well 
as their derived tables and views.

This can also be run manually via `make refresh-counts`, or `python backend/db/refresh_dataset_group_tables.py 
--dataset-group counts`.

To see when this refresh was last successfully run, consult the `last_refreshed_counts_tables` variable in the `manage` 
table.

## Vocabulary tables
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

To see when this refresh was last successfully run, consult the `last_refreshed_vocab_tables` variable in the `manage` 
table.

## Standard Operating Procedure (SOP) for vocabulary refresh
Every 6 months or so, whenever the vocab tables are updated:
1. Run the vocab refresh locally.
2. Go to https://portal.azure.com/ and restart the TermHub server(s).
3. After 15 minutes or so, face check the app in the browser to make sure it's working.
4. It's also a good idea to run the frontend [Playwright E2E tests](https://github.com/jhu-bids/termhub/actions), 
though these do run nightly.

## Monitoring
Failed GitHub actions will result in an email sent to termhub-support@jh.edu. They will link to a log for a specific run
of actions in https://github.com/jhu-bids/termhub/actions. Since development has halted as of 2025/01, these failures 
have hitherto been completely out of our control. However, they have all resolved on their own after some time (days, 
hours, or in most cases by the very next refresh 20 minutes later). Therefore, if you observe errors showing up, the 
best thing to do is ignore them unless they are still failing, i.e. they have failed multiple times, and the last time 
they ran (within the last 20 minutes) was also a failure. A list of failures out of our control that we have previously 
observed can be found in [refresh_failure_history.md](refresh_failure_history.md). 
