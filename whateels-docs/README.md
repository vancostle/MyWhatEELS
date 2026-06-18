# WhatEELS Documentation

This repository contains the Angular documentation website for **WhatEELS**, an application for Electron Energy Loss Spectroscopy (EELS) workflows.

The site is built as a standalone Angular app. Documentation pages are written in Markdown and loaded from `src/assets/pages`.

## Tech Stack

- Angular 21
- Angular Router
- Angular SSR configuration
- `ngx-markdown` for rendering Markdown documentation pages
- Font Awesome for icons
- GitHub Pages deployment support through `angular-cli-ghpages`

## Project Structure

```text
.
├── angular.json
├── package.json
├── package-lock.json
├── scripts/
│   ├── generate-pages-index.mjs
│   └── prepare-ghpages.mjs
├── public/
│   ├── favicon.ico
│   └── images/
└── src/
    ├── index.html
    ├── main.ts
    ├── main.server.ts
    ├── server.ts
    ├── styles.css
    ├── app/
    │   ├── app.routes.ts
    │   ├── doc/
    │   └── shared/
    └── assets/
        ├── pages-index.json
        └── pages/
```

Important folders:

- `src/app`: Angular components, routes, services, and UI logic.
- `src/assets/pages`: Markdown files used as documentation pages.
- `src/assets/pages-index.json`: Generated index used by the sidebar/navigation.
- `scripts`: Build helper scripts for page indexing and GitHub Pages output.
- `public`: Static public assets such as the favicon and images.

## Requirements

Install Node.js and npm before running the project.

This project currently declares:

```text
npm 11.14.1
```

Using the npm version from `packageManager` is recommended.

## Install Dependencies

```bash
npm install
```

Do not commit `node_modules`. It is generated locally by npm.

## Run Locally

```bash
npm start
```

This runs:

```bash
node scripts/generate-pages-index.mjs
ng serve
```

The page index is regenerated before the dev server starts, so new Markdown pages should appear in the sidebar.

## Build

```bash
npm run build
```

This runs:

```bash
node scripts/generate-pages-index.mjs
ng build
```

The production build output is generated under:

```text
dist/whateels-docs/
```

## GitHub Pages Build

```bash
npm run build:ghpages
```

This builds the app with:

```bash
ng build --base-href /whateels-docs/
```

Then it runs `scripts/prepare-ghpages.mjs`, which prepares the browser output for GitHub Pages by copying the client HTML fallback and page index.

If the final deployed path changes, update the `--base-href` value in `package.json`.

Examples:

```bash
ng build --base-href /whateels-docs/
ng build --base-href /docs/
ng build --base-href /
```

## Deploy To GitHub Pages

```bash
npm run deploy:ghpages
```

This command builds the GitHub Pages version and deploys:

```text
dist/whateels-docs/browser
```

## Documentation Pages

Documentation content lives in:

```text
src/assets/pages/
```

Each folder is treated as a documentation category. Each Markdown file is treated as a page.

Example:

```text
src/assets/pages/introduction/whateels.md
```

is loaded through a route like:

```text
/introduction/whateels
```

Page and category ordering is controlled with comments inside Markdown files:

```markdown
<!-- category_order: 1 -->
<!-- order: 1 -->
```

The `scripts/generate-pages-index.mjs` script reads those comments and generates:

```text
src/assets/pages-index.json
```

Run this manually if needed:

```bash
node scripts/generate-pages-index.mjs
```

## Routing

Routes are defined in:

```text
src/app/app.routes.ts
```

The current routing model is:

```text
/ -> redirects to /introduction/whateels
/:category/:page -> renders the docs page
```

The `Main` component reads the route parameters and loads the matching Markdown file from `src/assets/pages`.

## SEO Notes

Global fallback SEO metadata is defined in:

```text
src/index.html
```

This includes the default title, description, robots tag, Open Graph metadata, and Twitter card metadata.

For stronger SEO, future work should add dynamic per-page metadata using Angular's `Title` and `Meta` services when each Markdown page loads.

## Moving Into Another Repository

If this project is moved into the main WhatEELS repository, keep it isolated as a `docs` subproject.

Recommended structure:

```text
WhatEELS/
├── docs/
│   ├── angular.json
│   ├── package.json
│   ├── package-lock.json
│   ├── tsconfig.json
│   ├── tsconfig.app.json
│   ├── tsconfig.spec.json
│   ├── scripts/
│   ├── public/
│   └── src/
└── other WhatEELS project files...
```

Move these into `docs`:

- `angular.json`
- `package.json`
- `package-lock.json`
- `tsconfig*.json`
- `src`
- `public`
- `scripts`
- docs-specific config files such as `.editorconfig` and `.prettierrc`

Do not move generated folders:

- `node_modules`
- `dist`
- `.angular`

After moving, run commands from inside `docs`:

```bash
cd docs
npm install
npm run build
```

If GitHub Actions are used, workflow files must stay in the repository root under `.github/workflows`. Configure the workflow to run commands in `docs`.

Example:

```yaml
- run: npm ci
  working-directory: docs

- run: npm run build
  working-directory: docs
```

## Development Notes

- Keep Markdown page names and route slugs simple. Spaces are converted to hyphenated URL segments.
- When adding a new docs page, add the Markdown file under `src/assets/pages`, include an `order` comment, and regenerate `pages-index.json`.
- Keep assets that must be copied directly by Angular in `public`.
- Keep docs content assets and generated page data in `src/assets`.
- If navigation does not update after adding a page, rerun `node scripts/generate-pages-index.mjs`.
- If GitHub Pages routes return 404 on refresh, check `scripts/prepare-ghpages.mjs` and the `build:ghpages` output.

## Useful Commands

```bash
npm start
npm run build
npm run build:ghpages
npm run deploy:ghpages
npm test
```