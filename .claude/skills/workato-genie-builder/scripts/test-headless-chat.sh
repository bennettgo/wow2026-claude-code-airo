#!/usr/bin/env bash
#
# test-headless-chat.sh — smoke test a Workato Genie via the Headless API.
#
# Usage:
#   GENIE_ID=gin-...-CD \
#   GENIE_API_TOKEN=<64-char hex from provisioning> \
#   IDP_USER_ID=<from provisioning output> \
#   WORKATO_DC=us \
#   ./test-headless-chat.sh "How much PTO do I have left?"
#
# Creates a fresh conversation, sends the message with stream=true, prints SSE
# events as they arrive, and stops on processing.finished.

set -euo pipefail

: "${GENIE_ID:?GENIE_ID is required}"
: "${GENIE_API_TOKEN:?GENIE_API_TOKEN is required (64-char hex from provisioner)}"
: "${IDP_USER_ID:?IDP_USER_ID is required (printed by provisioner)}"
DC="${WORKATO_DC:-us}"
HEADLESS_HOST="genie-api.workato.com"
if [ "$DC" != "us" ]; then
  HEADLESS_HOST="genie-api.$DC.workato.com"
fi
BASE="https://$HEADLESS_HOST/api/v1/genies/$GENIE_ID/chat"

MESSAGE="${1:-Hello, who are you?}"

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PARSER="$SCRIPT_DIR/sse-parser.py"

echo "▶ Workato Genie smoke test"
echo "  DC:        $DC ($HEADLESS_HOST)"
echo "  Genie:     $GENIE_ID"
echo "  User:      $IDP_USER_ID"
echo "  Message:   $MESSAGE"
echo

echo "[1/2] Creating conversation..."
CONV_RESP=$(curl -sS -X POST \
  -H "Authorization: Bearer $GENIE_API_TOKEN" \
  -H "X-IDP-User-Id: $IDP_USER_ID" \
  -H "Content-Type: application/json" \
  -d '{}' \
  "$BASE/conversations")

CONV_ID=$(printf '%s' "$CONV_RESP" | python3 -c 'import sys,json; print(json.load(sys.stdin)["result"]["conversation_id"])')
echo "       ✓ conversation_id=$CONV_ID"
echo

# JSON-encode the message safely (handles quotes, newlines, etc.)
PAYLOAD=$(python3 -c '
import json, sys
msg = sys.argv[1]
print(json.dumps({"file_id": "", "message": msg, "stream": True}))
' "$MESSAGE")

echo "[2/2] Sending message (streaming SSE)..."
echo "------------------------------------------------------------------"
curl -sN -X POST \
  -H "Authorization: Bearer $GENIE_API_TOKEN" \
  -H "X-IDP-User-Id: $IDP_USER_ID" \
  -H "Content-Type: application/json" \
  -H "Accept: text/event-stream" \
  -d "$PAYLOAD" \
  "$BASE/conversations/$CONV_ID/messages" \
  | python3 "$PARSER"

echo
echo "------------------------------------------------------------------"
echo "✓ Done. Conversation: $CONV_ID"
