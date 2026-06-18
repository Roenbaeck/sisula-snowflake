#!/bin/bash
# Deploy metadata model and logging procedures to Snowflake
# Usage: ./deploy_metadata.sh <connection_name>

set -euo pipefail

if [ $# -lt 1 ]; then
    echo "Usage: $0 <connection_name>"
    echo "Example: $0 my_snowflake_conn"
    exit 1
fi

CONNECTION="$1"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "=== metadata deploy ==="
echo "Connection: $CONNECTION"
echo ""

run_step() {
    local step="$1"
    local file="$2"
    echo "--- $step ---"
    snow sql -c "$CONNECTION" --enable-templating NONE -f "$SCRIPT_DIR/$file" && echo "  OK" || { echo "  FAILED"; exit 1; }
    echo ""
}

run_step "1. Schema"           metadata/Install_1_CreateMetadataSchema.sql
run_step "2. Model (DDL)"      metadata/Install_2_MetadataModel.sql
run_step "3. Knot values"      metadata/Install_3_InsertKnotValues.sql
run_step "4. Logging procs"    metadata/Install_4_CreateLoggingProcedures.sql

echo "=== deploy complete ==="
