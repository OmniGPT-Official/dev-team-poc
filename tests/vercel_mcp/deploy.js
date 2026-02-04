'use strict';

/**
 * Vercel deploy tool — uses the official @vercel/sdk.
 *
 * 1. Creates a git-sourced deployment via the SDK
 * 2. Polls until state is READY (or errors / times out)
 * 3. Writes the live URL to stdout (one line — Python captures this)
 *
 * All other output goes to stderr so it doesn't pollute the URL capture.
 *
 * Requires: VERCEL_TOKEN env var
 */

const { Vercel } = require('@vercel/sdk');

// ---------------------------------------------------------------------------
// Config
// ---------------------------------------------------------------------------
// Override any of these via env vars when called from VercelDeployTools
const PROJECT_NAME     = process.env.DEPLOY_PROJECT_NAME || 'crumble-bakery-deploy-test';
const GITHUB_ORG       = process.env.DEPLOY_GITHUB_ORG   || 'Muhammad-Anique';
const GITHUB_REPO      = process.env.DEPLOY_GITHUB_REPO  || '--crumble-bakery--softwar-33438';
const POLL_INTERVAL_MS = 5_000;   // 5 s
const TIMEOUT_MS       = 300_000; // 5 min

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------
function log(msg) {
  console.error(msg);   // stderr only
}

async function sleep(ms) {
  return new Promise(resolve => setTimeout(resolve, ms));
}

// ---------------------------------------------------------------------------
// Poll until READY
// ---------------------------------------------------------------------------
async function waitForReady(vercel, deploymentId) {
  const deadline = Date.now() + TIMEOUT_MS;
  let attempt = 0;

  while (true) {
    attempt++;

    const dep = await vercel.deployments.getDeployment({ idOrUrl: deploymentId });
    const state = (dep.state || dep.status || 'UNKNOWN').toUpperCase();

    log(`  [poll ${attempt}] state=${state}`);

    if (state === 'READY') {
      return dep.url || `https://${dep.name}.vercel.app`;
    }

    if (state === 'ERROR' || state === 'CANCELED') {
      log(`  Full response: ${JSON.stringify(dep, null, 2)}`);
      throw new Error(`Deployment ended with state=${state}`);
    }

    if (Date.now() > deadline) {
      throw new Error(`Timed out after ${TIMEOUT_MS / 1000}s — last state: ${state}`);
    }

    await sleep(POLL_INTERVAL_MS);
  }
}

// ---------------------------------------------------------------------------
// Main
// ---------------------------------------------------------------------------
async function main() {
  if (!process.env.VERCEL_TOKEN) {
    throw new Error('VERCEL_TOKEN is not set');
  }

  const vercel = new Vercel({ bearerToken: process.env.VERCEL_TOKEN });

  // Ensure project name is lowercase and valid
  const sanitizedProjectName = PROJECT_NAME.toLowerCase()
    .replace(/[^a-z0-9._-]/g, '-')  // Replace invalid chars with -
    .replace(/---+/g, '--')          // Don't allow --- sequence
    .substring(0, 100);              // Max 100 chars

  log(`[deploy.js] Creating deployment: ${GITHUB_ORG}/${GITHUB_REPO}`);
  log(`[deploy.js] Project name: ${sanitizedProjectName}`);

  const deployment = await vercel.deployments.createDeployment({
    requestBody: {
      name: sanitizedProjectName,
      target: 'production',
      gitSource: {
        type:  'github',
        repo:  GITHUB_REPO,
        ref:   'main',
        org:   GITHUB_ORG,
      },
      projectSettings: {
        framework: null,  // Auto-detect framework
      },
    },
    skipAutoDetectionConfirmation: '1',  // Try as top-level parameter
  });

  log(`[deploy.js] Created — id=${deployment.id}  status=${deployment.status || deployment.state}`);

  const url = await waitForReady(vercel, deployment.id);

  // stdout: just the URL — this is what Python reads
  console.log(url);
}

main().catch(err => {
  console.error(`[deploy.js] ERROR: ${err.message}`);
  process.exit(1);
});
