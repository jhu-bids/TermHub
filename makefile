SRC=backend/

.PHONY: counts-compare-schemas counts-table deltas-table count-docs counts-update counts-help backup test test-backend \
test-missing-csets test-frontend test-frontend-unit test-frontend-e2e test-frontend-e2e-debug test-frontend-e2e-ui \
test-frontend-e2e-deployment fetch-missing-csets refresh-counts refresh-vocab reset-refresh-state serve-frontend \
serve-backend help

# Analysis
ANALYSIS_SCRIPT=backend/db/analysis.py

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

# counts-update: Update 'counts' table with current row counts for the 'n3c' schema. Adds note to the 'counts-runs' table.
counts-update:
	@python $(ANALYSIS_SCRIPT) --counts-update

counts-help:
	@python $(ANALYSIS_SCRIPT) --help

# Utils
backup:
	sh ./db_backup.sh

kill-idle-cons:
	python backend/db/utils.py --kill-idle-cons

# Testing
test: test-backend test-frontend

## Testing - Backend
test-backend:
	python -m unittest discover -v
test-missing-csets:
	python -m unittest test.test_database.TestDatabaseCurrent.test_all_enclave_csets_in_termhub_within_threshold

## Testing - Frontend
## - ENVIRONMENTS: To run multiple, hyphen-delimit, e.g. ENVIRONMENTS=local-dev-prod
TEST_ENV_LOCAL=ENVIRONMENTS=local
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
	ENVIRONMENTS=dev-prod ${TEST_FRONTEND_CMD})
test-frontend-e2e-dev:
	(cd frontend; \
	ENVIRONMENTS=dev ${TEST_FRONTEND_CMD})
test-frontend-e2e-prod:
	(cd frontend; \
	ENVIRONMENTS=prod ${TEST_FRONTEND_CMD})
## - codegen: "codeless" Playwright generation of UI tests by recording browser interaction
##   You don't need to use 'local' necessarily if you want to write the tests for local. Any of these commands can work
##   to write tests that are theoretically compatible in any environment (as long as the UI is the same). The only
##   difference is that when the test code is written, the first line will hard-code the URL to that environment. So
##   after recording, the code should be repuprosed in the style of frontend/tests/.
codegen-local:
	(cd frontend; \
	yarn playwright codegen http://localhost:3000)
codegen-dev:
	(cd frontend; \
	yarn playwright codegen http://icy-ground-0416a040f.2.azurestaticapps.net)
codegen-prod:
	(cd frontend; \
	yarn playwright codegen http://purple-plant-0f4023d0f.2.azurestaticapps.net)

# QC
fetch-missing-csets:
	python enclave_wrangler/objects_api.py --find-and-add-missing-csets-to-db

# Database refreshes
refresh-counts:
	python backend/db/refresh_dataset_group_tables.py --dataset-group counts
refresh-vocab:
	python backend/db/refresh_dataset_group_tables.py --dataset-group vocab
reset-refresh-state:
	python backend/db/utils.py --reset-refresh-state

# Serve
# nvm allows to switch to a particular versio of npm/node. Useful for working w/ deployment
# https://github.com/nvm-sh/nvm
serve-frontend:
	nvm use 18.2.0; cd frontend; yarn start

serve-backend:
	uvicorn backend.app:APP --reload

# Help
help:
	@echo "Available targets:"
	@echo counts-compare-schemas
	@printf "Checks counts of database tables for the current 'n3c' schema and its most recent backup.\n\n"
	@echo counts-table
	@printf "View counts row counts over time for the 'n3c' schema.\n\n"
	@echo deltas-table
	@printf "View row count detlas over time for the 'n3c' schema.\n\n"
	@echo count-docs
	@printf "Runs --counts-over-time and --deltas-over-time and puts in documentation: docs/backend/db/analysis.md.\n\n"
	@echo counts-update
	@printf "Update 'counts' table with current row counts for the 'n3c' schema. Adds note to the 'counts-runs' table.\
	\n\n"
	@echo counts-help
	@printf "Show help for counts commands.\n\n"
	@echo backup
	@printf "Runs a script with instructions on how to do a database backup.\n\n"
	@echo kill-idle-cons
	@printf "Kills all idle connections older than 10 minutes.\n\n"
	@echo test
	@printf "Runs all backend and frontend tests.\n\n"
	@echo test-backend
	@printf "Runs all backend tests.\n\n"
	@echo test-missing-csets
	@printf "Runs a test to check for any missing concept sets that have been in the Enclave for >30 minutes and are not in TermHub\n\n"
	@echo test-frontend
	@printf "Runs all frontend tests.\n\n"
	@echo test-frontend-unit
	@printf "Runs all frontend unit tests.\n\n"
	@echo test-frontend-e2e
	@printf "Runs all frontend end-to-end tests.\n\n"
	@echo test-frontend-e2e-debug
	@printf "Run frontend end-to-end tests in debug mode.\n\n"
	@echo test-frontend-e2e-ui
	@printf "Runs frontend end-to-end tests in Playwright's special UI.\n\n"
	@echo test-frontend-e2e-deployment
	@printf "Runs frontend end-to-end tests on just deployed instances; not local.\n\n"
	@echo fetch-missing-csets
	@printf "Fetches any missing concept sets from the Enclave, importing them into TermHub.\n\n"
	@echo refresh-counts
	@printf "Refresh the 'counts' dataset group tables.\n\n"
	@echo refresh-vocab
	@printf "Refresh the 'vocab' dataset group tables.\n\n"
	@echo reset-refresh-state
	@printf "Run this if the refresh exited incorrectly and the 'finally' block didn't get run (e.g. manually stopping \
	the debugger or a crash). Removes any temporary tables that have _old or _new suffixes. Updates timestamp database \
	variables which indicate that the refresh is currently in progress.\n\n"
	@echo serve-frontend
	@printf "Starts up a server process for the frontend.\n\n"
	@echo serve-backend
	@printf "Starts up a server process for the backend.\n\n"
	@echo help
	@printf "Show this help message.\n\n"
