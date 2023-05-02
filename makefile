SRC=backend/

.PHONY: lint tags ltags test all lintall codestyle docstyle lintsrc \
linttest doctest doc docs code linters_all codesrc codetest docsrc \
doctest counts-compare-schemas counts-table deltas-table

# Analysis
ANALYSIS_SCRIPT = 'backend/db/analysis.py'

# counts-compare-schemas: Checks counts of database tables for the current 'n3c' schema and its most recent backup.
counts-compare-schemas:
	@python3 $(ANALYSIS_SCRIPT) --counts-compare-schemas

# counts-table: View counts row counts over time for the 'n3c' schema.
counts-table:
	@python3 $(ANALYSIS_SCRIPT) --counts-over-time

# deltas-table: View row count detlas over time for the 'n3c' schema.
deltas-table:
	@python3 $(ANALYSIS_SCRIPT) --deltas-over-time

# counts-docs: Runs --counts-over-time and --deltas-over-time and puts in documentation: docs/backend/db/analysis.md.
counts-docs:
	@python3 $(ANALYSIS_SCRIPT) --counts-docs

# todo
#deltas-viz:
#	@python3 $(ANALYSIS_SCRIPT) --counts-over-time save_delta_viz
#counts-viz:
#	@python3 $(ANALYSIS_SCRIPT) --counts-over-time save_counts_viz

# counts-update: Update 'counts' table with current row counts for the 'n3c' schema. Adds note to the 'counts-runs' table.
ifeq (counts-update,$(firstword $(MAKECMDGOALS)))
  # use the rest as arguments for "counts-updates"
  COUNTS_UPDATE_ARGS := $(wordlist 2,$(words $(MAKECMDGOALS)),$(MAKECMDGOALS))
  # ...and turn them into do-nothing targets
  $(eval $(COUNTS_UPDATE_ARGS):;@:)
endif
counts-update:
	@python3 $(ANALYSIS_SCRIPT) --counts-update --note "$(COUNTS_UPDATE_ARGS)"

counts-help:
	@python3 $(ANALYSIS_SCRIPT) --help

# Codestyle, linters, and testing
# - Code & Style Linters
all: linters_all testall
lint: lintsrc codesrc docsrc
linters_all: doc code lintall

# Pylint Only
PYLINT_BASE =python3 -m pylint --output-format=colorized --reports=n
lintall: lintsrc linttest
lintsrc:
	${PYLINT_BASE} ${SRC}
linttest:
	${PYLINT_BASE} test/

# PyCodeStyle Only
PYCODESTYLE_BASE=python3 -m pycodestyle
codestyle: codestylesrc codestyletest
codesrc: codestylesrc
codetest: codestyletest
code: codestyle
codestylesrc:
	${PYCODESTYLE_BASE} ${SRC}
codestyletest:
	 ${PYCODESTYLE_BASE} test/

# PyDocStyle Only
PYDOCSTYLE_BASE=python3 -m pydocstyle
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
test:
	python3 -m unittest discover -v
testdoc:
	python3 -m test.test --doctests-only
testall: test testdoc

# Serve
# nvm allows to switch to a particular versio of npm/node. Useful for working w/ deployment
# https://github.com/nvm-sh/nvm
serve-frontend:
	nvm use 18.2.0; cd frontend; npm run start

serve-backend:
	uvicorn backend.app:APP --reload

# TODO: does this work?
serve: serve-backend serve-frontend
