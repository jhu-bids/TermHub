## VS-Hub Frontend

### Running locally

`cd frontend; yarn start`

### Deployment

#### Production

Deploys to: [bit.ly/termhub](https://bit.ly/termhub) ([purple-plant-0f4023d0f.2.azurestaticapps.net/](https://purple-plant-0f4023d0f.2.azurestaticapps.net/))
Is deployed via GitHub Action: [.github/workflows/frontend_prod.yml](https://github.com/jhu-bids/TermHub/blob/main/.github/workflows/frontend_prod.yml)

- Can be deployed manually from GitHub: [run workflow](https://github.com/jhu-bids/TermHub/actions/workflows/frontend_prod.yml)
- Is deployed automatically whenever the `main` branch is updated.

#### Development
Doesn't exist anymore as of 2025/01. This used to be the way it was set up:

Deploys to: [bit.ly/termhub-dev](https://bit.ly/termhub-dev) ([icy-ground-0416a040f.2.azurestaticapps.net](https://icy-ground-0416a040f.2.azurestaticapps.net))
Is deployed via GitHub Action: [.github/workflows/frontend_dev.yml](https://github.com/jhu-bids/TermHub/blob/main/.github/workflows/frontend_dev.yml)

- Can be deployed manually from GitHub: [run workflow](https://github.com/jhu-bids/TermHub/actions/workflows/frontend_dev.yml)
