import { mkdir, readdir, writeFile, readFile } from 'node:fs/promises';
import { join } from 'node:path';

const projectRoot = process.cwd();
const pagesRoot = join(projectRoot, 'src', 'assets', 'pages');
const srcAssetsRoot = join(projectRoot, 'src', 'assets');
const srcPagesIndexPath = join(srcAssetsRoot, 'pages-index.json');

function parseNumericComment(content, key, fallback) {
  const match = content.match(new RegExp(`${key}:\\s*(\\d+)`));
  return match ? parseInt(match[1], 10) : fallback;
}

async function buildPagesIndex() {
  const categoryEntries = await readdir(pagesRoot, { withFileTypes: true });

  const categories = await Promise.all(
    categoryEntries
      .filter((entry) => entry.isDirectory())
      .map(async (entry) => {
        const categoryPath = join(pagesRoot, entry.name);
        const pageEntries = await readdir(categoryPath, { withFileTypes: true });

        const mdFiles = pageEntries.filter((p) => p.isFile() && p.name.endsWith('.md'));

        // Read each markdown file to extract its page order.
        const pagesWithOrder = await Promise.all(
          mdFiles.map(async (pageEntry) => {
            const filePath = join(categoryPath, pageEntry.name);
            const content = await readFile(filePath, 'utf-8');
            const order = parseNumericComment(content, 'order', 999);

            return {
              name: pageEntry.name.slice(0, -3),
              order,
            };
          })
        );

        // Sort pages numerically by their `order` comment.
        pagesWithOrder.sort((left, right) => left.order - right.order);

        const indexEntry = mdFiles.find((pageEntry) => pageEntry.name === 'index.md');
        const indexContent = indexEntry ? await readFile(join(categoryPath, indexEntry.name), 'utf-8') : '';
        const categoryOrder = parseNumericComment(indexContent, 'category_order', 999);

        return {
          name: entry.name,
          order: categoryOrder,
          pages: pagesWithOrder.map((page) => page.name),
        };
      })
  );

  categories.sort((left, right) => left.order - right.order || left.name.localeCompare(right.name));

  await mkdir(srcAssetsRoot, { recursive: true });
  await writeFile(srcPagesIndexPath, JSON.stringify({ categories }, null, 2));
}

await buildPagesIndex();
