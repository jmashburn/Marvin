#!/usr/bin/env bash
#
# Test script for invitation system with workspace roles
#
# This script tests the complete invitation flow:
# 1. Creates invitation tokens for each workspace role
# 2. Validates API responses include workspace_role field
# 3. Registers test users with invitation tokens
# 4. Verifies users have correct workspace roles
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
FRONTEND_URL="${FRONTEND_URL:-http://localhost:4321}"
ADMIN_USER="${ADMIN_USER:-admin}"
ADMIN_PASS="${ADMIN_PASS:-MyPassword}"

# Test data - store as parallel arrays instead of associative arrays
ROLES=("VIEWER" "AUTHOR" "EDITOR" "ADMIN" "OWNER")
TOKENS=()
USER_IDS=()

echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}  Marvin Invitation System Test Suite${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

# Step 1: Get admin access token
echo -e "${YELLOW}[1/5] Authenticating as admin...${NC}"
ADMIN_TOKEN=$(curl -s -X POST "$MARVIN_URL/api/auth/token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=$ADMIN_USER&password=$ADMIN_PASS" | jq -r '.access_token')

if [ "$ADMIN_TOKEN" == "null" ] || [ -z "$ADMIN_TOKEN" ]; then
  echo -e "${RED}✗ Failed to authenticate as admin${NC}"
  exit 1
fi
echo -e "${GREEN}✓ Authenticated successfully${NC}"
echo ""

# Step 2: Create invitation tokens for each role
echo -e "${YELLOW}[2/5] Creating invitation tokens for each role...${NC}"
idx=0
for role in "${ROLES[@]}"; do
  echo -n "  Creating $role invitation... "

  response=$(curl -s -X POST "$MARVIN_URL/api/groups/invitations" \
    -H "Content-Type: application/json" \
    -H "Authorization: Bearer $ADMIN_TOKEN" \
    -d "{\"uses_left\": 1, \"workspace_role\": \"$role\"}")

  token=$(echo "$response" | jq -r '.token')
  api_role=$(echo "$response" | jq -r '.workspaceRole')

  if [ "$token" == "null" ] || [ -z "$token" ]; then
    echo -e "${RED}✗ Failed${NC}"
    echo "Response: $response"
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

# Step 3: List tokens and validate roles
echo -e "${YELLOW}[3/5] Validating invitation list...${NC}"
token_list=$(curl -s -H "Authorization: Bearer $ADMIN_TOKEN" \
  "$MARVIN_URL/api/groups/invitations?page=1&perPage=100")

idx=0
for role in "${ROLES[@]}"; do
  token="${TOKENS[$idx]}"
  # Check if token exists in list with correct role
  found_role=$(echo "$token_list" | jq -r ".items[] | select(.token == \"$token\") | .workspaceRole")

  if [ "$found_role" == "$role" ]; then
    echo -e "  ${GREEN}✓${NC} $role token found in list with correct role"
  else
    echo -e "  ${RED}✗${NC} $role token not found or role mismatch (got: $found_role)"
    exit 1
  fi
  idx=$((idx + 1))
done
echo ""

# Step 4: Register users with invitation tokens
echo -e "${YELLOW}[4/5] Registering test users...${NC}"
idx=0
for role in "${ROLES[@]}"; do
  username=$(echo "$role" | tr '[:upper:]' '[:lower:]')_test
  token="${TOKENS[$idx]}"

  echo -n "  Registering $username with $role role... "

  response=$(curl -s -X POST "$MARVIN_URL/api/users/register" \
    -H "Content-Type: application/json" \
    -d "{
      \"full_name\": \"Test $role User\",
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
echo -e "${YELLOW}[5/5] Verifying workspace roles...${NC}"

# Get workspace ID (assuming default workspace/group)
workspace_id=$(curl -s -H "Authorization: Bearer $ADMIN_TOKEN" \
  "$MARVIN_URL/api/admin/groups" | jq -r '.items[0].id')

if [ "$workspace_id" == "null" ] || [ -z "$workspace_id" ]; then
  echo -e "${RED}✗ Failed to get workspace ID${NC}"
  exit 1
fi

all_correct=true
idx=0
for role in "${ROLES[@]}"; do
  user_id="${USER_IDS[$idx]}"
  username=$(echo "$role" | tr '[:upper:]' '[:lower:]')_test

  # Get user's workspace membership
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
  echo -e "${GREEN}✓ All tests passed!${NC}"
  echo ""
  echo "Test Summary:"
  echo "  - 5 invitation tokens created (one per role)"
  echo "  - API responses validated (workspaceRole field present)"
  echo "  - 5 test users registered"
  echo "  - All workspace roles correctly assigned"
  echo ""
  echo "Test users created:"
  for role in "${ROLES[@]}"; do
    username=$(echo "$role" | tr '[:upper:]' '[:lower:]')_test
    echo "  - $username (role: $role, password: TestPass123!)"
  done
else
  echo -e "${RED}✗ Some tests failed${NC}"
  exit 1
fi
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
