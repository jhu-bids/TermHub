## TermHub Frontend

### Running locally

`cd frontend; yarn start`

### Deployment

#### Production

Deploys to: [bit.ly/termhub](https://bit.ly/termhub) ([purple-plant-0f4023d0f.2.azurestaticapps.net/](https://purple-plant-0f4023d0f.2.azurestaticapps.net/))
Is deployed via GitHub Action: [.github/workflows/frontend_prod.yml](https://github.com/jhu-bids/TermHub/blob/main/.github/workflows/frontend_prod.yml)

- Can be deployed manually from GitHub: [run workflow](https://github.com/jhu-bids/TermHub/actions/workflows/frontend_prod.yml)
- Is deployed automatically whenever the `main` branch is updated.

#### Development

Deploys to: [bit.ly/termhub-dev](https://bit.ly/termhub-dev) ([icy-ground-0416a040f.2.azurestaticapps.net](https://icy-ground-0416a040f.2.azurestaticapps.net))
Is deployed via GitHub Action: [.github/workflows/frontend_dev.yml](https://github.com/jhu-bids/TermHub/blob/main/.github/workflows/frontend_dev.yml)

- Can be deployed manually from GitHub: [run workflow](https://github.com/jhu-bids/TermHub/actions/workflows/frontend_dev.yml)

#### Local build

1. `cd frontend; npm run build`
2. When that process completes, you should now have an updated `frontend/build` directory. This can be deployed as a static site. The entry point is `index.html`, which you can also open directly in the browser.
