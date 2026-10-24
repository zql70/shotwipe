/* 从 shotwipe.svg 生成全套 App 图标。
 *
 * 布局说明：
 * - 源 SVG 无背景，画布 152，设计主体 bbox 约 x[27,127] y[20,119]，中心约 (77,70)。
 * - 全出血图标（iOS / Android 传统）：铺 #10263C 深海蓝底 + 原设计。
 * - Android 自适应前景：108dp 画布，主体缩放到 ~62%（66dp 安全区内）居中，
 *   背景层由 XML 纯色提供；单色层取前景 alpha 填白（Android 13+ 主题图标）。
 */
const fs = require('fs');
const path = require('path');
const sharp = require('sharp');

const SRC = String.raw`C:\Users\killian\Pictures\Saved Pictures\shotwipe.svg`;
const APP = String.raw`C:\Projects\shotwipe\app`;
const BG = '#10263C';

const svg = fs.readFileSync(SRC, 'utf8');
// 取 <svg ...> 与 </svg> 之间的内容
const inner = svg.replace(/^[\s\S]*?<svg[^>]*>/, '').replace(/<\/svg>[\s\S]*$/, '');
const INNER = inner; // defs + 主体形状

// 全出血图标：主体缩到 ~54% 画布宽（bbox 100 → 84），居中于 (76,76)
const FULL_SCALE = 0.84;
const ftx = 76 - 77 * FULL_SCALE;
const fty = 76 - 70 * FULL_SCALE;
const fullSvg = (px) =>
  `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 152 152" width="${px}" height="${px}">` +
  `<rect width="152" height="152" fill="${BG}"/>` +
  `<g transform="translate(${ftx.toFixed(2)} ${fty.toFixed(2)}) scale(${FULL_SCALE})">${INNER}</g></svg>`;

// 自适应前景：主体 ~55 units（安全区 66 内留呼吸），中心 77,70 → 平移到 54,54
const FG_SCALE = 0.55;
const tx = 54 - 77 * FG_SCALE;
const ty = 54 - 70 * FG_SCALE;
const fgSvg = (px) =>
  `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 108 108" width="${px}" height="${px}">` +
  `<g transform="translate(${tx.toFixed(2)} ${ty.toFixed(2)}) scale(${FG_SCALE})">${INNER}</g></svg>`;

const render = async (svgStr, out) => {
  await sharp(Buffer.from(svgStr)).png().toFile(out);
  console.log('wrote', out);
};

async function main() {
  // ---- iOS AppIcon（沿用 Contents.json 的文件名）----
  const iosDir = path.join(APP, 'ios', 'Runner', 'Assets.xcassets', 'AppIcon.appiconset');
  const iosSizes = {
    'Icon-App-20x20@1x.png': 20,
    'Icon-App-20x20@2x.png': 40,
    'Icon-App-20x20@3x.png': 60,
    'Icon-App-29x29@1x.png': 29,
    'Icon-App-29x29@2x.png': 58,
    'Icon-App-29x29@3x.png': 87,
    'Icon-App-40x40@1x.png': 40,
    'Icon-App-40x40@2x.png': 80,
    'Icon-App-40x40@3x.png': 120,
    'Icon-App-60x60@2x.png': 120,
    'Icon-App-60x60@3x.png': 180,
    'Icon-App-76x76@1x.png': 76,
    'Icon-App-76x76@2x.png': 152,
    'Icon-App-83.5x83.5@2x.png': 167,
    'Icon-App-1024x1024@1x.png': 1024,
  };
  for (const [name, px] of Object.entries(iosSizes)) {
    await render(fullSvg(px), path.join(iosDir, name));
  }

  // ---- Android 传统 mipmap ----
  const legacy = { mdpi: 48, hdpi: 72, xhdpi: 96, xxhdpi: 144, xxxhdpi: 192 };
  for (const [dpi, px] of Object.entries(legacy)) {
    await render(fullSvg(px), path.join(APP, 'android', 'app', 'src', 'main', 'res', `mipmap-${dpi}`, 'ic_launcher.png'));
  }

  // ---- Android 自适应前景 + 单色层 ----
  const fgPx = { mdpi: 108, hdpi: 162, xhdpi: 216, xxhdpi: 324, xxxhdpi: 432 };
  for (const [dpi, px] of Object.entries(fgPx)) {
    const dir = path.join(APP, 'android', 'app', 'src', 'main', 'res', `mipmap-${dpi}`);
    await render(fgSvg(px), path.join(dir, 'ic_launcher_foreground.png'));
    // 单色层：同几何，全部填白（只留 alpha）
    const { data, info } = await sharp(Buffer.from(fgSvg(px)))
      .ensureAlpha().raw().toBuffer({ resolveWithObject: true });
    const mono = Buffer.alloc(data.length);
    for (let i = 0; i < data.length; i += 4) {
      mono[i] = 255; mono[i + 1] = 255; mono[i + 2] = 255; mono[i + 3] = data[i + 3];
    }
    await sharp(mono, { raw: { width: info.width, height: info.height, channels: 4 } })
      .png().toFile(path.join(dir, 'ic_launcher_mono.png'));
    console.log('wrote', path.join(dir, 'ic_launcher_mono.png'));
  }

  // ---- 预览图 ----
  await render(fullSvg(512), 'preview_full.png');
  await render(fgSvg(512), 'preview_fg.png');
  console.log('done');
}

main().catch((e) => { console.error(e); process.exit(1); });
