# ValueSet Tools
Tools for converting value sets in different formats, such as converting 
extensional value sets in CSV format to JSON format able to be uploaded to a 
FHIR server. Tools to automate CRUD operations such as reads and updates from various different data sources and web services.

## Set up / installation
1. You must have [Python3](https://www.python.org/downloads/) installed.
2. Run to clone repo: `git https://github.com/HOT-Ecosystem/ValueSet-Tools.git`
3. Change directory: `cd ValueSet-Converters`
4. Make & use virtual environment: `virtualenv env; source env/bin/activate`
5. Run to install dependencies: `pip install -r requirements.txt` 
6. To use the "VSAC to OMOP/FHIR JSON" tool, which fetches from Google Sheets, 
   you'll need the following:  
   3.a. Access to [this 
   google sheet](https://docs.google.com/spreadsheets/d/1jzGrVELQz5L4B_-DqPflPIcpBaTfJOUTrVJT5nS_j18/edit#gid=1335629675).  
   3.b. Place `credentials.json` and `token.json` inside the `env/` directory. 
   For [BIDS](http://dhsi.med.jhmi.edu/) members, these can be downloaded from the BIDS OneDrive [here](https://livejohnshopkins-my.sharepoint.com/personal/jflack1_jh_edu/_layouts/15/onedrive.aspx?id=%2Fsites%2FBiomedicalInformaticsandDataScience%2FShared%20Documents%2FProjects%2FCD2H%2C%20N3C%2C%20PASC%2FValueSet%20Tools%2Fenv&listurl=https%3A%2F%2Flivejohnshopkins%2Esharepoint%2Ecom%2Fsites%2FBiomedicalInformaticsandDataScience%2FShared%20Documents&viewid=51daccc9%2D8479%2D4ef4%2Da7bf%2D65b689881f3a).
7. Create an `env/.env` file based on `env/.env.example`, replacing `VSAC_API_KEY` 
   with your own [VSAC API key](https://uts.nlm.nih.gov/uts/edit-profile) as 
   shown in your profile. More instructions on getting an API key can be found in 
   ["Step 1" on this page](https://documentation.uts.nlm.nih.gov/rest/authentication.html).
   Or, if you are a BIDS member, you can simply download and use the `.env` file
   [from the BIDS OneDrive](https://livejohnshopkins.sharepoint.com/:f:/r/sites/BiomedicalInformaticsandDataScience/Shared%20Documents/Projects/CD2H,%20N3C,%20PASC/ValueSet%20Tools/env?csf=1&web=1&e=f2iR9S) ([mirror link](https://livejohnshopkins.sharepoint.com/sites/BiomedicalInformaticsandDataScience/Shared%20Documents/Forms/AllItems.aspx?OR=Teams%2DHL&CT=1643222213761&sourceId=&params=%7B%22AppName%22%3A%22Teams%2DDesktop%22%2C%22AppVersion%22%3A%2228%2F21110108720%22%7D&id=%2Fsites%2FBiomedicalInformaticsandDataScience%2FShared%20Documents%2FProjects%2FCD2H%2C%20N3C%2C%20PASC%2FValueSet%20Tools%2Fenv&viewid=51daccc9%2D8479%2D4ef4%2Da7bf%2D65b689881f3a)).
   It already has an API key from the shared UMLS BIDS account pre-populated.

## Tools
First, `cd` into the directory where this repository was cloned.

### 1. VSAC Wrangler
This will fetch OIDs from the "OID" column of [this google sheet](https://docs.google.com/spreadsheets/d/1jzGrVELQz5L4B_-DqPflPIcpBaTfJOUTrVJT5nS_j18/edit#gid=1335629675), make VSAC API calls, and produce output.

#### Syntax
`python3 -m vsac_wrangler <options>`

Options:

|Short flag | Long flag | Choices | Default | Description |
|---	|---	|---	|--- | --- |
| `-i` | `--input-source-type` |`['google-sheet', 'txt', 'csv']` | `'csv'` | If (a) "google-sheet", this will fetch from a specific, hard-coded GoogleSheet URL, and pull OIDs from a specific hard-codeed column in that sheet. You may also want to specify the `--google-sheet-name`. If (b) "txt", or (c) "csv", please supply an `--input-path`. In case of "txt", it is expected that each line of the file contains an OID and nothing else. In case of "csv", it is expected that there be an "oid" column. |
| `-p` | `--input-path` | | | Path to input file. Required if `--input-source-type` is "txt" or "csv". |
| `-g` | `--google-sheet-name` |`['CDC reference table list', 'VSAC Lisa1']` | `'CDC reference table list'` | The name of the tab within a the GoogleSheet containing the target data within OID column. Make sure to encapsulate the text in quotes, e.g. `-g "Lisa1 VSAC"`. This option can only be used if `--input-source-type` is `google-sheet`. |
| `-o` | `--output-structure` |`['fhir', 'vsac', 'palantir-concept-set-tables', 'atlas', 'normalized']` | `'normalized'` | Destination structure. This determines the specific fields, in some cases, internal structure of the data in those fields. About structures: (a) "fhir" is intended to be uploaded to a FHIR server, (b) "vsac" retains similar struture/fields as VSAC data model, (c) "palantir-concept-set-tables" produces CSV files that can be bulk uploaded / appended in the N3C Palantir Foundry data enclave, (d) "atlas" produces a JSON format adherent to the Atlas DB data model, and (e) "normalized" creates a data structure that is normalized as much as possible, containing minimal amount of information / structure needed. |
| `-f` | `--output-format` |`['tabular/csv', 'json']` | `'json'` | The output format. If csv/tabular, it will produce a tabular file; CSV by default. This can be changed to TSV by passing "\t" as the field-delimiter. |
| `-d` | `--tabular-field-delimiter` |`[',', '\t']` | `','` | Field delimiter for tabular output. This applies when selecting "tabular/csv" for "output-format". By default, uses ",", which menas that the output will be CSV (Comma-Separated Values). If "\t" is chosen, output will be TSV (Tab-Separated Values). |
| `-d2` | `--tabular-intra-field-delimiter` | <code>[',', '\t', ';', '&#124;']</code> | <code>&#124;</code> | Intra-field delimiter for tabular output. This applies when selecting "tabular/csv" for "output-format". This delimiter will be used when a specific field contains multiple values. For example, in "tabular/csv" format, there will be 1 row per combination of OID (Object ID) + code system. A single OID represents a single value set, which can have codes from multiple code systems. For a given OID+CodeSystem combo, there will likely be multiple codes in the "code" field. These codes will be delimited using the "intra-field delimiter". |
| `-j` | `--json-indent` | 0 - 4 | 4 | The number of spacees to indent when outputting JSON. If 0, there will not only be no indent, but there will also be no whitespace. 0 is useful for minimal file size. 2 and 4 tend to be  standard indent values for readability. |
| `-c` | `--use-cache` | | | When running this tool, a cache of the results from the VSAC API will always be saved. If this flag is passed, the cached results will be used instead of calling the API. This is useful for (i) working offline, or (ii) speeding up processing. In order to not use the cache and get the most up-to-date results (both from (i) the OIDs present in the Google Sheet, and (ii) results from VSAC), simply run the tool without this flag. |
| `-h` | `--help` | | | Shows help information for using the tool. |

#### Examples
##### 1. Create a TSV with comma-delimited VSAC codes, and use the last cached results from the VSAC API.
`python -m vsac_wrangler -o vsac -f tabular/csv -d \t -d2 , -c`

### 2. Enclave Wrangler
Tool for working w/ the Palantir Foundry enclave API. Some documentation for the API endpoints involved can be found: [here](https://github.com/National-COVID-Cohort-Collaborative/Data-Ingestion-and-Harmonization/wiki/BulkImportConceptSet-REST-APIs).

#### Syntax
`python3 -m enclave_wrangler <options>`

Options:

|Short flag | Long flag | Choices | Default | Description |
|---	|---	|---	|--- | --- |
| `-i` | `--input-csv-folder-path` | | | Path to folder with 3 files that have specific columns that adhere to concept table data model. These files must have the following names: i. code_sets.csv, ii. concept_set_container_edited.csv, iii. concept_set_version_item_rv_edited.csv |
| `-h` | `--help` |  | | Shows help information for using the tool. |

### 3. CSV to FHIR JSON 
Tool for converting extensional value sets in CSV format to JSON format able to 
be uploaded to a FHIR server.

#### Syntax
`python3 -m csv_to_fhir <options>`

|Short flag | Long flag | Choices | Default | Description |
|---	|---	|---	|--- | --- |
| `-p` | `--input-file-path` | | | Path to CSV file(s). If `--input-schema-format` is "palantir-concept-set-tables", should pass 2 CSV paths, in any order, e.g. `-p code_sets.csv concept_set_version_item_rv_edited.csv`. |
| `-f` | `--input-schema-format` | `['palantir-concept-set-tables']` | `'palantir-concept-set-tables'` | The schema format of the CSV. Corresponds to the expected fields/column names. |
| `-o` | `--output-json` | | | If this flag is present, or if both this flag and `--upload-url` are absent, converted JSON will be saved in the directory where CLI is called from. |
| `-u` | `--upload-url` | | | If present, will upload value sets ValueSet resource at specified endpoint (e.g. http://localhost:8080/fhir/ValueSet) or server (e.g. http://localhost:8080). |
| `-j` | `--json-indent` | 0 - 4 | 4 | The number of spacees to indent when outputting JSON. If 0, there will not only be no indent, but there will also be no whitespace. 0 is useful for minimal file size. 2 and 4 tend to be  standard indent values for readability. |
| `-h` | `--help` |  | | Shows help information for using the tool. |

#### Examples
##### Example 1
`python3 -m csv_to_fhir -o -u http://localhost:8080 -p output/concept_set_version_item_rv_edited/2022.02.04/concept_set_version_item_rv_edited.csv`

##### Example 2
`python3 -m csv_to_fhir -p examples/1/input/n3cLikeExtensionalValueSetExample.csv`

##### TODO: Need to update this to palantir version of columns:
Before:
```csv
valueSet.id,valueSet.name,valueSet.description,valueSet.status,valueSet.codeSystem,valueSet.codeSystemVersion,concept.code,concept.display
1,bear family,A family of bears.,draft,http://loinc.org,2.36,1234,mama bear
1,bear family,A family of bears.,draft,http://loinc.org,2.36,1235,papa bear
1,bear family,A family of bears.,draft,http://loinc.org,2.36,1236,baby bear
```

After:
```json
{
    "resourceType": "ValueSet",
    "id": 1,
    "meta": {
        "profile": [
            "http://hl7.org/fhir/StructureDefinition/shareablevalueset"
        ]
    },
    "text": {
        "status": "generated",
        "div": "<div xmlns=\"http://www.w3.org/1999/xhtml\">\n\t\t\t<p>A family of bears.</p>\n\t\t</div>"
    },
    "name": "bear family",
    "title": "bear family",
    "status": "draft",
    "description": "A family of bears.",
    "compose": {
        "include": [
            {
                "system": "http://loinc.org",
                "version": 2.36,
                "concept": [
                    {
                        "code": 1234,
                        "display": "mama bear"
                    },
                    {
                        "code": 1235,
                        "display": "papa bear"
                    },
                    {
                        "code": 1236,
                        "display": "baby bear"
                    }
                ]
            }
        ]
    }
}
```