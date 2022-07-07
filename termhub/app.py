"""TermHub

Resources
  1. Features to add: https://docs.google.com/spreadsheets/d/19_eBv0MIBWPcXMTw3JJdcfPoEFhns93F-TKdODW27B8/edit#gid=0
  2. Flask boilerplate: https://github.com/realpython/flask-boilerplate

TODO's:
  - Patient counts: Get from N3C when they give us this API.
  - Datasets: Find hosting for static files / database: (a) AWS, (b) DataBricks
    https://docs.databricks.com/data-engineering/delta-live-tables/delta-live-tables-api-guide.html
    Background info: Stephanie has delta table in DataBricks. Can connect to CRISP (state of MD) data source, for ex.
    We would want to get this in OMOP format.
  - Add features: See resource (1) above.
"""
#----------------------------------------------------------------------------#
# Imports
#----------------------------------------------------------------------------#
import pandas as pd
from flask import Flask, render_template, request
# from flask.ext.sqlalchemy import SQLAlchemy
import logging
from logging import Formatter, FileHandler
try:
    from termhub.forms import *
except ModuleNotFoundError:
    from forms import *
import os

#----------------------------------------------------------------------------#
# App Config.
#----------------------------------------------------------------------------#

app = Flask(__name__)
try:
    app.config.from_object('termhub.config')
except ModuleNotFoundError:
    app.config.from_object('config')
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
@app.route('/')
def home():
    return render_template('pages/home.html')


@app.route('/concept_sets')
def concept_sets():
    # TODO: maybe move this later
    TERMHUB_DIR = os.path.dirname(os.path.realpath(__file__))
    DATASETS_DIR = os.path.join(TERMHUB_DIR, '..', 'termhub-csets')
    concept_set_names_df = pd.read_csv(os.path.join(DATASETS_DIR, 'codesets-junk.csv'), sep='\t')
    concept_sets = {}
    for _index, row in concept_set_names_df.iterrows():
        concept_sets[row['concept_set_name']] = row['codeset_id']
    return render_template('pages/concept_sets.html', concept_sets=concept_sets)


# TODO: AssertionError: View function mapping is overwriting an existing endpoint function: concept_sets
@app.route('/concept_sets/<concept_set_id>')
def concept_set(concept_set_id):
    return render_template('pages/concept_sets.html', concept_set_id=concept_set_id, concept_set_name='example')


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
    app.run()

# Or specify port manually:
'''
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
'''
