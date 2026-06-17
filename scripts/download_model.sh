#!/usr/bin/env bash
# Download the pre-trained sentiment analysis model
set -euo pipefail

MODEL_URL="https://github.com/Profession-AI/progetti-devops/raw/refs/heads/main/Deploy%20e%20monitoraggio%20di%20un%20modello%20di%20sentiment%20analysis%20per%20recensioni/sentimentanalysismodel.pkl"
DEST="${1:-app/sentimentanalysismodel.pkl}"

echo "Downloading model to ${DEST}..."
curl -fSL "${MODEL_URL}" -o "${DEST}"
echo "Done."
