// Fails the build when the server-only channel config reaches the browser.
// Client components must import @/lib/site-client, never @/lib/site: one client
// import of @/lib/site ships the whole generated config (club settings, the
// build layout and every locale's copy) in a JS chunk. Run after `next build`.
import fs from 'node:fs';
import path from 'node:path';

const STATIC_DIR = path.resolve('out', '_next', 'static');
// Keys that exist only in src/generated/site.json, never in site-client.json.
const SERVER_ONLY_KEYS = ['"contentDir"', '"brevoListId"', '"autoReply"', '"commitAs"', '"spokenName"', '"foundingDate"'];

function* jsFiles(dir) {
  for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
    const full = path.join(dir, entry.name);
    if (entry.isDirectory()) yield* jsFiles(full);
    else if (entry.name.endsWith('.js')) yield full;
  }
}

if (!fs.existsSync(STATIC_DIR)) {
  console.error(`[check-client-bundle] ${STATIC_DIR} is missing: run next build first`);
  process.exit(1);
}
const leaks = [];
let files = 0;
for (const file of jsFiles(STATIC_DIR)) {
  files += 1;
  const text = fs.readFileSync(file, 'utf8');
  const found = SERVER_ONLY_KEYS.filter((key) => text.includes(key));
  if (found.length) leaks.push(`${path.relative(process.cwd(), file)}: ${found.join(', ')}`);
}
if (leaks.length) {
  console.error('[check-client-bundle] server-only config reached the client bundle:');
  for (const leak of leaks) console.error(`  ${leak}`);
  console.error('A client component imports @/lib/site (directly or through @/lib/i18n). Use @/lib/site-client and @/lib/locales.');
  process.exit(1);
}
console.log(`[check-client-bundle] ${files} client scripts, no server-only config`);
