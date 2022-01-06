# ValueSet Converters
Tools for converting value sets in different formats. Such as converting 
extensional value sets in CSV format to JSON format able to be uploaded to a 
FHIR server.

## Set up / installation
1. You must have [Python3](https://www.python.org/downloads/) installed.
2. `git clone https://github.com/HOT-Ecosystem/ValueSet-Converters.git`
3. To use the "VSAC to OMOP/FHIR JSON" tool, which fetches from Google Sheets, 
   you'll need the following:  
   3.a. Access to [this 
   google sheet](https://docs.google.com/spreadsheets/d/1jzGrVELQz5L4B_-DqPflPIcpBaTfJOUTrVJT5nS_j18/edit#gid=1335629675).  
   3.b. Place `credentials.json` and `token.json` inside the `env/` directory. 
   These can be obtained from Joe (will upload them to a Google Drive folder 
   later).
4. Create an `env/.env` file based on `env/.env.example`, replacing `VSAC_API_KEY` 
   with your own [VSAC API key](https://uts.nlm.nih.gov/uts/edit-profile) as 
   shown in your profile. More instructions on getting an API key can be found in 
   ["Step 1" on this page](https://documentation.uts.nlm.nih.gov/rest/authentication.html).

## Tools
First, `cd` into the directory where this repository was cloned.

### 1. CSV to FHIR JSON 
First, convert your CSV to have column names like the example below. Then can 
run these commands.
#### Syntax
`python3 -m value_set_csv_to_fhir_json path/to/FILE.csv`

#### Example
`python3 -m value_set_csv_to_fhir_json examples/1/input/n3cLikeExtensionalValueSetExample.csv`

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

### 2. VSAC to OMOP/FHIR JSON
This will fetch from the following google sheet:
https://docs.google.com/spreadsheets/d/1jzGrVELQz5L4B_-DqPflPIcpBaTfJOUTrVJT5nS_j18/edit#gid=1335629675

#### Syntax
- With default options: `python3 -m value_set_vsac_to_json`
- Choosing an output format: `python3 -m value_set_vsac_to_json -f omop`

Options:

|Short flag | Long flag | Options | Default | Description|
|---	|---	|---	|---	|---	|
| `-f` | `--format` | `['omop', 'fhir']` | 'omop' | Output format. |
