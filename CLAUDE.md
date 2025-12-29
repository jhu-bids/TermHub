# TermHub - Claude Code Reference Guide
## Introduction
TermHub is a user interface and collection of analytic tools designed for working with OMOP concept sets. It serves as a
bridge between researchers and the N3C (National COVID Cohort Collaborative) Data Enclave, facilitating the authoring, 
comparison, and management of medical concept sets used in clinical research.

### Purpose
The application aims to ease the process of concept set authoring and facilitate the creation of higher-quality concept sets by providing:
- Immediate visualization of concept hierarchies and relationships
- Comparison capabilities for overlapping concept sets
- Display of metadata, term usage statistics, and patient counts
- Tools for modifying and uploading concept sets to the N3C Enclave
- Interface to multiple code set repositories

### Technology Stack
**Backend:**
- Python 3.9+ with FastAPI/Uvicorn
- PostgreSQL database (Azure-hosted in production)
- SQLAlchemy for database ORM
- Enclave API integration via custom `enclave_wrangler` module

**Frontend:**
- React 19.1.0 with Vite build system
- Material-UI (MUI) for components
- D3.js and d3-dag for complex graph visualizations
- ag-grid for data tables
- React Router for navigation
- Playwright for E2E testing

## Architecture Overview
### Backend Architecture
The backend (`backend/`) is a FastAPI application with the following key modules:

#### Application Entry Point
- `backend/app.py` - FastAPI application setup with CORS and GZip middleware
- Exposes three main route modules: `cset_crud`, `graph`, and `db`

#### Database Layer (`backend/db/`)
Core responsibilities:
- **Initialization** (`initialize.py`, `load.py`) - Database schema creation and data loading
- **Queries** (`queries.py`, `queries.sql`) - Reusable database queries
- **Refresh Scripts** - Multiple refresh mechanisms:
  - `refresh.py` - Main concept set refresh (runs every 20 minutes)
  - `refresh_dataset_group_tables.py` - Counts and vocabulary refreshes
  - `resolve_fetch_failures_*.py` - Handle draft csets and fetch failures
- **DDL Files** (`ddl-*.jinja.sql`) - Jinja2-templated SQL for creating tables, views, and indexes
  - Numbered sequentially (1-20+) to control execution order
  - Support schema switching via `{{schema}}` and optional suffixes for refreshes
- **Analysis** (`analysis.py`) - Database counts tracking and comparison over time
- **Configuration** (`config.py`) - Dependency maps for derived tables and views

#### API Routes (`backend/routes/`)
- `cset_crud.py` - CRUD operations for concept sets
- `graph.py` - Concept hierarchy and graph algorithms
- `db.py` - Database utilities and health checks

#### Enclave Integration (`enclave_wrangler/`)
Custom Python module for interacting with the N3C Data Enclave API:
- `objects_api.py` - Fetch concept sets and objects from Enclave
- `datasets.py` - Download and manage datasets
- `dataset_upload.py` - CSV-based concept set upload/creation
- `utils.py` - Authentication, pagination, error handling

### Frontend Architecture

The frontend (`frontend/src/`) is organized as follows:

#### Core Structure
- `App.jsx` - Main application component with routing
- `index.tsx` - Application entry point
- `env.js`, `env.dev.js`, `env.prod.js` - Environment-specific configurations

#### Components (`frontend/src/components/`)
Key page components:
- `CsetComparisonPage.jsx` - Main comparison and visualization interface
- `Csets.jsx` / `CsetsDataTable.jsx` - Concept set browsing and search
- `AddConcepts.tsx` - Interface for adding concepts to sets
- `AboutPage.jsx` - Application information and help
- `N3CRecommended.jsx` - Recommended concept sets display
- Shared components: `Tooltip.jsx`, `Popover.jsx`, `FlexibleContainer.jsx`, etc.

#### State Management (`frontend/src/state/`)
- Uses `react-hooks-global-state` for application-wide state
- Local state management within components

#### Utilities (`frontend/src/utils.jsx`)
- Helper functions for data transformation and formatting
- API client wrappers

### Database Schema

The primary schema is `n3c`, containing:

