
## Commits of interest

### [eb27fa7](https://github.com/jhu-bids/TermHub/commit/eb27fa7) 2023-05-16
First appearance of graph.py. Not sure if there's important stuff to look at
before this.


### [7c6b78b](https://github.com/jhu-bids/TermHub/commit/7c6b78b) 2023-06-26
Working on caching. Maybe no substantive change since 05-16, but graph.py is
stable. Apparently no change in algorithm until 11-13.


### [9f6f82b](https://github.com/jhu-bids/TermHub/commit/9f6f82b) 2023-11-13

From commit message:
  - Expanded to include all 'Is a' relationships from concept_relationship
    table in addition to concept_ancestor where min separation = 1 already
    included.
  - No longer need an undirected version of the graph
  - Totally redid subgraph generation and now downloading indented concept
    list instead of constructing it on the front end based on creating a
    front-end graph based on subgraph edges from backend. Seems to work,
    but collapse is broken now...maybe other stuff too.


### [89863ba9](https://github.com/jhu-bids/TermHub/commit/89863ba9)
