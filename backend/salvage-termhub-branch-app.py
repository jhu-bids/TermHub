# TODO: standardize this use case. right now this is just an experiment
@app.route('/fhir-terminology/<api_url_id>')
def fhir_terminology_i(api_url_id: str = '1'):
    """FHIR Terminology
    http://20.119.216.32:8080/fhir/"""
    # TODO: for some reason code systems etc aren't fetching from url dynamically
    # TODO: need when select from dropdown, actually follows link. look at url_for from main.html
    # TODO: Show only a subset of the JSON returned
    fhir_api_urls: Dict[int, str] = CONFIG['fhir_api_urls']
    fhir_api_base_url = fhir_api_urls[int(api_url_id)]
    fhir_codesystem_url = fhir_api_base_url + 'CodeSystem'
    fhir_valueset_url = fhir_api_base_url + 'ValueSet'
    fhir_conceptmap_url = fhir_api_base_url + 'ConceptMap'
    code_systems = requests.get(fhir_codesystem_url).json()
    value_sets = requests.get(fhir_valueset_url).json()
    concept_maps = requests.get(fhir_conceptmap_url).json()
    return render_template('pages/fhir_terminology.html',
        fhir_api_url_selection_id=int(api_url_id),
        fhir_api_urls=fhir_api_urls,
        code_systems=code_systems,
        value_sets=value_sets,
        concept_maps=concept_maps)


# TODO: Package enclave_wrangler separately. add this functionality there, and import that
@app.route('/enclave')
def enclave():
    """N3C Palantir Data Enclave
    - https://www.palantir.com/docs/foundry/api/general/overview/paging/
    - https://www.palantir.com/docs/foundry/api/ontology-resources/objects/list-objects/"""
    # TODO: Utilize some of this:
    # [3:25 PM] Sigfried Gold
    # cat ../ValueSet-Tools-REPLACED-BY-TermHub/enclave_wrangler/curl-tests/output/conceptSetVersionItems.json|jq  '.nextPageToken'
    # "v1.eyJ0IjoiT2JqZWN0cy4xIiwicHMiOjEwMDAsInRva2VuIjoidjEuZXlKeVpYRjFaWE4wUTJobFkydHpkVzBpT2lJMU5EQXpOalZsTldZeU9HUmhZVGc0WkROallqa3lOVFV5T0RRd01HVmhOemcxWVdZM01HSTNZVEEzTWpNME4ySmhZVEF4TlRVMllqQTRPREE0TWpBeUlpd2lZbUZqYTJWdVpGQmhaMlZVYjJ0bGJpSTZJbll4TGpVeFpqTTBPRFE1TFRnek1UQXROR0kzWkMwNE5UbGpMV1kxTTJRM05qSTJOelU1WVM0eE1EQXdJaXdpWW1GamEyVnVaQ0k2SWxCSVQwNVBSMUpCVUVnaWZRPT0ifQ=="
    #  curl \
    #                   -H "Content-type: application/json" \
    #                   -H "Authorization: Bearer $TOKEN" \
    #                   "https://$HOSTNAME/api/v1/ontologies" | jq '.data[0].rid'
    # Header: 'Content-type: application/json'
    # Header: 'Authorization: Bearer $TOKEN'

    # hostname = 'unite.nih.gov'
    # rid = ''
    # ontology_rid = ''
    # x1 = f'https://{hostname}/api/v1/ontologies/{rid}'
    # x2 = f'https://{hostname}/api/v1/ontologies/{ontology_rid}/objects/OmopConceptSetVersionItem'

    return render_template('pages/enclave.html')

