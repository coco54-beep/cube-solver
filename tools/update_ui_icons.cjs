// Export local Lucide SVGs as white PNG alpha masks for Kivy.
// Usage: node tools/update_ui_icons.cjs <lucide package directory> <sharp package directory>
const fs = require('fs');
const path = require('path');
const directory = process.argv[2];
const library = require(directory);
const sharp = require(process.argv[3]);
const out = path.resolve(__dirname, '../assets/icons/lucide');
const icons = {
  pick: 'Pipette', fill: 'PaintBucket', undo: 'Undo2', redo: 'Redo2',
  prev: 'ChevronLeft', next: 'ChevronRight', twist: 'Box', random: 'Shuffle',
  clear: 'Trash2', solve: 'Play', check: 'CircleCheck', scramble: 'ClipboardPaste',
  back: 'ArrowLeft', demo: 'BookOpen', zoom_in: 'Plus', zoom_out: 'Minus',
  first: 'SkipBack', last: 'SkipForward', reset: 'RotateCcw', pause: 'Pause',
  stop: 'Square', lock: 'LockKeyhole', unlock: 'LockKeyholeOpen',
  wide: 'Layers', single: 'Square', switch: 'Repeat2', cancel: 'X',
  done: 'Check', gear: 'Settings',
};
const escape = value => String(value).replace(/&/g, '&amp;').replace(/"/g, '&quot;')
  .replace(/</g, '&lt;');

async function main() {
  fs.mkdirSync(out, {recursive: true});
  for (const [name, exported] of Object.entries(icons)) {
    const nodes = library.icons[exported];
    if (!nodes) throw new Error(`Missing Lucide icon: ${exported}`);
    const body = nodes.map(([tag, attrs]) => `<${tag} ${Object.entries(attrs)
      .map(([key, value]) => `${key}="${escape(value)}"`).join(' ')}/>`).join('');
    const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" ` +
      `viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" ` +
      `stroke-linecap="round" stroke-linejoin="round">${body}</svg>`;
    fs.writeFileSync(path.join(out, `${name}.svg`), svg + '\n');
    await sharp(Buffer.from(svg.replace('currentColor', '#ffffff')), {density: 768})
      .resize(256, 256).png().toFile(path.join(out, `${name}.png`));
  }
  const version = JSON.parse(fs.readFileSync(path.join(directory, 'package.json'), 'utf8')).version;
  fs.copyFileSync(path.join(directory, 'LICENSE'), path.join(out, 'LICENSE.txt'));
  fs.writeFileSync(path.join(out, 'sources.json'), JSON.stringify({
    repository: 'https://github.com/lucide-icons/lucide', version,
    stroke_width: 1.8, icons,
  }, null, 2) + '\n');
  console.log(`Bundled ${Object.keys(icons).length} Lucide icons from version ${version}`);
}
main().catch(error => { console.error(error); process.exitCode = 1; });
