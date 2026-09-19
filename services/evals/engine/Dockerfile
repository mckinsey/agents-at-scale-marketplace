# Eval engine image — a one-shot CLI invoked by the Argo onExit handler.
#
# Contains: Python + the ark_evals engine + kubectl (the judge is called by
# creating an Ark Query, per story 03). No FastAPI/Postgres/dashboard — this is
# the lean, run-once path, not the full agentic-evals-service stack.
FROM python:3.13-slim

# kubectl, for creating/polling the judge Query in-cluster.
ARG KUBECTL_VERSION=v1.31.0
RUN apt-get update \
 && apt-get install -y --no-install-recommends curl ca-certificates \
 && curl -fsSL "https://dl.k8s.io/release/${KUBECTL_VERSION}/bin/linux/$(dpkg --print-architecture)/kubectl" -o /usr/local/bin/kubectl \
 && chmod +x /usr/local/bin/kubectl \
 && apt-get purge -y curl \
 && apt-get autoremove -y \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY ark_evals ./ark_evals

ENV PYTHONPATH=/app PYTHONUNBUFFERED=1

# No default CMD args: the onExit handler passes `run --suite-dir ...` etc.
ENTRYPOINT ["python", "-m", "ark_evals"]
