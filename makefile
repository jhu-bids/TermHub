SRC=backend/

.PHONY: lint tags ltags test all lintall codestyle docstyle lintsrc linttest doctest doc docs code linters_all codesrc \
codetest docsrc doctest counts-compare-schemas counts-table deltas-table test-missing-csets fetch-missing-csets

# Analysis
ANALYSIS_SCRIPT = 'backend/db/analysis.py'

# counts-compare-schemas: Checks counts of database tables for the current 'n3c' schema and its most recent backup.
counts-compare-schemas:
	@python $(ANALYSIS_SCRIPT) --counts-compare-schemas

# counts-table: View counts row counts over time for the 'n3c' schema.
counts-table:
	@python $(ANALYSIS_SCRIPT) --counts-over-time

# deltas-table: View row count detlas over time for the 'n3c' schema.
deltas-table:
	@python $(ANALYSIS_SCRIPT) --deltas-over-time

# counts-docs: Runs --counts-over-time and --deltas-over-time and puts in documentation: docs/backend/db/analysis.md.
counts-docs:
	@python $(ANALYSIS_SCRIPT) --counts-docs

# todo
#deltas-viz:
#	@python $(ANALYSIS_SCRIPT) --counts-over-time save_delta_viz
#counts-viz:
#	@python $(ANALYSIS_SCRIPT) --counts-over-time save_counts_viz

# counts-update: Update 'counts' table with current row counts for the 'n3c' schema. Adds note to the 'counts-runs' table.
counts-update:
	@python $(ANALYSIS_SCRIPT) --counts-update

counts-help:
	@python $(ANALYSIS_SCRIPT) --help

# Codestyle, linters, and testing
# - Code & Style Linters
all: linters_all test
lint: lintsrc codesrc docsrc
linters_all: doc code lintall

# Pylint Only
PYLINT_BASE =python -m pylint --output-format=colorized --reports=n
lintall: lintsrc linttest
lintsrc:
	${PYLINT_BASE} ${SRC}
linttest:
	${PYLINT_BASE} test/

# PyCodeStyle Only
PYCODESTYLE_BASE=python -m pycodestyle
codestyle: codestylesrc codestyletest
codesrc: codestylesrc
codetest: codestyletest
code: codestyle
codestylesrc:
	${PYCODESTYLE_BASE} ${SRC}
codestyletest:
	 ${PYCODESTYLE_BASE} test/

# PyDocStyle Only
PYDOCSTYLE_BASE=python -m pydocstyle
docstyle: docstylesrc docstyletest
docsrc: docstylesrc
doctest: docstyletest
docs: docstyle
docstylesrc:
	${PYDOCSTYLE_BASE} ${SRC}
docstyletest:
	${PYDOCSTYLE_BASE} test/
codetest:
	python -m pycodestyle test/
codeall: code codetest
doc: docstyle

# Testing
test: test-backend test-frontend

## Testing - Backend
test-backend:
	python -m unittest discover -v
test-missing-csets:
	python -m unittest test.test_database.TestDatabaseCurrent.test_all_enclave_csets_in_termhub

## Testing - Frontend
## - ENVIRONMENTS: To run multiple, hyphen-delimit, e.g. ENVIRONMENTS=local-dev-prod
TEST_ENV_LOCAL=ENVIRONMENTS=local
TEST_ENV_DEPLOYED=ENVIRONMENTS=dev-prod
TEST_FRONTEND_CMD=yarn test:e2e
test-frontend:
	(cd frontend; \
	yarn test)
test-frontend-unit:
	(cd frontend; \
	yarn test:unit)
test-frontend-e2e:
	(cd frontend; \
	${TEST_ENV_LOCAL} ${TEST_FRONTEND_CMD}; \
	yarn playwright show-report)
test-frontend-e2e-debug:
	(cd frontend; \
	${TEST_ENV_LOCAL} ${TEST_FRONTEND_CMD} --debug)
test-frontend-e2e-ui:
	(cd frontend; \
	${TEST_ENV_LOCAL} ${TEST_FRONTEND_CMD} --ui)
test-frontend-e2e-deployments:
	(cd frontend; \
	${TEST_ENV_DEPLOYED} ${TEST_FRONTEND_CMD})

# QC
fetch-missing-csets:
	python enclave_wrangler/objects_api.py --find-and-add-missing-csets-to-db

# Serve
# nvm allows to switch to a particular versio of npm/node. Useful for working w/ deployment
# https://github.com/nvm-sh/nvm
serve-frontend:
	nvm use 18.2.0; cd frontend; yarn start

serve-backend:
	uvicorn backend.app:APP --reload
