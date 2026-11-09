import { locales, sections, route, origin } from '../lib/site';
import { articleRoute, getArticles } from '../lib/articles';
export async function GET() {
  const urls = locales.flatMap((lang) =>
    sections.map(
      (section) =>
        `<url><loc>${origin + route(lang, section)}</loc>${locales.map((other) => `<xhtml:link rel="alternate" hreflang="${other}" href="${origin + route(other, section)}"/>`).join('')}<xhtml:link rel="alternate" hreflang="x-default" href="${origin + route('en', section)}"/></url>`
    )
  );
  const articleUrls = (await getArticles()).map(
    ({ data }) =>
      `<url><loc>${origin + articleRoute(data.lang, data.topic)}</loc><lastmod>${data.updated}</lastmod>${locales.map((other) => `<xhtml:link rel="alternate" hreflang="${other}" href="${origin + articleRoute(other, data.topic)}"/>`).join('')}<xhtml:link rel="alternate" hreflang="x-default" href="${origin + articleRoute('en', data.topic)}"/></url>`
  );
  const indexes = locales.map(
    (lang) =>
      `<url><loc>${origin + articleRoute(lang)}</loc>${locales.map((other) => `<xhtml:link rel="alternate" hreflang="${other}" href="${origin + articleRoute(other)}"/>`).join('')}<xhtml:link rel="alternate" hreflang="x-default" href="${origin + articleRoute('en')}"/></url>`
  );
  return new Response(
    `<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" xmlns:xhtml="http://www.w3.org/1999/xhtml">${[...urls, ...indexes, ...articleUrls].join('')}</urlset>`,
    { headers: { 'Content-Type': 'application/xml' } }
  );
}
