import { copyFile, mkdir } from 'node:fs/promises';
import { join } from 'node:path';

const projectRoot = process.cwd();
const srcPagesIndexPath = join(projectRoot, 'src', 'assets', 'pages-index.json');
const browserRoot = join(projectRoot, 'dist', 'whateels-docs', 'browser');
const pagesIndexPath = join(browserRoot, 'assets', 'pages-index.json');
const indexCsrHtmlPath = join(browserRoot, 'index.csr.html');
const indexHtmlPath = join(browserRoot, 'index.html');
const notFoundHtmlPath = join(browserRoot, '404.html');

async function copyPagesIndex() {
  await mkdir(join(browserRoot, 'assets'), { recursive: true });
  await copyFile(srcPagesIndexPath, pagesIndexPath);
}

async function createSpaFallback() {
  await copyFile(indexCsrHtmlPath, indexHtmlPath);
  await copyFile(indexCsrHtmlPath, notFoundHtmlPath);
}

await copyPagesIndex();
await createSpaFallback();