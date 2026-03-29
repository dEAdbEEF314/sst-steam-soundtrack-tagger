# Architecture

## Execution Model

All code is developed locally but executed inside Docker containers.

- Development: VS Code (local machine)
- Execution: SST-Worker container
- Deployment: Git pull + docker compose

Important:
- All paths must be container-relative (/app)
- Do not assume host execution