**Core Tables:**
- `code_sets` - Concept set metadata
- `concept_set_container` - Concept set containers
- `concept_set_version_item` - Expression items for concept set versions
- `concept_set_members` - Expanded concept set members
- `concept` - OMOP vocabulary concepts
- `concept_relationship` - Relationships between concepts
- `concept_ancestor` - Hierarchical relationships

**Derived Tables/Views:**
- `all_csets` / `all_csets_view` - Consolidated concept set information
- `concept_set_members` - Members derived from version items
- `cset_members_items` - Join of members and items
- `members_items_summary` - Summary statistics
- `concepts_with_counts` - Concepts with usage counts
- `concept_relationship_plus` / `concept_ancestor_plus` - Extended relationship tables
- `codeset_counts` - Aggregated counts per concept set

**Metadata Tables:**
- `manage` - System state variables (last refresh times, status)
- `counts` - Historical row counts for QC
- `counts_runs` - Audit log of count operations

### Data Flow
1. **Concept Set Refresh** (every 20 minutes):
   - GitHub Action triggers `backend/db/refresh.py`
   - Fetches new/updated concept sets from N3C Enclave API
   - Updates database tables
   - Regenerates derived tables and views

2. **Vocabulary Refresh** (every 6 months):
   - GitHub Action triggers vocabulary dataset refresh
   - Downloads latest OMOP vocabulary from Enclave
   - Updates `concept`, `concept_relationship`, `concept_ancestor` tables
   - Regenerates NetworkX graph (`termhub-vocab/relationship_graph.pickle`)

3. **Counts Refresh** (nightly):
   - GitHub Action checks for updated patient/record counts
   - Updates `concept_set_counts_clamped` and related tables

4. **User Interaction Flow**:
   - User selects concept sets via frontend
   - Frontend requests data from FastAPI backend
   - Backend queries PostgreSQL database
   - Graph algorithms compute hierarchies and relationships
   - Results returned to frontend for visualization

### Deployment
**Infrastructure** (JHU BIDS Azure):
- **Production Backend**: termhub.azurewebsites.net
- **Production Frontend**: purple-plant-0f4023d0f.2.azurestaticapps.net (bit.ly/termhub)
- **Database**: Azure PostgreSQL Flexible Server

**CI/CD**:
- GitHub Actions for automated testing and deployment
- Workflows: `.github/workflows/`
  - `backend_prod.yml` / `backend_dev.yml` - Backend deployments
  - `frontend_prod.yml` / `frontend_dev.yml` - Frontend deployments
  - `db_refresh.yml` - Automatic database refresh
  - `refresh_counts.yml` / `refresh_vocab.yml` - Data refreshes
  - Various test workflows for backend and frontend

**Versioning**:
- Semantic versioning (MAJOR.MINOR.PATCH)
- Version tracked in `frontend/src/env.js`
- Git tags mark deployed versions (`prod`, `dev`, dated backups)

## Development Workflows
### Local Setup
1. **Clone and Setup Submodules**:
   ```bash
   git clone git@github.com:jhu-bids/TermHub.git
   cd TermHub
   git submodule init
   git submodule update
   git lfs pull
   git submodule foreach git lfs pull
   ```

