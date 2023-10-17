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
