/**
 * Vercel deploy tool — uses the Vercel REST API directly (no SDK).
 *
 * 1. Creates a git-sourced deployment via POST /v13/deployments
 * 2. Polls until state is READY (or errors / times out)
 * 3. Writes the live URL to stdout (one line — Python captures this)
 *
 * All other output goes to stderr so it doesn't pollute the URL capture.
 *
 * Requires: VERCEL_TOKEN env var
 */

const API_BASE = 'https://api.vercel.com';

// ---------------------------------------------------------------------------
// Config
// ---------------------------------------------------------------------------
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

async function vercelAPI(method, path, body) {
  const opts = {
    method,
    headers: {
      'Authorization': `Bearer ${process.env.VERCEL_TOKEN}`,
      'Content-Type': 'application/json',
    },
  };
  if (body) opts.body = JSON.stringify(body);

  const res = await fetch(`${API_BASE}${path}`, opts);
  const data = await res.json();

  if (!res.ok) {
    const err = new Error(data.error?.message || `API error ${res.status}`);
    err.status = res.status;
    err.body = data;
    throw err;
  }
  return data;
}

// ---------------------------------------------------------------------------
// Poll until READY
// ---------------------------------------------------------------------------
async function waitForReady(deploymentId) {
  let attempt = 0;

  while (true) {
    attempt++;
    log(`[POLL ${attempt}] Checking deployment status...`);

    try {
      const dep = await vercelAPI('GET', `/v13/deployments/${deploymentId}`);
      const state = (dep.readyState || dep.state || dep.status || 'UNKNOWN').toUpperCase();

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
      if (pollError.message.includes('state=')) throw pollError;
      log(`[POLL ${attempt}] Error checking status: ${pollError.message}`);
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
    throw new Error('VERCEL_TOKEN is not set');
  }
  const tokenPreview = process.env.VERCEL_TOKEN.slice(0, 8) + '...' + process.env.VERCEL_TOKEN.slice(-4);
  log(`[STEP 1] VERCEL_TOKEN is set: ${tokenPreview}`);

  // Step 2: Prepare project name
  log('[STEP 2] Preparing deployment parameters...');
  const sanitizedProjectName = PROJECT_NAME.toLowerCase()
    .replace(/[^a-z0-9._-]/g, '-')
    .replace(/---+/g, '--')
    .substring(0, 100);

  log(`[STEP 2] GitHub Org:     ${GITHUB_ORG}`);
  log(`[STEP 2] GitHub Repo:    ${GITHUB_REPO}`);
  log(`[STEP 2] Project Name:   ${sanitizedProjectName}`);
  log(`[STEP 2] Branch:         main`);

  // Step 3: Create deployment
  log('[STEP 3] Creating Vercel deployment...');

  let deployment;
  try {
    deployment = await vercelAPI('POST', '/v13/deployments?skipAutoDetectionConfirmation=1', {
      name: sanitizedProjectName,
      target: 'production',
      gitSource: {
        type: 'github',
        repo: GITHUB_REPO,
        ref: 'main',
        org: GITHUB_ORG,
      },
      projectSettings: {
        framework: null,
      },
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

  log(`[STEP 3] Deployment created successfully!`);
  log(`[STEP 3] Deployment ID: ${deployment.id}`);
  log(`[STEP 3] Initial Status: ${deployment.status || deployment.readyState || 'unknown'}`);

  // Step 4: Wait for deployment
  log('[STEP 4] Waiting for deployment to complete...');
  const url = await waitForReady(deployment.id);

  // Step 5: Output URL
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
