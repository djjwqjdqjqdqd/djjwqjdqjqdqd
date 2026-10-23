import fs from 'node:fs';
import crypto from 'node:crypto';
const [input, output] = process.argv.slice(2);
const key = Buffer.from(process.env.BUILD_LOG_KEY || '', 'base64');
if (!input || !output || key.length !== 32) {
  throw new Error('Usage: BUILD_LOG_KEY=<secret> node scripts/decrypt-log.mjs input.enc output.log');
}
const bytes = fs.readFileSync(input);
if (bytes.subarray(0, 8).toString() !== 'TUTULOG1') throw new Error('Unknown log format');
const decipher = crypto.createDecipheriv('aes-256-gcm', key, bytes.subarray(8, 20));
decipher.setAuthTag(bytes.subarray(-16));
const clear = Buffer.concat([decipher.update(bytes.subarray(20, -16)), decipher.final()]);
fs.writeFileSync(output, clear, { mode: 0o600 });
console.log('Decrypted log saved locally. Do not upload the plaintext log.');
