// Keep private source and build configuration out of public Actions logs.
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import crypto from 'node:crypto';
import { spawn } from 'node:child_process';

const input = process.argv[2];
const key = Buffer.from(process.env.BUILD_LOG_KEY || '', 'base64');
if (!input || key.length !== 32) {
  console.error('Private build logging is not configured; refusing to run.');
  process.exit(1);
}
const logDir = path.join(process.env.RUNNER_TEMP || os.tmpdir(), 'build-logs');
fs.mkdirSync(logDir, { recursive: true, mode: 0o700 });
const id = `${Date.now()}-${crypto.randomBytes(6).toString('hex')}`;
const log = fs.openSync(path.join(logDir, `${id}.enc`), 'wx', 0o600);
fs.writeSync(log, Buffer.from('BLDLOG02'));
let sequence = 0n;
function saveRecord(clear) {
  const nonce = crypto.randomBytes(12);
  const aad = Buffer.alloc(8);
  aad.writeBigUInt64BE(sequence++);
  const cipher = crypto.createCipheriv('aes-256-gcm', key, nonce);
  cipher.setAAD(aad);
  const encrypted = Buffer.concat([cipher.update(clear), cipher.final()]);
  const length = Buffer.alloc(4);
  length.writeUInt32BE(encrypted.length + 28);
  // Authenticate each record immediately, so a killed job retains readable logs.
  fs.writeSync(log, Buffer.concat([length, nonce, encrypted, cipher.getAuthTag()]));
}
const isWindows = process.platform === 'win32';
const script = path.join(os.tmpdir(), `build-step-${id}.${isWindows ? 'ps1' : 'sh'}`);
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
child.stdout.on('data', saveRecord);
child.stderr.on('data', saveRecord);
const started = Date.now();
const heartbeat = setInterval(() => console.log(`Private build step running (${Math.floor((Date.now() - started) / 60000)} min).`), 60000);
let launchFailure = false;
const code = await new Promise(resolve => {
  child.on('error', () => { launchFailure = true; resolve(1); });
  child.on('close', value => resolve(Number.isInteger(value) ? value : 1));
});
clearInterval(heartbeat);
saveRecord(Buffer.alloc(0));
fs.closeSync(log);
fs.unlinkSync(script);
if (code === 0) console.log('Private build step succeeded; encrypted diagnostics saved.');
else console.error(launchFailure
  ? 'Private build step could not launch; inspect encrypted diagnostics.'
  : `Private build step failed (exit ${code}); inspect encrypted diagnostics.`);
process.exitCode = code;
