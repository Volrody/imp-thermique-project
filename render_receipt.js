#!/usr/bin/env node
const fs = require('fs');
const puppeteer = require('puppeteer');
const yargs = require('yargs/yargs');
const { hideBin } = require('yargs/helpers');

const argv = yargs(hideBin(process.argv))
  .option('html', { type: 'string', demandOption: true })
  .option('out', { type: 'string', default: 'receipt.png' })
  .option('width', { type: 'number', default: 512 })
  .argv;

(async () => {
  const browser = await puppeteer.launch({
    args: ['--no-sandbox', '--disable-setuid-sandbox'],
  });
  const page = await browser.newPage();

  const htmlContent = fs.readFileSync(argv.html, 'utf8');
  await page.setViewport({ width: argv.width, height: 800 });
  await page.setContent(htmlContent, { waitUntil: 'networkidle0' });

  let height = await page.evaluate(() => {
    const el = document.getElementById('ticket');
    return el ? el.scrollHeight : document.body.scrollHeight;
  });

  height = Math.max(height, 600); // hauteur min 600 px

  console.log("Hauteur détectée (avec min 600) :", height);
  await page.setViewport({ width: argv.width, height });

  await page.screenshot({ path: argv.out, omitBackground: false });
  await browser.close();
  console.log(`✅ Image générée : ${argv.out} (${argv.width}px x ${height}px)`);
})();