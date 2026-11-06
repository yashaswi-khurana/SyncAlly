#!/bin/sh
set -eu

namespace="${DEFAULT_NAMESPACE:-default}"
address="${TEMPORAL_ADDRESS:-temporal:7233}"

if temporal operator namespace describe --namespace "$namespace" --address "$address" >/dev/null 2>&1; then
  echo "Temporal namespace '$namespace' already exists"
  exit 0
fi

temporal operator namespace create --namespace "$namespace" --retention 7d --address "$address"
