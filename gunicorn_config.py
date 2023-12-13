# Configuration for Gunicorn on Azure
# Azure Startup Command should be: gunicorn -c gunicorn_config.py app:app
# See: https://docs.gunicorn.org/en/stable/settings.html#config
# 2023/12/11: I don't think this file is used in any way right now. Also we're using uvicorn right now, not gunicorn.
# The actual command that runs to initiate our servers on dev/prod isn't shown in the GH action. Instead, go to the following URL, and then click the "General Settings" tab:
# Dev: https://portal.azure.com/#@live.johnshopkins.edu/resource/subscriptions/fe24df19-d251-4821-9a6f-f037c93d7e47/resourceGroups/jh-termhub-webapp-rg/providers/Microsoft.Web/sites/termhub/slots/dev/configuration
# Prod: https://portal.azure.com/#@live.johnshopkins.edu/resource/subscriptions/fe24df19-d251-4821-9a6f-f037c93d7e47/resourceGroups/JH-TERMHUB-WEBAPP-RG/providers/Microsoft.Web/sites/termhub/configuration
workers = 4
worker_class = "uvicorn.workers.UvicornWorker"
