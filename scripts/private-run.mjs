// Keep private source and build configuration out of public Actions logs.
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import crypto from 'node:crypto';
import { spawn } from 'node:child_process';
import { once } from 'node:events';

const input = process.argv[2];
const key = Buffer.from(process.env.BUILD_LOG_KEY || '', 'base64');
if (!input || key.length !== 32) {
  console.error('Private build logging is not configured; refusing to run.');
  process.exit(1);
}
const logDir = path.join(process.env.RUNNER_TEMP || os.tmpdir(), 'tutu-build-logs');
fs.mkdirSync(logDir, { recursive: true, mode: 0o700 });
const nonce = crypto.randomBytes(12);
const id = `${Date.now()}-${crypto.randomBytes(6).toString('hex')}`;
const log = fs.createWriteStream(path.join(logDir, `${id}.enc`), { mode: 0o600 });
log.write(Buffer.from('TUTULOG1'));
log.write(nonce);
const cipher = crypto.createCipheriv('aes-256-gcm', key, nonce);
cipher.pipe(log, { end: false });
const isWindows = process.platform === 'win32';
const script = path.join(os.tmpdir(), `tutu-step-${id}.${isWindows ? 'ps1' : 'sh'}`);
let text = fs.readFileSync(input, 'utf8');
if (isWindows) {
  text = "$ErrorActionPreference = 'Stop'\n$PSNativeCommandUseErrorActionPreference = $true\n" + text +
    '\nif (Test-Path variable:LASTEXITCODE) { exit $LASTEXITCODE }\n';
}
fs.writeFileSync(script, text, { mode: 0o600 });
const command = isWindows ? 'pwsh' : 'bash';
const args = isWindows
  ? ['-NoLogo', '-NoProfile', '-NonInteractive', '-ExecutionPolicy', 'Bypass', '-File', script]
  : ['--noprofile', '--norc', '-e', '-o', 'pipefail', script];
const child = spawn(command, args, { stdio: ['ignore', 'pipe', 'pipe'], windowsHide: true });
child.stdout.on('data', chunk => cipher.write(chunk));
child.stderr.on('data', chunk => cipher.write(chunk));
let launchFailure = false;
const code = await new Promise(resolve => {
  child.on('error', () => { launchFailure = true; resolve(1); });
  child.on('close', value => resolve(Number.isInteger(value) ? value : 1));
});
const drained = once(cipher, 'end');
cipher.end();
await drained;
const saved = once(log, 'finish');
log.end(cipher.getAuthTag());
await saved;
fs.unlinkSync(script);
if (code === 0) console.log('Private build step succeeded; encrypted diagnostics saved.');
else console.error(launchFailure
  ? 'Private build step could not launch; inspect encrypted diagnostics.'
  : `Private build step failed (exit ${code}); inspect encrypted diagnostics.`);
process.exitCode = code;
