// Rejects raw colour values in components (design token rule: semantic tokens only).
// Only app/tokens.css may define colours. Exit code 1 lists every offending line.
import { readdirSync, readFileSync, statSync } from "node:fs";
import { join, relative } from "node:path";

const ROOT = new URL("..", import.meta.url).pathname.replace(/^\/([A-Za-z]:)/, "$1");
const SCAN = ["app", "components", "lib"];
const ALLOWED = new Set(["app/tokens.css"]);
const EXTENSIONS = /\.(css|tsx?|jsx?)$/;

// #abc, #aabbcc, #aabbccdd, rgb()/rgba()/hsl()/hsla()
const RAW_COLOR = /#[0-9a-fA-F]{3,8}\b|\b(?:rgba?|hsla?)\s*\(/;

function* walk(dir) {
  for (const name of readdirSync(dir)) {
    const path = join(dir, name);
    if (statSync(path).isDirectory()) yield* walk(path);
    else if (EXTENSIONS.test(name)) yield path;
  }
}

const problems = [];
for (const top of SCAN) {
  let files;
  try {
    files = [...walk(join(ROOT, top))];
  } catch {
    continue; // folder does not exist yet
  }
  for (const file of files) {
    const rel = relative(ROOT, file).replaceAll("\\", "/");
    if (ALLOWED.has(rel)) continue;
    readFileSync(file, "utf8")
      .split("\n")
      .forEach((line, i) => {
        if (RAW_COLOR.test(line)) problems.push(`${rel}:${i + 1}: ${line.trim()}`);
      });
  }
}

if (problems.length) {
  console.error("Raw colour values found. Use semantic tokens (var(--color-*)) instead:\n");
  console.error(problems.join("\n"));
  process.exit(1);
}
console.log("No raw colour values found.");
