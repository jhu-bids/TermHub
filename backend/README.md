## TermHub Backend
### Running locally
`uvicorn backend.app:app --reload`

### Deployment
#### Production
Deploys to: [termhub.azurewebsites.net](https://termhub.azurewebsites.net)
Is deployed via GitHub Action: [.github/workflows/backend_prod.yml](https://github.com/jhu-bids/TermHub/blob/main/.github/workflows/backend_prod.yml)
- Can be deployed manually from GitHub: [run workflow](https://github.com/jhu-bids/TermHub/actions/workflows/backend_prod.yml)
- Is deployed automatically whenever the `main` branch is updated.

#### Development
Deploys to: [termhub-dev.azurewebsites.net](https://termhub-dev.azurewebsites.net)
Is deployed via GitHub Action: [.github/workflows/backend_dev.yml](https://github.com/jhu-bids/TermHub/blob/main/.github/workflows/backend_dev.yml)
- Can be deployed manually from GitHub: [run workflow](https://github.com/jhu-bids/TermHub/actions/workflows/backend_dev.yml)

### Developer notes
From [3bfa2d](https://github.com/jhu-bids/TermHub/commit/3bfa2d) commit msg

- Moved to prevent circular imports:
  - from `actions_api` to `objects_api`
    - `get_concept_set_set_version_expression_items` and
    - `get_concept_set_version_members`, and
  - from `backend.app` to `backend.db.queries`
    - `get_concepts`
- `actions_api` can import from `object_api` but
  not the other way around (and, btw, any module called `utils` should
  never import other app modules so it will be importable from anywhere,
  and nothing should ever import from `backend.app`)
- Added a check for paginated results to enclave_get. Raises an error if
  there are any. Probably should handle more gracefully. See Teams chat,
  Siggie/Joe 2023-02-16:
  - Joe: hmmm... maybe indeed. perhaps we should keep the name enclave_get and add pagination as needed built into it
  - Siggie: 
    - That was my first thought, but handle_paginate returns a tuple of results and last response while enclave get just returns response. -- and there's error handling (that should maybe be centralized) in paginate as well as get_objects_by_type, and probably other places. and lots of scattered code for unwrapping response (response.json()['data'], and often extracting ['properties'] from each record.)
    - So, I'm not sure how ambitious the refactor should be.
    - If we do want to refactor and centralize all this, it might be nice to prohibit any other part of the code from importing requests or touching a Response object. Is that feasible?
