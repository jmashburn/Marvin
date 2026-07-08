#!/usr/bin/env bash
#
# Test script for invitation system using marvin CLI
#
# This script tests the complete invitation flow using CLI commands:
# 1. Creates invitation tokens for each workspace role via CLI
# 2. Validates CLI output includes workspace_role field
# 3. Registers test users with invitation tokens via API
# 4. Verifies users have correct workspace roles via CLI
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

# Test data - store as parallel arrays
ROLES=("VIEWER" "AUTHOR" "EDITOR" "ADMIN" "OWNER")
TOKENS=()
USER_IDS=()

echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}  Marvin Invitation System CLI Test Suite${NC}"
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
echo -e "${YELLOW}[1/5] Authenticating with marvin CLI...${NC}"

# Get access token via API (CLI doesn't have username/password login)
ADMIN_TOKEN=$(curl -s -X POST "$MARVIN_URL/api/auth/token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=$ADMIN_USER&password=$ADMIN_PASS" | jq -r '.access_token')

if [ "$ADMIN_TOKEN" == "null" ] || [ -z "$ADMIN_TOKEN" ]; then
  echo -e "${RED}✗ Failed to authenticate as admin${NC}"
  exit 1
fi

# Save token to credentials file directly instead of using login command
mkdir -p ~/.marvin
echo "{\"userToken\":\"$ADMIN_TOKEN\",\"activeWorkspace\":\"home\"}" > ~/.marvin/credentials.json

# Verify CLI can authenticate
test_output=$(MARVIN_API_URL="$MARVIN_URL" "$MARVIN_CLI" workspace current 2>&1)
if [[ "$test_output" == *"Error"* ]] || [[ "$test_output" == *"error"* ]]; then
  echo -e "${RED}✗ CLI authentication failed${NC}"
  echo "Output: $test_output"
  exit 1
fi

echo -e "${GREEN}✓ Authenticated successfully${NC}"
echo ""

# Step 2: Create invitation tokens for each role using CLI
echo -e "${YELLOW}[2/5] Creating invitation tokens via CLI...${NC}"
idx=0
for role in "${ROLES[@]}"; do
  echo -n "  Creating $role invitation... "

  # Create invitation using CLI
  output=$(MARVIN_API_URL="$MARVIN_URL" "$MARVIN_CLI" platform invites invite --uses 1 --role "$role" --json 2>&1)

  if [ $? -ne 0 ]; then
    echo -e "${RED}✗ Failed${NC}"
    echo "Output: $output"
    exit 1
  fi

  token=$(echo "$output" | jq -r '.token')
  api_role=$(echo "$output" | jq -r '.workspaceRole')

  if [ "$token" == "null" ] || [ -z "$token" ]; then
    echo -e "${RED}✗ Failed to get token${NC}"
    echo "Output: $output"
    exit 1
  fi

  if [ "$api_role" != "$role" ]; then
    echo -e "${RED}✗ Role mismatch! Expected $role, got $api_role${NC}"
    exit 1
  fi

  TOKENS[$idx]=$token
  echo -e "${GREEN}✓${NC} (token: ${token:0:20}...)"
  idx=$((idx + 1))
done
echo ""

# Step 3: List tokens via CLI and validate roles
echo -e "${YELLOW}[3/5] Validating invitation list via CLI...${NC}"

token_list=$(MARVIN_API_URL="$MARVIN_URL" "$MARVIN_CLI" platform invites list --json 2>&1)

if [ $? -ne 0 ]; then
  echo -e "${RED}✗ Failed to list invitations${NC}"
  echo "Output: $token_list"
  exit 1
fi

idx=0
for role in "${ROLES[@]}"; do
  token="${TOKENS[$idx]}"

  # CLI list doesn't return full token, so we'll just verify the role exists
  role_count=$(echo "$token_list" | jq -r ".[] | select(.Role == \"$role\") | .Role" | wc -l | tr -d ' ')

  if [ "$role_count" -gt 0 ]; then
    echo -e "  ${GREEN}✓${NC} $role token found in CLI list"
  else
    echo -e "  ${RED}✗${NC} $role token not found in CLI list"
    exit 1
  fi
  idx=$((idx + 1))
