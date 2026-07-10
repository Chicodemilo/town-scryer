#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
RESULTS_FILE="$PROJECT_DIR/api/test-results.json"

echo "Running tests..."

PASSED=0
FAILED=0
FAILED_TESTS=""

# Backend tests (pytest)
echo "=== Backend Tests (pytest) ==="
cd "$PROJECT_DIR/api"
if DATABASE_URL=sqlite:///:memory: SECRET_KEY=test pytest app/tests/ -v --tb=short 2>&1 | tee /tmp/pytest_output.txt; then
  BACKEND_PASSED=$(grep -cE "PASSED" /tmp/pytest_output.txt || echo 0)
  BACKEND_FAILED=$(grep -cE "FAILED" /tmp/pytest_output.txt || echo 0)
else
  BACKEND_PASSED=$(grep -cE "PASSED" /tmp/pytest_output.txt || echo 0)
  BACKEND_FAILED=$(grep -cE "FAILED" /tmp/pytest_output.txt || echo 1)
  FAILED_TESTS=$(grep -E "FAILED" /tmp/pytest_output.txt | sed 's/FAILED //' || echo "")
fi
PASSED=$((PASSED + BACKEND_PASSED))
FAILED=$((FAILED + BACKEND_FAILED))

# Frontend tests (vitest)
echo ""
echo "=== Frontend Tests (vitest) ==="
cd "$PROJECT_DIR/frontend"
if npx vitest run --reporter=verbose 2>&1 | tee /tmp/vitest_output.txt; then
  FRONTEND_PASSED=$(grep -cE "✓" /tmp/vitest_output.txt || echo 0)
  FRONTEND_FAILED=$(grep -cE "✗|×" /tmp/vitest_output.txt || echo 0)
else
  FRONTEND_PASSED=$(grep -cE "✓" /tmp/vitest_output.txt || echo 0)
  FRONTEND_FAILED=$(grep -cE "✗|×" /tmp/vitest_output.txt || echo 1)
fi
PASSED=$((PASSED + FRONTEND_PASSED))
FAILED=$((FAILED + FRONTEND_FAILED))

# Build failed tests array
FAILED_ARRAY="[]"
if [ -n "$FAILED_TESTS" ]; then
  FAILED_ARRAY=$(echo "$FAILED_TESTS" | while IFS= read -r line; do
    echo "\"$(echo "$line" | sed 's/"/\\"/g')\""
  done | paste -sd "," - | sed 's/^/[/' | sed 's/$/]/')
fi

TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

cat > "$RESULTS_FILE" << EOJSON
{
  "passed": $PASSED,
  "failed": $FAILED,
  "failed_tests": $FAILED_ARRAY,
  "timestamp": "$TIMESTAMP"
}
EOJSON

echo ""
echo "=== Results ==="
echo "Passed: $PASSED"
echo "Failed: $FAILED"
echo "Results written to: $RESULTS_FILE"
