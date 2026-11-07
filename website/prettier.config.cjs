module.exports = {
  ...require('../.prettierrc.json'),
  plugins: ['prettier-plugin-astro'],
  overrides: [{ files: '*.astro', options: { parser: 'astro' } }]
};
