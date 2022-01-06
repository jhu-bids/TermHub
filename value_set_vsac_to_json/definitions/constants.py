"""Constants"""
from typing import Any, Dict


FHIR_JSON_TEMPLATE: Dict[str, Any] = {
    "resourceType": "ValueSet",  # not defined in http://hl7.org/fhir/valueset.html
    "id": "TO_FILL",  # not defined in http://hl7.org/fhir/valueset.html
    "meta": {  # not defined in http://hl7.org/fhir/valueset.html
        "profile": [
          "http://hl7.org/fhir/StructureDefinition/shareablevalueset"
        ]
    },
    "text": {  # not defined in http://hl7.org/fhir/valueset.html
        "status": "generated",
        "div": "<div xmlns=\"http://www.w3.org/1999/xhtml\">\n\t\t\t<p>{}</p>\n\t\t</div>"
    },
    "url": "http://n3cValueSets.org/fhir/ValueSet/{}",  # can format w/ id  # optional?
    # "identifier": [
    #   {
    #     "system": "e.g. http://acme.com/identifiers/valuesets",
    #     "value": "e.g. loinc-cholesterol-int"
    #   }
    # ],
    # "version": "e.g. 1",
    "name": "TO_FILL",  # Name for this value set (computer friendly)
    "title": "TO_FILL",  # Name for this value set (human friendly)
    "status": "TO_FILL",  # draft | active | retired | unknown
    # "experimental": True,
    # "date": "2015-06-22",
    # "publisher": "e.g. HL7 International",
    # "contact": [
    #   {
    #     "name": "e.g. FHIR project team",
    #     "telecom": [
    #       {
    #         "system": "url",
    #         "value": "http://hl7.org/fhir"
    #       }
    #     ]
    #   }
    # ],
    "description": "TO_FILL",  # optional
    # "useContext": [
    #   {
    #     "code": {
    #       "system": "e.g. http://terminology.hl7.org/CodeSystem/usage-context-type",
    #       "code": "e.g. age"
    #     },
    #     "valueQuantity": {  # example
    #       "value": 18,
    #       "comparator": ">",
    #       "unit": "yrs",
    #       "system": "http://unitsofmeasure.org",
    #       "code": "a"
    #     }
    #   }
    # ],
    # "jurisdiction": [
    #   {
    #     "coding": [
    #       {
    #         "system": "e.g. urn:iso:std:iso:3166",
    #         "code": "US"
    #       }
    #     ]
    #   }
    # ],
    # "purpose": "e.g. This value set was published by ACME Inc in order to make clear which codes are used for...",
    # "copyright": "e.g. This content from LOINC ® is...",  # not defined in http://hl7.org/fhir/valueset.html
    "compose": {
        # "lockedDate": "e.g 2012-06-13",
        # "inactive": True,
        "include": [
            {
                "system": "TO_FILL",  # e.g. http://loinc.org
                "version": "TO_FILL",  # e.g. 2.36
                "concept": [  # examples below
                    # {
                    #   "code": "14647-2",
                    #   "display": "Cholesterol [Moles/Volume]"
                    # },
                    # {
                    #   "code": "2093-3",
                    #   "display": "Cholesterol [Mass/Volume]"
                    # },
                ]
            }
        ]
    }
}


OMOP_JSON_TEMPLATE = {
    "Concept Set Name": "",
    "Created At": "",
    "Created By": "",
    "Intention": {
        "Clinical Focus": "",
        "Inclusion Criteria": "",
        "Data Element Scope": "",
    },
    "Limitations": {
        "Exclusion Criteria": "",
        "VSAC Note": None,  # VSAC Note: (exclude if null)
    },
    "Provenance": {
        "VSAC Steward": "",
        "OID": "",
        "Code System(s)": [],
        "Definition Type": "",
        "Definition Version": "",
    }
}