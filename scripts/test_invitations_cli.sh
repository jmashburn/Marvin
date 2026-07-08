#!/usr/bin/env bash
#
# End-to-end test script for invitation system using marvin CLI
#
# This script tests the complete invitation flow:
# 1. Creates invitation tokens for each workspace role via CLI
# 2. Validates CLI output includes workspace_role field
# 3. Lists invitations and verifies roles via CLI
# 4. Registers test users with invitation tokens (via API - CLI doesn't support registration yet)
# 5. Verifies users have correct workspace roles
# 6. Confirms invitation tokens had uses_left decremented
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
USER_IDS=()
TIMESTAMP=$(date +%s)

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
echo -e "${YELLOW}[1/6] Authenticating with marvin CLI...${NC}"

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
echo -e "${YELLOW}[2/6] Creating invitation tokens via CLI...${NC}"
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
echo -e "${YELLOW}[3/6] Validating invitation list via CLI...${NC}"

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

# Step 4: Register users with invitation tokens
echo -e "${YELLOW}[4/6] Registering test users (via API - CLI doesn't support registration yet)...${NC}"
idx=0
for role in "${ROLES[@]}"; do
  username=$(echo "$role" | tr '[:upper:]' '[:lower:]')_cli_test_${TIMESTAMP}
  token="${TOKENS[$idx]}"

  echo -n "  Registering $username with $role role... "

  response=$(curl -s -X POST "$MARVIN_URL/api/users/register" \
    -H "Content-Type: application/json" \
    -d "{
      \"full_name\": \"CLI Test $role User ${TIMESTAMP}\",
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

# Step 5: Verify workspace roles
echo -e "${YELLOW}[5/6] Verifying workspace roles...${NC}"

# Get workspace ID using marvin CLI
workspace_list=$(MARVIN_API_URL="$MARVIN_URL" "$MARVIN_CLI" workspace list 2>&1)
if [ $? -ne 0 ]; then
  echo -e "${RED}✗ Failed to list workspaces via CLI${NC}"
  echo "Output: $workspace_list"
  exit 1
fi

# Extract first workspace ID from table output (skip header, get first data row)
workspace_id=$(echo "$workspace_list" | grep -v "^ID\|^--\|^$" | head -1 | awk '{print $1}')

if [ -z "$workspace_id" ]; then
  echo -e "${RED}✗ Failed to get workspace ID from CLI output${NC}"
  exit 1
fi

all_correct=true
idx=0
for role in "${ROLES[@]}"; do
  user_id="${USER_IDS[$idx]}"
  username=$(echo "$role" | tr '[:upper:]' '[:lower:]')_cli_test_${TIMESTAMP}

  # Get user's workspace membership via marvin CLI
  member_info=$(MARVIN_API_URL="$MARVIN_URL" "$MARVIN_CLI" platform workspace-members get "$workspace_id" "$user_id" 2>&1)

  if [ $? -ne 0 ]; then
    echo -e "  ${RED}✗${NC} Failed to get membership for $username"
    all_correct=false
    idx=$((idx + 1))
    continue
  fi

  # Extract workspace role from CLI output (looking for "Workspace Role:" line)
  actual_role=$(echo "$member_info" | grep -i "workspace role" | awk -F: '{print $2}' | xargs)

  if [ "$actual_role" == "$role" ]; then
    echo -e "  ${GREEN}✓${NC} $username has correct role: $role"
  else
    echo -e "  ${RED}✗${NC} $username role mismatch! Expected $role, got $actual_role"
    all_correct=false
  fi
  idx=$((idx + 1))
done
echo ""

# Step 6: Verify invitation tokens were consumed
echo -e "${YELLOW}[6/6] Verifying invitation tokens were consumed...${NC}"

# Get updated token list
token_list=$(curl -s -H "Authorization: Bearer $ADMIN_TOKEN" \
  "$MARVIN_URL/api/groups/invitations?page=1&perPage=100")

idx=0
tokens_consumed=true
for role in "${ROLES[@]}"; do
  token="${TOKENS[$idx]}"
  # Check uses_left for each token
  uses_left=$(echo "$token_list" | jq -r ".items[] | select(.token == \"$token\") | .usesLeft")

  if [ "$uses_left" == "0" ]; then
    echo -e "  ${GREEN}✓${NC} $role token consumed (uses_left: 0)"
  else
    echo -e "  ${RED}✗${NC} $role token not consumed! (uses_left: $uses_left, expected: 0)"
    tokens_consumed=false
  fi
  idx=$((idx + 1))
done
echo ""

# Summary
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
if [ "$all_found" = true ] && [ "$all_correct" = true ] && [ "$tokens_consumed" = true ]; then
  echo -e "${GREEN}✓ All end-to-end tests passed!${NC}"
  echo ""
  echo "Test Summary:"
  echo "  - 5 invitation tokens created via marvin CLI"
  echo "  - CLI JSON output validated (workspaceRole field present)"
  echo "  - All roles verified in CLI list output"
  echo "  - 5 test users registered via API"
  echo "  - All workspace roles correctly assigned"
  echo "  - All invitation tokens consumed (uses_left: 0)"
  echo ""
  echo "CLI commands tested:"
  echo "  ✓ marvin platform invites invite --role <ROLE> --uses <N> --json"
  echo "  ✓ marvin platform invites list"
  echo ""
  echo "Test users created:"
  for role in "${ROLES[@]}"; do
    username=$(echo "$role" | tr '[:upper:]' '[:lower:]')_cli_test_${TIMESTAMP}
    echo "  - $username (role: $role, password: TestPass123!)"
  done
else
  echo -e "${RED}✗ Some tests failed${NC}"
  exit 1
fi
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
