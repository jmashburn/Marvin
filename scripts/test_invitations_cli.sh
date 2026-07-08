#!/usr/bin/env bash
#
# Test script for invitation system using marvin CLI
#
# This script tests invitation token creation via CLI:
# 1. Creates invitation tokens for each workspace role via CLI
# 2. Validates CLI output includes workspace_role field
# 3. Lists invitations and verifies roles via CLI
#
# Note: This script focuses on CLI testing only. For end-to-end registration
# testing, use test_invitations.sh instead.
#

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
MARVIN_URL="${MARVIN_URL:-http://localhost:8080}"
MARVIN_CLI="${MARVIN_CLI:-marvin}"
ADMIN_USER="${ADMIN_USER:-admin}"
ADMIN_PASS="${ADMIN_PASS:-MyPassword}"

# Test data
ROLES=("VIEWER" "AUTHOR" "EDITOR" "ADMIN" "OWNER")
TOKENS=()

echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}  Marvin CLI Invitation Test Suite${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

# Check if marvin CLI is available
if [[ "$MARVIN_CLI" == *"node"* ]]; then
  # Using node path directly
  if [ ! -f "${MARVIN_CLI##* }" ]; then
    echo -e "${RED}✗ marvin CLI not found at: ${MARVIN_CLI##* }${NC}"
    exit 1
  fi
elif ! command -v "$MARVIN_CLI" &> /dev/null; then
  echo -e "${RED}✗ marvin CLI not found${NC}"
  echo "  Please install: npm install -g @inneropen/marvin-cli@next"
  exit 1
fi

# Step 1: Authenticate with marvin CLI
echo -e "${YELLOW}[1/3] Authenticating with marvin CLI...${NC}"

# Get access token via API (CLI doesn't have username/password login)
ADMIN_TOKEN=$(curl -s -X POST "$MARVIN_URL/api/auth/token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=$ADMIN_USER&password=$ADMIN_PASS" | jq -r '.access_token')

if [ "$ADMIN_TOKEN" == "null" ] || [ -z "$ADMIN_TOKEN" ]; then
  echo -e "${RED}✗ Failed to authenticate as admin${NC}"
  exit 1
fi

# Save token to credentials file
mkdir -p ~/.marvin
echo "{\"userToken\":\"$ADMIN_TOKEN\",\"activeWorkspace\":\"home\"}" > ~/.marvin/credentials.json

# Verify CLI can authenticate
test_output=$(MARVIN_API_URL="$MARVIN_URL" "$MARVIN_CLI" workspace current 2>&1 || true)
if [[ "$test_output" == *"Error"* ]] || [[ "$test_output" == *"error"* ]] || [[ "$test_output" == *"401"* ]]; then
  echo -e "${RED}✗ CLI authentication failed${NC}"
  echo "Output: $test_output"
  exit 1
fi

echo -e "${GREEN}✓ Authenticated successfully${NC}"
echo ""

# Step 2: Create invitation tokens for each role using CLI
echo -e "${YELLOW}[2/3] Creating invitation tokens via CLI...${NC}"
idx=0
for role in "${ROLES[@]}"; do
  echo -n "  Creating $role invitation... "

  # Create invitation using CLI with JSON output
  output=$(MARVIN_API_URL="$MARVIN_URL" "$MARVIN_CLI" platform invites invite --uses 1 --role "$role" --json 2>&1)

  if [ $? -ne 0 ]; then
    echo -e "${RED}✗ Failed${NC}"
    echo "Output: $output"
    exit 1
  fi

  token=$(echo "$output" | jq -r '.token' 2>/dev/null)
  api_role=$(echo "$output" | jq -r '.workspaceRole' 2>/dev/null)

  if [ "$token" == "null" ] || [ -z "$token" ]; then
    echo -e "${RED}✗ Failed to parse JSON${NC}"
    echo "Output: $output"
    exit 1
  fi

  if [ "$api_role" != "$role" ]; then
    echo -e "${RED}✗ Role mismatch! Expected $role, got $api_role${NC}"
    exit 1
  fi

  TOKENS[$idx]=$token
  echo -e "${GREEN}✓${NC} (workspaceRole: $api_role)"
  idx=$((idx + 1))
done
echo ""

# Step 3: List tokens via CLI and validate roles
echo -e "${YELLOW}[3/3] Validating invitation list via CLI...${NC}"

# List all invitations
list_output=$(MARVIN_API_URL="$MARVIN_URL" "$MARVIN_CLI" platform invites list 2>&1)

if [ $? -ne 0 ]; then
  echo -e "${RED}✗ Failed to list invitations${NC}"
  echo "Output: $list_output"
  exit 1
fi

# Check each role appears in the list output
all_found=true
for role in "${ROLES[@]}"; do
  if echo "$list_output" | grep -q "$role"; then
    echo -e "  ${GREEN}✓${NC} $role invitation found in list"
  else
    echo -e "  ${RED}✗${NC} $role invitation not found in list"
    all_found=false
  fi
done
echo ""

# Summary
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
if [ "$all_found" = true ]; then
  echo -e "${GREEN}✓ All CLI tests passed!${NC}"
  echo ""
  echo "Test Summary:"
  echo "  - 5 invitation tokens created via marvin CLI"
  echo "  - CLI JSON output validated (workspaceRole field present)"
  echo "  - All roles verified in list output"
  echo ""
  echo "CLI commands tested:"
  echo "  ✓ marvin platform invites invite --role <ROLE> --uses <N> --json"
  echo "  ✓ marvin platform invites list"
  echo ""
  echo "Invitation tokens created (uses_left: 1):"
  idx=0
  for role in "${ROLES[@]}"; do
    echo "  - $role: ${TOKENS[$idx]}"
    idx=$((idx + 1))
  done
else
  echo -e "${RED}✗ Some tests failed${NC}"
  exit 1
fi
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
