#!/usr/bin/env node
/**
 * End-to-end test for invitation system using Marvin SDK
 *
 * Tests complete flow:
 * 1. Create invitation tokens for each workspace role
 * 2. Register users with invitation tokens
 * 3. Verify users have correct workspace roles
 *
 * Usage:
 *   npm install @inneropen/marvin-sdk@next
 *   node scripts/test_invitations_e2e.mjs
 *
 * Or with local SDK:
 *   SDK_PATH=/path/to/marvin-sdk node scripts/test_invitations_e2e.mjs
 */

import { fileURLToPath } from 'url';
import { dirname, join } from 'path';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

// Allow using local SDK for development
const SDK_PATH = process.env.SDK_PATH;
const sdkImportPath = SDK_PATH
  ? join(SDK_PATH, 'dist/platform.js')
  : '@inneropen/marvin-sdk/platform';

const { PlatformClient } = await import(sdkImportPath);

// Configuration
const MARVIN_URL = process.env.MARVIN_URL || 'http://localhost:8080';
const ADMIN_USER = process.env.ADMIN_USER || 'admin';
const ADMIN_PASS = process.env.ADMIN_PASS || 'MyPassword';

const ROLES = ['VIEWER', 'AUTHOR', 'EDITOR', 'ADMIN', 'OWNER'];

// Colors
const colors = {
  reset: '\x1b[0m',
  red: '\x1b[31m',
  green: '\x1b[32m',
  yellow: '\x1b[33m',
  blue: '\x1b[34m',
};

function log(color, message) {
  console.log(`${colors[color]}${message}${colors.reset}`);
}

function header(message) {
  console.log(`${colors.blue}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${colors.reset}`);
  console.log(`${colors.blue}  ${message}${colors.reset}`);
  console.log(`${colors.blue}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${colors.reset}`);
  console.log('');
}

async function getAdminToken() {
  const response = await fetch(`${MARVIN_URL}/api/auth/token`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    body: `username=${ADMIN_USER}&password=${ADMIN_PASS}`,
  });

  const data = await response.json();
  return data.access_token;
}

async function registerUser(token, role, timestamp) {
  const username = `${role.toLowerCase()}_sdk_${timestamp}`;

  const response = await fetch(`${MARVIN_URL}/api/users/register`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      full_name: `SDK Test ${role} User`,
      email: `${username}@test.com`,
      username: username,
      password: 'TestPass123!',
      password_confirm: 'TestPass123!',
      group_token: token,
      group: null,
      advanced: false,
      private: false,
      seed_data: false,
    }),
  });

  if (!response.ok) {
    const error = await response.text();
    throw new Error(`Registration failed: ${error}`);
  }

  return response.json();
}

async function main() {
  header('Marvin SDK End-to-End Invitation Test');

  const tokens = {};
  const users = {};

  try {
    // Step 1: Authenticate
    log('yellow', '[1/5] Authenticating...');
    const adminToken = await getAdminToken();

    if (!adminToken) {
      log('red', '✗ Failed to authenticate');
      process.exit(1);
    }

    const client = new PlatformClient({
      apiUrl: MARVIN_URL,
      userToken: adminToken,
    });

    log('green', '✓ Authenticated successfully');
    console.log('');

    // Step 2: Create invitation tokens
    log('yellow', '[2/5] Creating invitation tokens via SDK...');
    for (const role of ROLES) {
      process.stdout.write(`  Creating ${role} invitation... `);

      const invitation = await client.invites.create({
        usesLeft: 1,
        workspaceRole: role,
      });

      if (!invitation.token || invitation.workspaceRole !== role) {
        log('red', '✗ Failed');
        console.log('Response:', invitation);
        process.exit(1);
      }

      tokens[role] = invitation.token;
      log('green', `✓ (workspaceRole: ${invitation.workspaceRole})`);
    }
    console.log('');

    // Step 3: List and validate tokens
    log('yellow', '[3/5] Validating invitation list via SDK...');
    const invitations = await client.invites.list();

    for (const role of ROLES) {
      const token = tokens[role];
      const found = invitations.find(inv => inv.token === token);

      if (found && found.workspaceRole === role) {
        log('green', `  ✓ ${role} token found with correct role`);
      } else {
        log('red', `  ✗ ${role} token not found or role mismatch`);
        process.exit(1);
      }
    }
    console.log('');

    // Step 4: Register users
    log('yellow', '[4/5] Registering test users...');
    const timestamp = Date.now();
    for (const role of ROLES) {
      const username = `${role.toLowerCase()}_sdk_${timestamp}`;
      process.stdout.write(`  Registering ${username} with ${role} role... `);

      const user = await registerUser(tokens[role], role, timestamp);

      if (!user.id) {
        log('red', '✗ Failed');
        console.log('Response:', user);
        process.exit(1);
      }

      users[role] = user;
      log('green', `✓ (id: ${user.id.substring(0, 8)}...)`);
    }
    console.log('');

    // Step 5: Verify workspace roles
    log('yellow', '[5/5] Verifying workspace roles via SDK...');

    // Get current workspace - use the first user's groupId since they all joined the same workspace
    const workspaceId = users[ROLES[0]].groupId;

    let allCorrect = true;
    for (const role of ROLES) {
      const user = users[role];
      const username = `${role.toLowerCase()}_sdk_${timestamp}`;

      // Get workspace membership
      const member = await client.workspaceMembers.get(workspaceId, user.id);

      if (member.workspaceRole === role) {
        log('green', `  ✓ ${username} has correct role: ${role}`);
      } else {
        log('red', `  ✗ ${username} role mismatch! Expected ${role}, got ${member.workspaceRole}`);
        allCorrect = false;
      }
    }
    console.log('');

    // Summary
    header('Test Results');
    if (allCorrect) {
      log('green', '✓ All end-to-end tests passed!');
      console.log('');
      console.log('Test Summary:');
      console.log('  - 5 invitation tokens created via SDK');
      console.log('  - SDK responses validated (workspaceRole field)');
      console.log('  - 5 test users registered');
      console.log('  - All workspace roles correctly assigned');
      console.log('');
      console.log('Test users created:');
      for (const role of ROLES) {
        const username = `${role.toLowerCase()}_sdk_${timestamp}`;
        console.log(`  - ${username} (role: ${role}, password: TestPass123!)`);
      }
      console.log('');
      console.log('SDK modules tested:');
      console.log('  ✓ PlatformClient.invites.create()');
      console.log('  ✓ PlatformClient.invites.list()');
      console.log('  ✓ PlatformClient.workspaceMembers.get()');
    } else {
      log('red', '✗ Some tests failed');
      process.exit(1);
    }
    console.log(`${colors.blue}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${colors.reset}`);

  } catch (error) {
    console.log('');
    log('red', `✗ Test failed with error:`);
    console.error(error);
    process.exit(1);
  }
}

main();
