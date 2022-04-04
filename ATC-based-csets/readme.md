from [#43](/../../issues/43)
## Description
Harold has some ATC Concept Sets he wants to create in the enclave.

We need to map the ATC codes to RxNorm codes and use those as the concept set items.

## Additional info
### Useful links
- [ANTINEOPLASTIC AND IMMUNOMODULATING AGENTS
 in Atlas](https://atlas-demo.ohdsi.org/#/concept/21601386)
- [ATC Concept set hierarchy (WHO)](https://www.whocc.no/atc_ddd_index/?code=L01AA&showdescription=yes)

<br/>**siggie adding on 4.4.22 from [JHU Team Daily Morning Rolling Meeting Minutes](https://docs.google.com/document/d/1ojHRjh_IWItT4xul1z1XaHzDQPctOUCe/edit#):**

#### 3.22.22
ATC - Davera created Immuno compromised group concept sets and Scott Chapman created medication concept sets - may be 120? Or more concept sets.  

#### 3.11.22
- Status on work on ATC - 2 requests for medication
    - New medication concept set requests also from ISC
        - Paxlovid (0069-1085-30), 
        - EVUSHELD (0310-7442-02), 
        - molnupiravir (0006-5055-06),  
        - molnupiravir (0006-5055-07)  &nbsp;&nbsp;&nbsp;&nbsp;      **#  _added 3.22.22_**
    - [Ingredient-level Medication Concept Set Build SOP](https://docs.google.com/document/d/1SEAQO2eqFQ1JONkFVBCvh4YBM3FtYiHoQqwJP__iyMc/edit)
    - [Rest-API query for ingredients in an ATC Class (opioids)](https://rxnav.nlm.nih.gov/REST/rxclass/classMembers?classId=N02A&relaSource=ATC)

# Work to find these drugs and construct concept sets

Starting from Paxlovid (0069-1085-30), following instructions in [Ingredient-level Medication Concept Set Build
](https://docs.google.com/document/d/1SEAQO2eqFQ1JONkFVBCvh4YBM3FtYiHoQqwJP__iyMc/edit)

1) RxNav reported not being able to find [Paxlovid as string](https://mor.nlm.nih.gov/RxNav/search?searchBy=String&searchTerm=paxlovid). Tried [0069-1085-30 as NDC](https://mor.nlm.nih.gov/RxNav/search?searchBy=NDC&searchTerm=0069-1085-30) which retrieved {20 (nirmatrelvir 150 MG Oral Tablet) / 10 (ritonavir 100 MG Oral Tablet) } Pack [Paxlovid 5-Day] [RxCUI = 2587899]
2) Paxlovid apparently has two ingredients: nirmatrelvir [RxCUI = 2587892](https://mor.nlm.nih.gov/RxNav/search?searchBy=RXCUI&searchTerm=2587892) and ritonavir [RxCUI = 85762](https://mor.nlm.nih.gov/RxNav/search?searchBy=RXCUI&searchTerm=85762)
3) Searched for them using RxCUIs and also by ingredient name
    2) Couldn't find nirmatrelvir: by string [gives no results](https://atlas.ohdsi.org/#/search?query=nirmatrelvir); by RxCUI -- [2587892 in ATLAS search](https://atlas.ohdsi.org/#/search?query=2587892) does find one concept code, OMOP2587892, in RxNorm Extension, 40 ML Cefuroxime 39.5 MG/ML Injectable Solution Box of 25, which presumably has nothing to do with what we're looking for. Looking in RxNav, [nirmatrelvir](https://mor.nlm.nih.gov/RxNav/search?searchBy=RXCUI&searchTerm=2587892) seems to appear in no other drug except for the the Paxlovid 5-pack. [](https://atlas.ohdsi.org/#/search?query=2587899)
    3) Also searched ATLAS for the RxCUI of the Paxlovid 5-pack [2587899](https://atlas.ohdsi.org/#/search?query=2587899) and only got an RxNorm Extension code for [40 ML Penicillin G 7.18 MG/ML Oral Solution [Tardocillin]](https://atlas.ohdsi.org/#/concept/41389937), presumably irrelevant.
    1) Did find [ritonavir in ATLAS](https://atlas.ohdsi.org/#/concept/1748921) (both by name and RxCUI). It has 85 children and is an ingredient in 34 drugs, but I couldn't even find it appearing in any 5-packs, much less with a name like paxlovid or a co-ingredient like nirmatrelvir.

Conclusion for Paxlovid: no ATC-based concept sets will be possible because Paxlovid itself belongs to no ATC classes except through ritonavir, and, though ritonavir belongs to 26 classes, it is not itself a class. And the rest are also individual drugs (with NDC codes), so, now I realize this was a ridiculous exercise because probably none of these will be ATC classes.



