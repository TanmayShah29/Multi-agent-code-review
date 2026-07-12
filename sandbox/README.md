# Sandbox

This folder is a placeholder from initial scaffolding. The Docker-based
sandbox (`src/agents/executor_docker.py`) doesn't need a custom Dockerfile —
it runs the Coder's script directly inside the stock `python:3.11-slim` image
with `--network none`, memory/CPU/pid limits, and a read-only volume mount.

If you later want a custom image (e.g. to pre-install packages the Coder's
code might import), add a `Dockerfile` here, build it, and point
`DOCKER_IMAGE` in `executor_docker.py` at your built tag instead of
`python:3.11-slim`.
