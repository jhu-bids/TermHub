"""TermHub

Resources
  1. Features to add: https://docs.google.com/spreadsheets/d/19_eBv0MIBWPcXMTw3JJdcfPoEFhns93F-TKdODW27B8/edit#gid=0
  2. Flask boilerplate: https://github.com/realpython/flask-boilerplate
  3. App: https://termhub.herokuapp.com

TODO's:
  - Fetch from my FHIR server and see what it looks like
  - Heroku: submodules issue: google "heroku deploy with git submodules"
  - Patient counts: Get from N3C when they give us this API.
  - Datasets: Find hosting for static files / database: (a) AWS, (b) DataBricks, (c) our FHIR server
    https://docs.databricks.com/data-engineering/delta-live-tables/delta-live-tables-api-guide.html
    Background info: Stephanie has delta table in DataBricks. Can connect to CRISP (state of MD) data source, for ex.
    We would want to get this in OMOP format.
  - Add features: See resource (1) above.
  - Add API library: FastAPI?
  - later: SPA: Use React or something else to improve UX.
  - later: Heroku: slug size: !Warning: slug size (381 MB) exceeds our soft limit (300 MB) which may affect boot time.
  - later: Heroku: stack architecture: This app is using the Heroku-20 stack, however a newer stack is available.
    To upgrade to Heroku-22, see: https://devcenter.heroku.com/articles/upgrading-to-the-latest-stack
"""
#----------------------------------------------------------------------------#
# Imports
#----------------------------------------------------------------------------#
from typing import Dict

import pandas as pd
import requests
from flask import Flask, render_template, request
# from flask.ext.sqlalchemy import SQLAlchemy
import logging
from logging import Formatter, FileHandler
try:
    from termhub.forms import *
except ModuleNotFoundError:
    from forms import *
import os
from enclave_wrangler.dataset_download_new_api import objTypes





#----------------------------------------------------------------------------#
# App Config.
#----------------------------------------------------------------------------#
CONFIG = {
    'fhir_api_urls': {
        1: 'http://20.119.216.32:8080/fhir/'
    }
}

app = Flask(__name__)
try:
    app.config.from_object('termhub.config')
except ModuleNotFoundError:
    app.config.from_object('config')


from flask_restful import Resource, Api
api = Api(app)

class HelloWorld(Resource):
    def get(self):
        return {'hello': 'world'}

api.add_resource(HelloWorld, '/')

if __name__ == '__main__':
    app.run(debug=True)

#db = SQLAlchemy(app)

# Automatically tear down SQLAlchemy.
'''
@app.teardown_request
def shutdown_session(exception=None):
    db_session.remove()
'''

# Login required decorator.
'''
def login_required(test):
    @wraps(test)
    def wrap(*args, **kwargs):
        if 'logged_in' in session:
            return test(*args, **kwargs)
        else:
            flash('You need to login first.')
            return redirect(url_for('login'))
    return wrap
'''
#----------------------------------------------------------------------------#
# Variables on load
#----------------------------------------------------------------------------#
# todo

#----------------------------------------------------------------------------#
# Controllers.
#----------------------------------------------------------------------------#
def browse_onto_data() -> Dict[str, str]:
    ot = objTypes()
    apiNames = sorted([t['apiName'] for t in ot])
    # raise 'debugging'
    return apiNames


@app.route('/browse-onto')
def browse_onto():
    object_types: List = browse_onto_data()
    return render_template('pages/browse_onto.html', object_types=object_types)


def load_concept_sets(by_id: bool = False) -> Dict[str, str]:
    # TODO: maybe move this later
    TERMHUB_DIR = os.path.dirname(os.path.realpath(__file__))
    # DATASETS_DIR = os.path.join(TERMHUB_DIR, '..', 'termhub-csets')
    # concept_set_names_df = pd.read_csv(os.path.join(DATASETS_DIR, 'codesets-junk.csv'), sep='\t')
    # todo : temporarily moved this file
    concept_set_names_df = pd.read_csv(os.path.join(TERMHUB_DIR, 'codesets-junk.csv'), sep='\t')
    concept_sets = {}
    for _index, row in concept_set_names_df.iterrows():
        if by_id:
            concept_sets[str(row['codeset_id'])] = row['concept_set_name']
        else:
            concept_sets[row['concept_set_name']] = row['codeset_id']
    return concept_sets


@app.route('/')
def home():
    concept_sets: Dict = load_concept_sets()
    # return render_template('pages/home.html')
    # TODO: temp:
    return render_template('pages/concept_sets.html', concept_sets=concept_sets)


@app.route('/concept-sets')
def concept_sets():
    concept_sets: Dict = load_concept_sets()
    return render_template('pages/concept_sets.html', concept_sets=concept_sets)


# TODO: AssertionError: View function mapping is overwriting an existing endpoint function: concept_sets
@app.route('/concept-sets/<concept_set_id>')
def concept_set(concept_set_id: str):
    concept_sets: Dict = load_concept_sets(by_id=True)
    concept_set_name: str = concept_sets[concept_set_id]
    return render_template('pages/concept_set.html', concept_set_id=concept_set_id, concept_set_name=concept_set_name)


@app.route('/fhir-terminology')
def fhir_terminology():
    return fhir_terminology_i()


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


@app.route('/about')
def about():
    return render_template('pages/placeholder.about.html')


@app.route('/login')
def login():
    form = LoginForm(request.form)
    return render_template('forms/login.html', form=form)


@app.route('/register')
def register():
    form = RegisterForm(request.form)
    return render_template('forms/register.html', form=form)


@app.route('/forgot')
def forgot():
    form = ForgotForm(request.form)
    return render_template('forms/forgot.html', form=form)


# Error handlers.
@app.errorhandler(500)
def internal_error(error):
    #db_session.rollback()
    return render_template('errors/500.html'), 500


@app.errorhandler(404)
def not_found_error(error):
    return render_template('errors/404.html'), 404

if not app.debug:
    file_handler = FileHandler('error.log')
    file_handler.setFormatter(
        Formatter('%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]')
    )
    app.logger.setLevel(logging.INFO)
    file_handler.setLevel(logging.INFO)
    app.logger.addHandler(file_handler)
    app.logger.info('errors')

#----------------------------------------------------------------------------#
# Launch.
#----------------------------------------------------------------------------#

# Default port:
if __name__ == '__main__':
    app.run(debug=True, evalex=True)

# Or specify port manually:
'''
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
'''
