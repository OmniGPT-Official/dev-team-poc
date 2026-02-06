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

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------
function log(msg) {
  const timestamp = new Date().toISOString().slice(11, 23);
  console.error(`[${timestamp}] ${msg}`);   // stderr only
}

async function sleep(ms) {
  return new Promise(resolve => setTimeout(resolve, ms));
}

// ---------------------------------------------------------------------------
// Poll until READY
// ---------------------------------------------------------------------------
async function waitForReady(vercel, deploymentId) {
  let attempt = 0;

  while (true) {
    attempt++;

    log(`[POLL ${attempt}] Checking deployment status...`);

    try {
      const dep = await vercel.deployments.getDeployment({ idOrUrl: deploymentId });
      const state = (dep.state || dep.status || 'UNKNOWN').toUpperCase();

      log(`[POLL ${attempt}] State: ${state}`);

      if (state === 'READY') {
        const finalUrl = dep.url ? `https://${dep.url}` : `https://${dep.name}.vercel.app`;
        log(`[SUCCESS] Deployment is READY!`);
        log(`[SUCCESS] URL: ${finalUrl}`);
        return finalUrl;
      }

      if (state === 'ERROR' || state === 'CANCELED') {
        log(`[ERROR] Deployment ended with state: ${state}`);
        log(`[ERROR] Full response: ${JSON.stringify(dep, null, 2)}`);
        throw new Error(`Deployment ended with state=${state}`);
      }

      if (state === 'BUILDING') {
        log(`[POLL ${attempt}] Build in progress...`);
      } else if (state === 'QUEUED') {
        log(`[POLL ${attempt}] Deployment queued, waiting...`);
      } else if (state === 'INITIALIZING') {
        log(`[POLL ${attempt}] Initializing deployment...`);
      }

    } catch (pollError) {
      log(`[POLL ${attempt}] Error checking status: ${pollError.message}`);
      // Continue polling even on transient errors
    }

    await sleep(POLL_INTERVAL_MS);
  }
}

// ---------------------------------------------------------------------------
// Main
// ---------------------------------------------------------------------------
async function main() {
  log('========================================');
  log('VERCEL DEPLOYMENT SCRIPT STARTED');
  log('========================================');

  // Step 1: Check token
  log('[STEP 1] Checking VERCEL_TOKEN...');
  if (!process.env.VERCEL_TOKEN) {
    log('[ERROR] VERCEL_TOKEN is NOT SET!');
    log('[ERROR] Please set VERCEL_TOKEN environment variable');
    throw new Error('VERCEL_TOKEN is not set');
  }
  const tokenPreview = process.env.VERCEL_TOKEN.slice(0, 8) + '...' + process.env.VERCEL_TOKEN.slice(-4);
  log(`[STEP 1] VERCEL_TOKEN is set: ${tokenPreview}`);

  // Step 2: Initialize SDK
  log('[STEP 2] Initializing Vercel SDK...');
  const vercel = new Vercel({ bearerToken: process.env.VERCEL_TOKEN });
  log('[STEP 2] SDK initialized successfully');

  // Step 3: Prepare project name
  log('[STEP 3] Preparing deployment parameters...');
  const sanitizedProjectName = PROJECT_NAME.toLowerCase()
    .replace(/[^a-z0-9._-]/g, '-')  // Replace invalid chars with -
    .replace(/---+/g, '--')          // Don't allow --- sequence
    .substring(0, 100);              // Max 100 chars

  log(`[STEP 3] GitHub Org:     ${GITHUB_ORG}`);
  log(`[STEP 3] GitHub Repo:    ${GITHUB_REPO}`);
  log(`[STEP 3] Project Name:   ${sanitizedProjectName}`);
  log(`[STEP 3] Branch:         main`);

  // Step 4: Create deployment
  log('[STEP 4] Creating Vercel deployment...');
  log('[STEP 4] Sending request to Vercel API...');

  let deployment;
  try {
    deployment = await vercel.deployments.createDeployment({
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
      skipAutoDetectionConfirmation: '1',
    });
  } catch (createError) {
    log(`[ERROR] Failed to create deployment!`);
    log(`[ERROR] Status: ${createError.status || 'unknown'}`);
    log(`[ERROR] Message: ${createError.message}`);
    if (createError.body) {
      log(`[ERROR] Body: ${JSON.stringify(createError.body, null, 2)}`);
    }
    throw createError;
  }

  log(`[STEP 4] Deployment created successfully!`);
  log(`[STEP 4] Deployment ID: ${deployment.id}`);
  log(`[STEP 4] Initial Status: ${deployment.status || deployment.state || 'unknown'}`);

  // Step 5: Wait for deployment
  log('[STEP 5] Waiting for deployment to complete...');
  const url = await waitForReady(vercel, deployment.id);

  // Step 6: Output URL
  log('========================================');
  log('DEPLOYMENT COMPLETE');
  log(`URL: ${url}`);
  log('========================================');

  // stdout: just the URL — this is what Python reads
  console.log(url);
}

main().catch(err => {
  console.error(`[FATAL ERROR] ${err.message}`);
  if (err.stack) {
    console.error(err.stack);
  }
  process.exit(1);
});