done
echo ""

# Step 4: Register users with invitation tokens
echo -e "${YELLOW}[4/5] Registering test users...${NC}"
idx=0
for role in "${ROLES[@]}"; do
  username=$(echo "$role" | tr '[:upper:]' '[:lower:]')_cli_test
  token="${TOKENS[$idx]}"

  echo -n "  Registering $username with $role role... "

  response=$(curl -s -X POST "$MARVIN_URL/api/users/register" \
    -H "Content-Type: application/json" \
    -d "{
      \"full_name\": \"CLI Test $role User\",
      \"email\": \"${username}@test.com\",
      \"username\": \"${username}\",
      \"password\": \"TestPass123!\",
      \"password_confirm\": \"TestPass123!\",
      \"group_token\": \"${token}\",
      \"group\": null,
      \"advanced\": false,
      \"private\": false,
      \"seed_data\": false
    }")

  user_id=$(echo "$response" | jq -r '.id')

  if [ "$user_id" == "null" ] || [ -z "$user_id" ]; then
    echo -e "${RED}✗ Failed${NC}"
    echo "Response: $response"
    exit 1
  fi

  USER_IDS[$idx]=$user_id
  echo -e "${GREEN}✓${NC} (id: ${user_id:0:8}...)"
  idx=$((idx + 1))
done
echo ""

# Step 5: Verify workspace roles using CLI
echo -e "${YELLOW}[5/5] Verifying workspace roles via CLI...${NC}"

# Get workspace slug (assuming first workspace)
workspace_slug=$(curl -s -H "Authorization: Bearer $ADMIN_TOKEN" \
  "$MARVIN_URL/api/admin/workspaces" | jq -r '.items[0].slug')

if [ "$workspace_slug" == "null" ] || [ -z "$workspace_slug" ]; then
  echo -e "${RED}✗ Failed to get workspace slug${NC}"
  exit 1
fi

# Get workspace ID for API verification
workspace_id=$(curl -s -H "Authorization: Bearer $ADMIN_TOKEN" \
  "$MARVIN_URL/api/admin/workspaces" | jq -r '.items[0].id')

all_correct=true
idx=0
for role in "${ROLES[@]}"; do
  user_id="${USER_IDS[$idx]}"
  username=$(echo "$role" | tr '[:upper:]' '[:lower:]')_cli_test

  # Verify via API (CLI doesn't have a direct workspace member get command yet)
  membership=$(curl -s -H "Authorization: Bearer $ADMIN_TOKEN" \
    "$MARVIN_URL/api/platform/workspaces/$workspace_id/members/$user_id")

  actual_role=$(echo "$membership" | jq -r '.workspaceRole')

  if [ "$actual_role" == "$role" ]; then
    echo -e "  ${GREEN}✓${NC} $username has correct role: $role"
  else
    echo -e "  ${RED}✗${NC} $username role mismatch! Expected $role, got $actual_role"
    all_correct=false
  fi
  idx=$((idx + 1))
done
echo ""

# Summary
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
if [ "$all_correct" = true ]; then
  echo -e "${GREEN}✓ All CLI tests passed!${NC}"
  echo ""
  echo "Test Summary:"
  echo "  - 5 invitation tokens created via CLI"
  echo "  - CLI JSON output validated (workspaceRole field present)"
  echo "  - 5 test users registered"
  echo "  - All workspace roles correctly assigned"
  echo ""
  echo "Test users created:"
  for role in "${ROLES[@]}"; do
    username=$(echo "$role" | tr '[:upper:]' '[:lower:]')_cli_test
    echo "  - $username (role: $role, password: TestPass123!)"
  done
  echo ""
  echo "CLI tested:"
  echo "  - marvin platform invites invite --role <ROLE> --json"
  echo "  - marvin platform invites list --json"
else
  echo -e "${RED}✗ Some tests failed${NC}"
  exit 1
fi
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
