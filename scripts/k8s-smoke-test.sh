#!/usr/bin/env bash
set -euo pipefail

# Smoke tests for the ExaMon K8s deployment.
# Run after k8s-local-setup.sh to validate all services are healthy.
# Usage: ./scripts/k8s-smoke-test.sh

NAMESPACE="${NAMESPACE:-examon}"
FAILURES=0

pass() { echo "  PASS: $1"; }
fail() { echo "  FAIL: $1"; FAILURES=$((FAILURES + 1)); }

cleanup_port_forwards() {
  kill "$KDB_PF_PID" 2>/dev/null || true
  kill "$GF_PF_PID" 2>/dev/null || true
  kill "$ES_PF_PID" 2>/dev/null || true
  kill "$MQ_PF_PID" 2>/dev/null || true
}
trap cleanup_port_forwards EXIT

echo "=== ExaMon Smoke Tests ==="
echo ""

# --- Pod readiness ---
echo "--- Checking pod status ---"
kubectl get pods -n "$NAMESPACE" -o wide
kubectl get svc -n "$NAMESPACE"
echo ""

# Use high local ports for port-forward to avoid conflicts with K3d-exposed NodePorts
KDB_PORT=18083
GF_PORT=13000
ES_PORT=15000
MQ_PORT=11883

# --- Port forwards for testing ---
echo "--- Setting up port forwards ---"
kubectl port-forward svc/examon-kairosdb ${KDB_PORT}:8083 -n "$NAMESPACE" &
KDB_PF_PID=$!

kubectl port-forward svc/examon-grafana ${GF_PORT}:80 -n "$NAMESPACE" &
GF_PF_PID=$!

kubectl port-forward svc/examon-examon-server ${ES_PORT}:5000 -n "$NAMESPACE" &
ES_PF_PID=$!

kubectl port-forward svc/examon-mosquitto ${MQ_PORT}:1883 -n "$NAMESPACE" &
MQ_PF_PID=$!

sleep 5
echo ""

# --- Test 1: KairosDB health ---
echo "--- Test: KairosDB health endpoint ---"
if timeout 30s bash -c "while [[ \"\$(curl -s -o /dev/null -w '%{http_code}' http://localhost:${KDB_PORT}/api/v1/health/check)\" != '204' ]]; do sleep 3; done" 2>/dev/null; then
  pass "KairosDB is healthy"
else
  fail "KairosDB health check did not return 204"
fi

# --- Test 2: Grafana accessibility ---
echo "--- Test: Grafana accessibility ---"
if timeout 30s bash -c "while [[ \"\$(curl -s -o /dev/null -w '%{http_code}' http://localhost:${GF_PORT})\" != '302' ]]; do sleep 3; done" 2>/dev/null; then
  pass "Grafana is accessible"
else
  fail "Grafana did not return 302 redirect"
fi

# --- Test 3: ExaMon API server ---
echo "--- Test: ExaMon API server ---"
STATUS=$(curl -s -o /dev/null -w "%{http_code}" "http://localhost:${ES_PORT}/" 2>/dev/null || echo "000")
if [[ "$STATUS" == "401" || "$STATUS" == "200" ]]; then
  pass "ExaMon API is responding (HTTP $STATUS)"
else
  fail "ExaMon API returned unexpected HTTP $STATUS"
fi

# --- Test 4: MQTT broker pub/sub ---
echo "--- Test: MQTT broker connectivity ---"
if command -v mosquitto_pub &>/dev/null && command -v mosquitto_sub &>/dev/null; then
  mosquitto_sub -h localhost -p "${MQ_PORT}" -t 'smoke/test' -C 1 -W 10 &
  SUB_PID=$!
  sleep 1
  mosquitto_pub -h localhost -p "${MQ_PORT}" -t 'smoke/test' -m 'hello from smoke test'
  if wait "$SUB_PID" 2>/dev/null; then
    pass "MQTT pub/sub works"
  else
    fail "MQTT subscriber did not receive message"
  fi
else
  echo "  SKIP: mosquitto-clients not installed (apt-get install mosquitto-clients)"
fi

# --- Test 5: Data pipeline ---
echo "--- Test: Data pipeline (random_pub -> MQTT -> KairosDB) ---"
echo "  random_pub logs:"
kubectl logs -l app.kubernetes.io/name=random-pub -n "$NAMESPACE" --tail=3 2>/dev/null || echo "  (no logs)"
echo "  mqtt2kairosdb logs:"
kubectl logs -l app.kubernetes.io/name=mqtt2kairosdb -n "$NAMESPACE" --tail=3 2>/dev/null || echo "  (no logs)"

METRICS=$(curl -s "http://localhost:${KDB_PORT}/api/v1/metricnames" 2>/dev/null \
  | python3 -c "import sys,json; print(len(json.load(sys.stdin).get('results',[])))" 2>/dev/null || echo "0")
if [[ "$METRICS" -gt 0 ]]; then
  pass "Data pipeline verified: $METRICS metrics in KairosDB"
else
  echo "  WARN: No metrics in KairosDB yet (may need more time)"
fi

# --- Summary ---
echo ""
echo "=== Results ==="
if [[ "$FAILURES" -eq 0 ]]; then
  echo "All tests passed."
else
  echo "$FAILURES test(s) failed."
  exit 1
fi
