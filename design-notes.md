
# Term Hub 
*(name already used, ideas for new one below)*

### Chris idea: Do it all on GitHub. 

With GitHub apps and an additional local web application, it just might work.

#### Motivations and approach

Many of our pipeline and analytic jobs may need repeating, and definitely need
reliable, usable documentation. Affordances for these functions exist in the
enclave, but 

1) at the cost of isolation from external APIs and resources, and 
2) with a very limited set of development tools that are very slow to code in 
   (even after ascending their considerable learning curve.) 

In order to start bringing VSAC and HCUP value sets into the enclave, we have
needed to build tools outside the enclave to extract and transform them and use
Palantir APIs from outside the enclave to push them into the concept set tables
inside the enclave.

We will focus on our current use case:

###### Fetch a set of OIDs from VSAC and push them to the enclave

We have written *somewhat* automated processes for this task and have
executed them a few times. Each time through, we improve the code and
repeatability of the task and the automation of validating and documenting
it, but we need a more robust application rather than a collection of 
command-line tools.

Current steps:

  1. Identify authoritative value sets
      has OIDs? yes/no
  2. Put them in spreadsheet with metadata and OIDs
    a) Different for HCUP
    b) Will also be different for ATC medication sets
  3. Tell programmer type to load them into the enclave
      (continue from POV of programmer type)
  4. Programmer gets OIDs, two ways to do it now, choose favorite
    1. With OIDs copied from wherever to CSV
    2. Or software grabs directly from spreadsheet
  5. Set parameters for VSAC fetch: tell it where to get OIDs and where
      to put palantir-three-file CSVs
  6. Run VSAC fetch, sanity check
  7. Set parameter for enclave import to say where to find the 3 files
  8. Run that
  9. Some automated processes occur on the enclave. Stephanie wrote some of
      these, others, maybe Amin; we don't know what they all are
  10. Tell Stephanie to tell Amin that we did it.
  11. Amin does some special thing
  12. Siggie then tries to figure out which concept sets were actually
      just loaded, and copies that data back out of the enclave in order
      to run validation and find concept sets and concept codes that
      *should* have made it into the enclave but didn't. (And sometimes
      it seems that more makes it into the enclave than should.)
  13. Generate report and share with team of missing codes and csets
  14. Now it's Lisa's problem
  15. Lisa sanity checks, does something, who knows what?
  16. Once satisfied, Lisa changes them all from DRAFT to new versions
  17. Tell whoever is interested that we're done


  - Prior to these operations, work is done to decide what should be
    retrieved and transfered and why. Perhaps we would like to capture
    documentation of those processes, but for now consider them out of scope.


##### What the steps *should* be:

  - Use structured form to specify and document new `transfer operation`.
    Collect:
    - Label, description, purpose
    - Source data (and where did source data come from)
    - Which APIs or methods to retrieve or construct value sets
    - Transformations necessary
      - Descendants? Mapping? Adding of metadata? Etc.
    - Specification of API or methods to be used to push the value sets 
      (in this case to the enclave)

[not finished]
  


  

  
- will store structure record of the job & metadata
- will launch VSAC extract
- will store raw VSAC response to data folder for each valve set
- push to enclave, w/ record of what was pushed
- pull from enclave to validate and provide additional metadata



- How to deal WI big files?  
  - git LFS -- $5/50GB, not bad

- csets each have their own directory?
  - do cset member codes go in cset dir? or common file?

- Sync for faster analysis between git & postgres? and HAPI? 

- Would an interface access git files on the user's filesystem ~or on GitHub?~
- Interface could be web app with server on user's machine, implement in node or Flask
  - start small, local web server
  - get latest charges (if on ma#
→
  - Use special branch for data? or keep data in directories?
or in a separate repo, possibly yes"%
sub Anodvle?-
    - spot-on data changes
for foreseeable future real-time
won't matter
    - So, we'll have the GitHub online
interface but also a
local web interface That rung
fast on local data


## ideas for names

**Terminology Central**

| letters for acronym | words                                                |
| ------------------- | ---------------------------------------------------- |
| TRASH-Collector     | Terminology Resources Archive Semantic Hub Collector |
| SI                  | Semantic Information                                 |
| MASI                | Manage and Analyze Semantic Information              |
| ASSIST              | Analytic System of Semantic Information Storing T    |
| SIM                 | Semantic Information Management                      |
| SIT                 | Semantic Information Tracker                         |
| SIA                 | Semantic Information Archive                         |
| ETL,ELT             | Extract Load Transform                               |
| TH                  | Transformation Hub                                   |
| RC, RA, RR          | Replayable Chronicle/Archive/Record                  |
| CTS                 | Clinical Terminology Server                          |
| TH                  | Terminology Hub                                      |
| TSH                 | Terminology Services Hub                             |

### Other words
- Terminology, Value Set, Mapping, Archive, Administration, Analysis, Extracting,
  VSAC, Import, Ontologies, Automation, Replayable, vocabulary, tracker,
  Semantic Resources, Validation, Reconciliation, Job execution, Workflow, Git,
  Diff, Replayable, Chronicle, Journal, Register, Record, Archive,
  Clinical Terminology, Server, Hub, Value set, Concept set, Code set, Mapping,

