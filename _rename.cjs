const fs = require("fs");

// 1. Delete LICENSE
try { fs.unlinkSync("LICENSE"); console.log("deleted LICENSE"); } catch(e) {}

// 2. pyproject.toml updates
let ppt = fs.readFileSync("pyproject.toml", "utf8");
ppt = ppt
  .replace(/name = "fastapi-fullstack"/, 'name = "framework-agent-python"')
  .replace(/description = "[^"]+"/, 'description = "Agent scaffolding framework for FastAPI + Next.js — internal AI agent project generator."')
  .replace(/authors = \[[^\]]*\]/, 'authors = [{ name = "Company", email = "dev@company.com" }]')
  .replace(/Homepage = "[^"]+"/, 'Homepage = "https://git.company.com/framework-agent-python"')
  .replace(/Documentation = "[^"]+"/, 'Documentation = "https://git.company.com/framework-agent-python#readme"')
  .replace(/Repository = "[^"]+"/, 'Repository = "https://git.company.com/framework-agent-python"')
  .replace(/fastapi-fullstack = "fastapi_gen.cli:main"/, 'framework-agent-python = "fastapi_gen.cli:main"')
  .replace(/"MIT License"/, '"Proprietary"')
  .replace(/license = \{ text = "MIT" \}/, 'license = { text = "Proprietary" }');
fs.writeFileSync("pyproject.toml", ppt, "utf8");
console.log("pyproject.toml updated");

// 3. Scan for project name references in key .md files
const dirs = [".", "docs", "template/{{cookiecutter.project_slug}}"];
const renames = [
  ["full-stack-ai-agent-template", "framework-agent-python"],
  ["fastapi-fullstack", "framework-agent-python"],
];
const mdFiles = [];
dirs.forEach(d => {
  try {
    const items = fs.readdirSync(d, { withFileTypes: true });
    items.forEach(item => {
      if (item.isFile() && (item.name.endsWith(".md") || item.name === "mkdocs.yml" || item.name === "AGENTS.md" || item.name === "CLAUDE.md")) {
        mdFiles.push(d + "/" + item.name);
      }
    });
  } catch(e) {}
});
// Also handle root-level .md that readdir already covers
// Add the template root files separately
["README.md","AGENTS.md","CLAUDE.md","CONTRIBUTING.md","GOVERNANCE.md","SECURITY.md","mkdocs.yml"].forEach(f => {
  if (!mdFiles.includes(f) && fs.existsSync(f)) mdFiles.push(f);
});

let replaced = 0;
mdFiles.forEach(fp => {
  try {
    let c = fs.readFileSync(fp, "utf8");
    let orig = c;
    renames.forEach(([from, to]) => {
      c = c.split(from).join(to);
    });
    if (c !== orig) {
      fs.writeFileSync(fp, c, "utf8");
      replaced++;
      console.log("  updated: " + fp);
    }
  } catch(e) {}
});
console.log("replaced references in " + replaced + " files");
