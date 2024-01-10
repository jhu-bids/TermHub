
## Commits of interest

### _[eb27fa7](https://github.com/jhu-bids/TermHub/commit/eb27fa7)_ 2023-05-16
First appearance of graph.py. Not sure if there's important stuff to look at
before this.


### _[7c6b78b](https://github.com/jhu-bids/TermHub/commit/7c6b78b)_ 2023-06-26
Working on caching. Maybe no substantive change since 05-16, but graph.py is
stable. Apparently no change in algorithm until 11-13.


### _[9f6f82b](https://github.com/jhu-bids/TermHub/commit/9f6f82b)_ 2023-11-13
From commit message:
  - Totally redid subgraph generation and now downloading indented concept
    list instead of constructing it on the front end based on creating a
    front-end graph based on subgraph edges from backend. Seems to work,
    but collapse is broken now...maybe other stuff too.
  - No longer need an undirected version of the graph
  - Expanded to include all 'Is a' relationships from `concept_relationship`
    table in addition to `concept_ancestor` where min separation = 1 already
    included. [switched back at some later time]


### _[89863ba9](https://github.com/jhu-bids/TermHub/commit/89863ba9)_


### _[29ce57d](https://github.com/jhu-bids/TermHub/commit/29ce57d)_
  - Base case for tst_graph


## Test cases

[MALIGNANT CANCER](http://localhost:3000/cset-comparison?codeset_ids=585389357&codeset_ids=1000003793)
  - 585389357 v2.0, vocab v5.0 09-APR-22; 1469846 pts, **53510** concepts, flags: D: 1, DX: 5
  - 1000003793 v1.0, vocab v5.0 31-AUG-23; 0 pts, 53993 concepts, flags: D: 1, DX: 5
  - 53K concepts
  - 9f6f82bf: hoses server
