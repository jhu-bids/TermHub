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
- (From commit msg):
  actions_api can import from object_api but
  not the other way around (and, btw, any module called utils should
  never import other app modules so it will be importable from anywhere,
  and nothing should ever import from backend.app.py)
