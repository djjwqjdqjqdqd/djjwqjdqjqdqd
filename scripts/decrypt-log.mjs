import fs from 'node:fs';
import crypto from 'node:crypto';
const [input, output, option] = process.argv.slice(2);
const key = Buffer.from(process.env.BUILD_LOG_KEY || '', 'base64');
if (!input || !output || key.length !== 32) {
  throw new Error('Usage: BUILD_LOG_KEY=<secret> node scripts/decrypt-log.mjs input.enc output.log');
}
const bytes = fs.readFileSync(input);
const magic = bytes.subarray(0, 8).toString();
let clear;
if (magic === 'BLDLOG01') {
  const decipher = crypto.createDecipheriv('aes-256-gcm', key, bytes.subarray(8, 20));
  decipher.setAuthTag(bytes.subarray(-16));
  clear = Buffer.concat([decipher.update(bytes.subarray(20, -16)), decipher.final()]);
} else if (magic === 'BLDLOG02') {
  let offset = 8, sequence = 0n, complete = false;
  const records = [];
  while (offset + 4 <= bytes.length) {
    const length = bytes.readUInt32BE(offset);
    if (length < 28 || length > 16 * 1024 * 1024) throw new Error('Invalid record length');
    if (offset + 4 + length > bytes.length) break;
    const record = bytes.subarray(offset + 4, offset + 4 + length);
    const decipher = crypto.createDecipheriv('aes-256-gcm', key, record.subarray(0, 12));
    const aad = Buffer.alloc(8);
    aad.writeBigUInt64BE(sequence++);
    decipher.setAAD(aad);
    decipher.setAuthTag(record.subarray(-16));
    const decoded = Buffer.concat([decipher.update(record.subarray(12, -16)), decipher.final()]);
    offset += 4 + length;
    if (decoded.length === 0) { complete = true; break; }
    records.push(decoded);
  }
  if (complete && offset !== bytes.length) throw new Error('Unexpected trailing log data');
  if (!complete && option !== '--allow-incomplete') throw new Error('Interrupted log; use --allow-incomplete to recover authenticated records');
  if (!complete) console.error('Recovered authenticated records from an interrupted build step.');
  clear = Buffer.concat(records);
} else throw new Error('Unknown log format');
fs.writeFileSync(output, clear, { mode: 0o600 });
console.log('Decrypted log saved locally. Do not upload the plaintext log.');
