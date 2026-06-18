#!/bin/bash
# Run all sisula-snowflake tests against Snowflake
# Usage: ./test_all.sh <connection_name>

set -euo pipefail

if [ $# -lt 1 ]; then
    echo "Usage: $0 <connection_name>"
    echo "Example: $0 my_snowflake_conn"
    exit 1
fi

CONNECTION="$1"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SQL_DIR="$SCRIPT_DIR/sql"

echo "=== sisula-snowflake test suite ==="
echo "Connection: $CONNECTION"
echo ""

FAILED=0
PASSED=0

run_test() {
    local name="$1"
    local file="$SQL_DIR/$2"
    echo "--- $name ---"
    if snow sql -c "$CONNECTION" --enable-templating NONE -f "$file"; then
        PASSED=$((PASSED + 1))
        echo "  PASS"
    else
        FAILED=$((FAILED + 1))
        echo "  FAIL"
    fi
    echo ""
}

run_test "Basic rendering"       test_render.sql
run_test "AND/OR operators"      test_and_or.sql
run_test "contains() function"   test_contains.sql
run_test "Inline IF OR"          test_inline_if_or.sql
run_test "Nested inline IF"      test_nested_inline_if.sql

echo "=== Results: $PASSED passed, $FAILED failed ==="

if [ "$FAILED" -gt 0 ]; then
    exit 1
fi
