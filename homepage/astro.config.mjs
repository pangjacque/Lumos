import { defineConfig } from 'astro/config';

// Hosted on GitHub Pages at https://pangjacque.github.io/Lumos/
// `base` must match the repo name (case-sensitive) so asset URLs resolve under the subpath.
export default defineConfig({
  site: 'https://pangjacque.github.io',
  base: '/Lumos',
});
