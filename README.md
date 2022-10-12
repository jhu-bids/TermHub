# TermHub

## [Features under development / consideration](https://docs.google.com/spreadsheets/d/19_eBv0MIBWPcXMTw3JJdcfPoEFhns93F-TKdODW27B8/edit#gid=0)
More info: [Requirements](https://github.com/jhu-bids/TermHub/issues/72)

### Vocabulary management (a single concept, subsets of or an entire vocabulary)
The simple concept vocabulary mapping, SNOMED, etc.

### One concept set (cset)
A grouping of vocabularies (single concepts) that make up a particular value set. This entails user-based tagging. 

(Siggie?) The vocabulary that deals with just concept IDs and terminologies but also there is a part that deals with presence of these terminologies within your data source. 

Description of API needed outside enclave in order to do cset analysis:
(see Siggie's spreadsheet: https://roamresearch.com/#/app/jhu-bids/page/RsLm1drBI)

### multiple csets
--includes single cset to a revised single cset (version compare)
--similar/related csets
--combination of csets

managing multiple csets may include single cset comparisons, either one cset compared to another, or a single cset version comparison. It can include neighborhods or similar, related csets. Or, it can be a combination of csets for a broader category.

### Documentation and associated metadata
Source, Limitations, Intention

Identifying/labeling sets of csets: 
--bundles, 
--approved
--reviewed 
--published 
--externally curated, etc.

### Neighborhood analysis
Documentation and visualization;
reviewing, understanding, what is in the sets

Identifying neighborhoods
--what is similar/different
-- properties (articulating why they are different)
User Interactions
--select, relabel, groupings, 

### Review Process of cset(s)

### Validation
(is this the same as Review? maybe not)

### Choosing concept sets for Logic Liaison templates

### Archiving

### Editing Concepts & Concept Sets

## Developer docs
- [Frontend](./frontend/README.md)  
- [Backend](./backend/README.md)

Setup
1. Clone this repository.
2. Run `git submodule update`
3. Run: `git lfs install` if not installed already
4. If any expected files are not showing up in `termhub-csets/`, run `git lfs pull`
