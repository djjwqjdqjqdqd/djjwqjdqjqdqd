import fs from 'node:fs';
const run = process.env.SOURCE_RUN_ID || '';
if (!/^\d+$/.test(run)) throw new Error('Invalid package run identifier');
const response = await fetch(`https://api.github.com/repos/${process.env.GITHUB_REPOSITORY}/actions/runs/${run}/artifacts?per_page=100`, {
  headers: { Authorization: `Bearer ${process.env.GH_TOKEN}`, Accept: 'application/vnd.github+json' },
});
if (!response.ok) throw new Error(`Cannot inspect package artifacts (HTTP ${response.status})`);
const data = await response.json();
const available = data.artifacts.some(artifact => artifact.name === 'package-android' && !artifact.expired);
fs.appendFileSync(process.env.GITHUB_OUTPUT, `available=${available}\nrun_id=${run}\n`);
console.log(available ? 'Package is available for signature verification.' : 'No matching package; signature verification is skipped.');
