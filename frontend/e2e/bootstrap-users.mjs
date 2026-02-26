import { spawnSync } from 'node:child_process';
import { writeFileSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

function runDockerCompose(args, extraEnv = {}) {
  const result = spawnSync('docker', ['compose', ...args], {
    stdio: 'inherit',
    env: { ...process.env, ...extraEnv },
  });
  if (result.status !== 0) {
    throw new Error(`docker compose ${args.join(' ')} failed with exit code ${result.status}`);
  }
}

function runDockerComposeCapture(args, extraEnv = {}) {
  const result = spawnSync('docker', ['compose', ...args], {
    stdio: 'pipe',
    encoding: 'utf-8',
    env: { ...process.env, ...extraEnv },
  });
  if (result.status !== 0) {
    const stderr = (result.stderr || '').trim();
    throw new Error(`docker compose ${args.join(' ')} failed: ${stderr || result.status}`);
  }
  return (result.stdout || '').trim();
}

function isBootstrapEnabled() {
  const raw = String(process.env.NBMS_E2E_BOOTSTRAP ?? '1').toLowerCase();
  return !['0', 'false', 'no'].includes(raw);
}

function main() {
  if (!isBootstrapEnabled()) {
    console.log('NBMS_E2E_BOOTSTRAP disabled; skipping user bootstrap.');
    return;
  }

  const adminUsername = process.env.PLAYWRIGHT_USERNAME || 'SystemAdmin';
  const adminPassword = process.env.PLAYWRIGHT_PASSWORD || 'SystemAdmin';
  const adminEmail = process.env.PLAYWRIGHT_ADMIN_EMAIL || 'systemadmin@demo.nbms.local';
  const contributorUsername = process.env.PLAYWRIGHT_CONTRIBUTOR_USERNAME || 'Contributor';
  const reviewerUsername = process.env.PLAYWRIGHT_REVIEWER_USERNAME || 'Reviewer';
  const publicUsername = process.env.PLAYWRIGHT_PUBLIC_USERNAME || 'PublicUser';

  runDockerCompose(['ps', '--status', 'running', 'backend']);

  // Reset runtime throttling/cache state to keep login e2e deterministic between runs.
  runDockerCompose([
    'exec',
    'backend',
    'python',
    'manage.py',
    'shell',
    '-c',
    "from django.core.cache import cache; cache.clear(); print('cache-cleared')",
  ]);

  runDockerCompose(
    [
      'exec',
      '-e',
      `NBMS_ADMIN_USERNAME=${adminUsername}`,
      '-e',
      `NBMS_ADMIN_EMAIL=${adminEmail}`,
      '-e',
      `NBMS_ADMIN_PASSWORD=${adminPassword}`,
      'backend',
      'python',
      'manage.py',
      'ensure_system_admin',
    ],
    {}
  );

  runDockerCompose(
    [
      'exec',
      '-e',
      'SEED_DEMO_USERS=1',
      '-e',
      'ALLOW_INSECURE_DEMO_PASSWORDS=1',
      '-e',
      'ENVIRONMENT=dev',
      '-e',
      'DJANGO_DEBUG=true',
      'backend',
      'python',
      'manage.py',
      'seed_demo_users',
    ],
    {}
  );

  const sessionUsers = [adminUsername, contributorUsername, reviewerUsername, publicUsername];
  const sessionOutput = runDockerComposeCapture([
    'exec',
    'backend',
    'python',
    'manage.py',
    'issue_e2e_sessions',
    '--users',
    ...sessionUsers,
  ]);
  if (String(process.env.NBMS_E2E_DEBUG || '0') === '1') {
    console.log(`SESSION_OUTPUT\n${sessionOutput}`);
  }
  const sessionJsonLine = sessionOutput
    .split(/\r?\n/)
    .map((line) => line.trim())
    .filter((line) => line.startsWith('{') && line.endsWith('}'))
    .at(-1);
  if (!sessionJsonLine) {
    throw new Error(`Unable to parse generated session keys from output: ${sessionOutput}`);
  }
  const sessionMap = JSON.parse(sessionJsonLine);
  const scriptDir = dirname(fileURLToPath(import.meta.url));
  const outputPath = resolve(scriptDir, '.session-keys.json');
  writeFileSync(
    outputPath,
    `${JSON.stringify({ generated_at: new Date().toISOString(), sessions: sessionMap }, null, 2)}\n`,
    'utf-8'
  );
  console.log(`Wrote ${outputPath}`);
}

try {
  main();
} catch (error) {
  console.error(error instanceof Error ? error.message : String(error));
  process.exit(1);
}
