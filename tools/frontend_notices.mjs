// Preserve upstream notices for the pinned production dependency graph.
import fs from 'node:fs';
import path from 'node:path';
const root=path.resolve(import.meta.dirname,'..');
const lock=JSON.parse(fs.readFileSync(path.join(root,'package-lock.json'),'utf8'));
let result='ROEFS ONE frontend third-party notices\nGenerated from package-lock.json; upstream terms are reproduced unchanged.\n';
for(const [dir,entry] of Object.entries(lock.packages)) {
  if(!dir||entry.dev)continue;
  const base=path.join(root,dir),manifest=path.join(base,'package.json');
  if(!fs.existsSync(manifest))continue;
  const pkg=JSON.parse(fs.readFileSync(manifest,'utf8'));
  const licenses=fs.readdirSync(base).filter(name=>/^(licen[cs]e|copying)(\.|$)/i.test(name)&&fs.statSync(path.join(base,name)).isFile());
  result+=`\n${'='.repeat(70)}\n${pkg.name} ${pkg.version}\nDeclared license: ${pkg.license||'See upstream terms'}\n`;
  for(const name of licenses)result+=`\n${name}\n${fs.readFileSync(path.join(base,name),'utf8')}\n`;
}
fs.writeFileSync(path.join(root,'THIRD-PARTY-LICENSES.txt'),result);
