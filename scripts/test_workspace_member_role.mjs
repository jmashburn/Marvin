#!/usr/bin/env node
/**
 * Test workspace member role update via SDK
 * Usage: node scripts/test_workspace_member_role.mjs <workspace_id> <user_id> <new_role>
 */

import { PlatformClient } from '@inneropen/marvin-sdk';

const [workspaceId, userId, newRole] = process.argv.slice(2);

if (!workspaceId || !userId || !newRole) {
  console.error('Usage: node scripts/test_workspace_member_role.mjs <workspace_id> <user_id> <new_role>');
  console.error('Example: node scripts/test_workspace_member_role.mjs abc123 user456 EDITOR');
  process.exit(1);
}

const validRoles = ['VIEWER', 'AUTHOR', 'EDITOR', 'ADMIN', 'OWNER'];
if (!validRoles.includes(newRole)) {
  console.error(`Invalid role: ${newRole}`);
  console.error(`Valid roles: ${validRoles.join(', ')}`);
  process.exit(1);
}

// Read credentials from ~/.marvin/credentials.json
import { readFileSync } from 'fs';
import { join } from 'path';
import { homedir } from 'os';

const credPath = join(homedir(), '.marvin', 'credentials.json');
let credentials;
try {
  credentials = JSON.parse(readFileSync(credPath, 'utf8'));
} catch (error) {
  console.error('Failed to read credentials from ~/.marvin/credentials.json');
  console.error('Run: marvin login first');
  process.exit(1);
}

const sdk = new PlatformClient({
  apiUrl: process.env.MARVIN_API_URL || 'http://localhost:8080',
  userToken: credentials.userToken,
});

console.log('\n🔄 Testing workspace member role update...');
console.log(`Workspace ID: ${workspaceId}`);
console.log(`User ID: ${userId}`);
console.log(`New Role: ${newRole}`);

try {
  // First, get current member details
  console.log('\n📋 Current member details:');
  const currentMember = await sdk.workspaceMembers.get(workspaceId, userId);
  console.log(JSON.stringify(currentMember, null, 2));

  // Update the role using snake_case
  console.log(`\n🔧 Updating role to ${newRole} (using workspace_role)...`);
  const updated = await sdk.workspaceMembers.updateRole(workspaceId, userId, {
    workspace_role: newRole,
  });

  console.log('\n✅ Role updated successfully!');
  console.log('Updated member:');
  console.log(JSON.stringify(updated, null, 2));

} catch (error) {
  console.error('\n❌ Error updating role:');
  console.error(error.message);
  if (error.response) {
    console.error('Response status:', error.response.status);
    console.error('Response data:', error.response.data);
  }
  process.exit(1);
}
