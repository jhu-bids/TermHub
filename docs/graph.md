# Documentation about vocabulary hierarchy algorithms and display
## 2024-01-03 update
The code for filling in gaps in concept subgraphs and displaying them as trees has never worked quite right -- though it usually is or seems right enough for people not to notice. But there have been a wide variety of edge cases like
- The gaps aren't filled in correctly
- Unneeded ancestors are added
- The subgraph gap-filling or backend tree construction takes so long that it hangs
- There's so many indented tree nodes that the browser slows to a crawl or crashes

I'm realizing again that there are problems in the algorithm, so I'm going to use this space to try to plan out and document a new algorithm. This will be based on [graph testing](./graph_testing.md)

### Steps
1. Find all roots of subgraph (...)


## Graph visualization
I'd like to make a few test cases that include all the various edge cases that have to be handled. At least one small one that can be manually tinkered with and easy to understand and some big ones made with real data for testing front/back end performance and manageability and summarization features (collapsing many nodes into an expandable summary node.)

I would like to be able to use [graphviz and dot](https://graphviz.org/) for authoring and graphically rendering the small use cases, but it has a weird architecture. It has APIs, declarative language, CLIs, and stuff; but they rely on [executables](https://graphviz.org/download/) which are environment-specific. (See stack overflow for [how to handle azure](https://stackoverflow.com/questions/76244214/how-to-fix-pygraphviz-program-dot-not-found-in-path-error-in-azure-or-gcp).)

![graph examples](./graph-examples/graph-example-simple.svg)
![graph examples](./graph-examples/graph-example-common-ancestor-roots.svg)
![graph examples](./graph-examples/graph-example-common-ancestor-nodes.svg)

## Old
This is to answer @joeflack4's questions on https://github.com/jhu-bids/TermHub/pull/611 and will also
be useful for documenting future work on managing vocabulary data and display, which will get complex
when we start breaking it down into smaller pieces. See [issue 611](https://github.com/jhu-bids/TermHub/pull/611)
and [octopus notes](https://github.com/trberg/Octopus/blob/master/Notes.md#oct-6-2023----requirements-for-multiple-concept-set-display-and-dynamic-subtree-summarization-and-loading) (also pasted in below.)

## Explanation of new concept hierarchy algorithm
[Code is here](https://github.com/jhu-bids/TermHub/blob/fixing-concept-hierarchy/backend/routes/graph.py#L43C1-L137C1)

As an example, we can look at the first 12 lines of [this concept set comparison](https://icy-ground-0416a040f.2.azurestaticapps.net/cset-comparison?codeset_ids=817711041&codeset_ids=1000020459):
![image](https://github.com/jhu-bids/TermHub/assets/1586931/d16733a0-a7e1-449b-a703-d060f13367e3)


call `all_paths`, which finds all simple paths from every root node (no parents) to every leaf node (no children);
the first four rows of its return account for the indented concept list shown above.

    [37312530, 761858]
    [37312530, 36712805, 35611566]
    [37312530, 36712807, 35611566]
    [321052, 3654996, 37110250, 46271459, 761430, 761858]

But rather than return those full paths, we call `paths_as_indented_tree(paths)`, which converts the paths
to this simpler structure for easy tabular display:

    (0, 37312530)
    (1, 761858)
    (1, 36712805)
    (2, 35611566)
    (1, 36712807)
    (2, 35611566)
    (0, 321052)
    (1, 3654996)
    (2, 37110250)
    (3, 46271459)
    (4, 761430)
    (5, 761858)
    (5, 761431)

## Eventual goals for vocabulary / concept set display and data management

Oct 6, 2023
1. Moving towards controlling data collapse/fetch from our own data module
   instead of operating on the d3-dag data structure
2. Talking through data and display ideas
3. For multiple concept sets, show the list, and when you hover over
   a node, highlight the concept sets that contain it.
4. Have check boxes for each concept set and highlight all the nodes that
   are contained by all the ones checked (partial highlight if not all
   descendants are contained.)
5. If a node has x (10?) or more children, try to keep it collapsed, but allow
   user to see what's in it: 1) by size/color; 2) with a list that appears on
   hover or click;
6. Showing a lot with each node: 
   - number of children
   - whether all or some children/descendants belong to concept sets
   - how deep it goes
   - easy access to names of children
7. What about multiple relationship types? Mapping, body site, causes, etc.
   - Could show collapsed nodes as children, one for each relationship type
8. If user has a lot of nodes displayed (and many more in memory), and tries
   to expand something big: prompt them to collapse something else?
   - Maybe it's temporary message for a few seconds: "You're displaying a lot of
     nodes. The application may become slow. Do you want to collapse something else?"
   - Or message, how many nodes in memory and displayed.
   - And how many descendants/levels
9. Server should provide number of descendants/levels for nodes first
   and then provide the actual nodes for them either on demand or, if
   resources available, on prefetch
10.Slider for the user to balance between performance and data density
