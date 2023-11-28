# Frontend testing documentation

## Performance testing
- Implements strategies described in [issue #514](/../../issues/514)

### "Experiments"
Values that can be specified while running tests and can be passed to TermHub querystring to control
what optimization is being performed and tested. Can take multiple values delimited by tilde (`~`).

| experiment name     | description                                          | implemented | tested |
|---------------------|------------------------------------------------------|:------------:|:--------:|
| `as-is` or no value | Use code without attempting any special optimization |   yes  | yes |
| `no-cache`          | Disables caching -- in DataCache.cachePut            |   yes  | yes |
| `no-rxext-from-api` | RxNorm Extension codes left out of backend API results. See [below](#no-rxnorm-extension-codes)|   no   | no  |


## Notes

### No RxNorm Extension codes
1.  This could be implemented by excluding these codes from `concept_set_members`, `concept_set_version_item`,
    and maybe even `concept`, `concept_relationship`, and `concept_ancestor` and all downstream derived tables.
    But that would make it impossible to tell user how many RxNorm Extension codes have been omitted.


2.  It could be done by eliminating the codes as a last step of each api call that returns `concept_id`s,
    but that would actually increase api processing time and only save time/memory in the frontend
    receiving and processing results.

3.  What I'm going to try is #1, but into a special schema (n3c_no_rxnorm), just to see how much it helps
    with the antibiotics test, which currently crashes.