2. **Backend Setup**:
   ```bash
   python -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

3. **Frontend Setup**:
   ```bash
   cd frontend
   npm install
   cd ..
   ```

4. **Environment Variables**:
   ```bash
   mkdir env
   cp .env.example env/.env
   # Edit env/.env with database credentials and API tokens
   ```

5. **Start Development Servers**:
   ```bash
   # Backend (terminal 1)
   make serve-backend
   # or: uvicorn backend.app:APP --reload

   # Frontend (terminal 2)
   make serve-frontend
   # or: cd frontend; yarn start
   ```

### Common Make Commands
The `Makefile` provides shortcuts for frequent tasks:

**Testing**:
- `make test` - Run all tests (backend + frontend)
- `make test-backend` - Python unittest suite
- `make test-frontend` - All frontend tests (Jest + Playwright)
- `make test-frontend-unit` - Jest unit tests only
- `make test-frontend-e2e` - Playwright E2E tests (local)
- `make test-frontend-e2e-ui` - Playwright UI mode for debugging

**Database Management**:
- `make backup` - Generate database backup commands
- `make counts-update` - Update row counts in database
- `make counts-table` - View historical row counts
- `make deltas-table` - View row count changes over time
- `make counts-docs` - Generate count documentation
- `make refresh-counts` - Refresh counts dataset group
- `make refresh-vocab` - Refresh vocabulary dataset group
- `make reset-refresh-state` - Clean up after failed refresh

**Utilities**:
- `make kill-idle-cons` - Kill idle database connections
- `make fetch-missing-csets` - Find and import missing concept sets
- `make help` - Display all available commands

### Testing Strategy
**Backend Tests** (`test/`):
- Unit tests using Python's `unittest` framework
- Database tests validate schema and data integrity
- Run locally: `python -m unittest discover -v`
- Run via GitHub Actions on every push

**Frontend Tests** (`frontend/tests/`):
- **Unit Tests**: Jest for component and utility testing
  - Run: `cd frontend; yarn test:unit`
- **E2E Tests**: Playwright for user workflow testing
  - Run local: `make test-frontend-e2e`
  - Run with UI: `make test-frontend-e2e-ui`
  - Run against deployments: `make test-frontend-e2e-deployments`
  - Debug mode: `make test-frontend-e2e-debug`

**Test Environments**:
- Local (http://localhost:3000)
- Dev deployment (discontinued as of 2025/01)
- Production (https://purple-plant-0f4023d0f.2.azurestaticapps.net)

### Database Management Best Practices
#### Adding New Tables or Views
When adding derived tables or views, follow these steps:

1. **Create DDL File**: `backend/db/ddl-N-MODULE.jinja.sql`
   - Choose `N` based on dependencies (run after parent tables)
   - Use descriptive MODULE name
   - Template should use `{{schema}}` and `{{optional_suffix}}` appropriately

2. **Update Dependency Maps** in `backend/db/config.py`:
   - Add to `DERIVED_TABLE_DEPENDENCY_MAP` if it's a derived table
   - Add to `VIEWS` list if it's a view

3. **Template Syntax Rules**:
   - Use `{{optional_suffix}}` ONLY on the table/view being created
   - Do NOT use suffix on tables being selected FROM
   - Example:
     ```sql
     CREATE OR REPLACE VIEW {{schema}}my_view{{optional_suffix}} AS
     SELECT * FROM {{schema}}source_table;  -- No suffix here
     ```

4. **Test the Refresh**:
   - Run locally: `python backend/db/refresh_dataset_group_tables.py --dataset-group <group>`
   - Verify no errors and correct data

#### Database Refresh Process
The refresh system uses a swap-table approach to avoid downtime:

1. Creates new tables with `_new` suffix
2. Populates new tables with updated data
3. Renames current tables to `_old`
4. Renames `_new` tables to production names
5. Drops `_old` tables
6. Updates timestamp in `manage` table

**Recovery from Failed Refresh**:
- If a refresh fails mid-process, run: `make reset-refresh-state`
- This cleans up temporary tables and resets state flags

#### Monitoring Database Health
Track database size and row counts over time:
- `make counts-update` - Record current counts
- `make counts-table` - View historical data
- `make counts-compare-schemas` - Compare current vs backup schema
- Documentation auto-generated: `docs/backend/db/analysis.md`

### Graph Algorithm Considerations
TermHub's most complex feature is visualizing concept hierarchies:

**Key Challenges**:
- Concept sets can contain 50,000+ concepts
- Hierarchies may have disconnected components
- Gap-filling needed for "missing in-betweens" (concepts between selected ones)
- Performance critical for both backend computation and frontend rendering

**Algorithm Approach** (`backend/routes/graph.py`):
1. Extract subgraph from full concept relationship graph
2. Identify root and leaf nodes
3. Fill gaps to connect disconnected components
4. Filter by vocabulary (e.g., exclude RxNorm Extension)
5. Dynamic subtree hiding (show ~2000 nodes initially, expandable)

**Performance Strategies**:
- Caching of computed hierarchies
- Incremental loading with collapsible nodes
- Limiting initial display depth
- Frontend uses virtual scrolling for large lists

**Documentation**:
- Algorithm details: `docs/graph.md`
- Test cases: `docs/graph-testing.md`

## Repository-Specific Best Practices
### Version Control
**Submodules**:
- `termhub-csets` and `termhub-vocab` are Git LFS submodules
- Always pull LFS data: `git lfs pull && git submodule foreach git lfs pull`
- Submodules track specific commits; update carefully

**Branching**:
- `main` branch - production code
- Feature branches for development
- Tag deployments with git tags (`prod`, `dev`)

**Git Tags for Deployment**:
When deploying, update tags to match deployed commit:
```bash
git checkout COMMIT_TO_DEPLOY
git tag -d dev  # or prod
git tag dev     # or prod
git tag dev-YYYY-MM-DD  # Backup tag
git push --tags -f
```

### Deployment Process
**Pre-deployment Checklist**:
1. Ensure `ENV_FILE` GitHub secret is up-to-date (if env vars changed)
2. Run tests locally
3. Update version in `frontend/src/env.js` if needed
4. Tag the commit appropriately

**Manual Deployment**:
1. Go to GitHub Actions page
2. Select appropriate workflow (backend/frontend, dev/prod)
3. Click "Run workflow", select branch
4. Monitor deployment logs

**Post-deployment QA**:
1. Clear browser cache: Open console, run `localStorage.clear()`
2. Test example comparison page load
3. Test concept set selection and comparison
4. Verify controls on comparison page work
5. Check logs for errors

**Rollback Procedure** (if deployment fails):
1. Find last stable deployment in GitHub Actions history
2. Locate commit hash from action logs
3. Checkout that commit
4. Create rollback branch: `git checkout -b ROLLBACK`
5. Push branch and deploy from it
6. Delete rollback branch after successful deployment

### Environmental Variables
**Local Development** (`env/.env`):
- Never commit this file (gitignored)
- All team members should have identical `.env` files
- Use `.env.example` as template

**GitHub Actions** (`ENV_FILE` secret):
- Must be updated whenever local `.env` changes
- Location: GitHub repo → Settings → Secrets → Actions → ENV_FILE
- Copy entire contents of `env/.env` into this secret

**Key Variables**:
- `TERMHUB_DB_*` - Database connection parameters
- `PALANTIR_ENCLAVE_AUTHENTICATION_BEARER_TOKEN` - Enclave API auth (expires every 6 months)
- `BACKEND_URL` - Backend API endpoint for frontend

**Token Expiration**:
- Check auth token TTL: `python -c "from enclave_wrangler.utils import check_token_ttl; print(check_token_ttl(format='date-days'))"`
- Renew with N3C Enclave IT team (Mariam Deacy)
- Set calendar reminder before expiration

### Error Handling and Monitoring
**GitHub Actions Failures**:
- Automatic email to termhub-support@jh.edu on failure
- Most failures are transient (external services)
- Historical failure patterns documented: `docs/refresh_failure_history.md`
- Only investigate if multiple consecutive failures

**Common External Failures**:
- Enclave API errors (403, 406, 500, 503)
- GitHub infrastructure issues
- PyPI/npm registry connectivity
- Database connection limits

**Database Issues**:

*Connection slots exhausted*:
- Error: "remaining connection slots are reserved for non-replication superuser connections"
- Fix: Restart database via Azure Portal or run `make kill-idle-cons`

*Read-only mode after OOM*:
- Error: "cannot execute in a read-only transaction"
- Fix: Run SQL commands documented in `docs/developer.md`

*Memory issues*:
- Check Azure Portal → App Service Plan → Metrics
- May need to increase allocated memory

### Code Organization Principles
**Import Structure**:
To prevent circular imports:
- `utils.py` modules should never import other app modules
- `actions_api` can import from `objects_api`, but not vice versa
- Nothing should import from `backend.app`

**Module Responsibilities**:
- `enclave_wrangler/` - All external API interactions
- `backend/db/` - All database operations
- `backend/routes/` - API endpoint definitions only
- Backend query logic in `backend/db/queries.py`, not route handlers

**Frontend State**:
- Global state via `react-hooks-global-state` in `frontend/src/state/`
- Component-local state with React hooks
- Avoid prop drilling; use context or global state for deep trees

### CSV Upload for Concept Set Management
Users can create/update concept sets via CSV upload:

**Required Columns**:
- `concept_set_name` - Name of the concept set container
- `concept_id` - OMOP concept ID (or use vocabulary_concept_code + vocabulary_id)
- `includeDescendants` - Boolean
- `isExcluded` - Boolean
- `includeMapped` - Boolean
- `action` - Set to "add/replace"

**For Updates** (additionally require):
- `parent_version_codeset_id` - Parent concept set version ID
- `current_max_version` - Maximum existing version number

**Usage**:
```python
from enclave_wrangler.dataset_upload import upload_new_cset_version_with_concepts_from_csv
upload_new_cset_version_with_concepts_from_csv('path/to/csv')
```

Full schema documentation: `enclave_wrangler/README.md`

## Useful Resources
**Documentation**:
- Developer guide: `docs/developer.md`
- Database refresh: `docs/refresh.md`
- Graph algorithms: `docs/graph.md`
- Call graphs: `docs/call_graph.md`
- Backend: `backend/README.md`
- Frontend: `frontend/README.md`
- Enclave integration: `enclave_wrangler/README.md`

**External Links**:
- N3C Data Enclave: https://unite.nih.gov/
- Foundry API docs: https://www.palantir.com/docs/foundry/api/
- Enclave API docs: https://unite.nih.gov/workspace/documentation/developer/api
- Production deployment: https://bit.ly/termhub

**Key GitHub Workflows**:
- Database refresh: `.github/workflows/db_refresh.yml`
- Counts refresh: `.github/workflows/refresh_counts.yml`
- Vocab refresh: `.github/workflows/refresh_vocab.yml`
- All workflows: `.github/workflows/`

## Common Scenarios
### Adding a New API Endpoint
1. Choose appropriate route file in `backend/routes/`:
   - `cset_crud.py` - Concept set operations
   - `graph.py` - Graph/hierarchy operations
   - `db.py` - Database utilities
2. Create route handler function
3. Add database query to `backend/db/queries.py` if needed
4. Add route to router in the route file
5. Test endpoint using FastAPI auto-docs: http://localhost:8000/docs
6. Add frontend integration in appropriate component
7. Write tests (backend unit test, frontend E2E if user-facing)

### Updating OMOP Vocabulary
When N3C releases new vocabulary (every ~6 months):

1. **Trigger Refresh**:
   - Manually: `make refresh-vocab` (takes 4-6 hours)
   - Or wait for nightly GitHub Action

2. **Post-Refresh Steps**:
   - Restart TermHub servers (Azure Portal)
   - Wait 15 minutes for NetworkX graph regeneration
   - Face-check application in browser
   - Run Playwright E2E tests: `make test-frontend-e2e-prod`

3. **Monitoring**:
   - Check `manage.last_refreshed_vocab_tables` in database
   - Verify `termhub-vocab/relationship_graph.pickle` timestamp

### Database Corruption Recovery
If database becomes corrupted:

**Option A - Restore from Backup**:
```sql
-- Rename corrupted schema
ALTER SCHEMA n3c RENAME TO n3c_corrupted;
-- Rename backup to production
ALTER SCHEMA n3c_backup_YYYYMMDD RENAME TO n3c;
```

**Option B - Full Refresh**:
- Run workflow: `.github/workflows/refresh_from_datasets.yml`
- Or locally: `python backend/db/refresh_from_datasets.py`

**QC After Recovery**:
1. `make counts-update && make counts-table` - Verify counts
2. Restart local frontend/backend, clear localStorage, test features
3. Test dev deployment with localStorage cleared
4. Inspect `n3c` schema tables for anomalies

## Working with Claude Code
When working on this repository with Claude Code, keep in mind:

- **Complex Graph Algorithms**: The concept hierarchy rendering is one of the most complex parts of the codebase. 
Refer to `docs/graph.md` for algorithm explanations before making changes.

- **Database Schema Changes**: Any modification to database structure requires updates in multiple places (DDL files, 
config.py, potentially refresh scripts).

- **Testing**: Both backend and frontend have comprehensive test suites. When adding features, corresponding tests are expected.

- **External Dependencies**: Many failures in GitHub Actions are external (Enclave API, PyPI, GitHub infrastructure). 
Consult `docs/refresh_failure_history.md` before troubleshooting.

- **Performance**: The application handles large datasets (50K+ concepts). Always consider performance implications of 
changes, especially in graph algorithms and database queries.

- **Git Submodules**: These are actually not currently used. Try to ignore them.
