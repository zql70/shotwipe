/* iOS LaunchImage：透明底 Logo（深海蓝底色由 storyboard 提供） */
const fs = require('fs');
const sharp = require('sharp');
const SRC = String.raw`C:\Users\killian\Pictures\Saved Pictures\shotwipe.svg`;
const OUT = String.raw`C:\Projects\shotwipe\app\ios\Runner\Assets.xcassets\LaunchImage.imageset`;
const svg = fs.readFileSync(SRC, 'utf8');
const inner = svg.replace(/^[\s\S]*?<svg[^>]*>/, '').replace(/<\/svg>[\s\S]*$/, '');
// 画布 176（设计主体约 100 宽，留边），主体放大到 ~78% 居中
const S = 1.1, tx = 88 - 77 * S, ty = 88 - 70 * S;
const mk = (px) => `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 176 176" width="${px}" height="${px}"><g transform="translate(${tx.toFixed(2)} ${ty.toFixed(2)}) scale(${S})">${inner}</g></svg>`;
(async () => {
  for (const [name, px] of [['LaunchImage.png', 176], ['LaunchImage@2x.png', 352], ['LaunchImage@3x.png', 528]]) {
    await sharp(Buffer.from(mk(px))).png().toFile(OUT + '/' + name);
    console.log('wrote', name);
  }
})();
