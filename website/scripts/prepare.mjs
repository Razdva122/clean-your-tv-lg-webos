import {
  mkdirSync,
  copyFileSync,
  rmSync,
  readFileSync,
  writeFileSync,
} from "node:fs";
import { execFileSync } from "node:child_process";
import { fileURLToPath } from "node:url";
const root = fileURLToPath(new URL("../../", import.meta.url));
const pub = fileURLToPath(new URL("../public/", import.meta.url));
// This directory belongs to this build; never remove repository or user files.
rmSync(pub, { recursive: true, force: true });
mkdirSync(pub + "assets", { recursive: true });
execFileSync(
  process.env.PYTHON || "python3",
  ["scripts/preview.py", "--build", pub + "demo"],
  { cwd: root, stdio: "inherit" },
);
for (const page of [
  "index.html",
  "launcher/index.html",
  "root-launcher/index.html",
]) {
  const path = pub + "demo/" + page;
  writeFileSync(
    path,
    readFileSync(path, "utf8")
      .replace(
        '<html lang="en">',
        '<html lang="en">\n<meta name="robots" content="noindex">',
      )
      .replace("<head>", '<head>\n<meta name="robots" content="noindex">'),
  );
}
for (const name of ["logo-dark.svg", "symbol-color.svg"])
  copyFileSync(root + "assets/brand/" + name, pub + "assets/" + name);
for (const theme of ["classic", "alpine", "ribbon"])
  copyFileSync(
    root + "docs/launcher-" + theme + ".jpg",
    pub + "assets/" + theme + ".jpg",
  );
writeFileSync(pub + ".nojekyll", "");
