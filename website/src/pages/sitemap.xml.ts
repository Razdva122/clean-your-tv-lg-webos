import { locales, sections, route, origin } from "../lib/site";
export function GET() {
  const urls = locales.flatMap((lang) =>
    sections.map(
      (section) =>
        `<url><loc>${origin + route(lang, section)}</loc>${locales.map((other) => `<xhtml:link rel="alternate" hreflang="${other}" href="${origin + route(other, section)}"/>`).join("")}<xhtml:link rel="alternate" hreflang="x-default" href="${origin + route("en", section)}"/></url>`,
    ),
  );
  return new Response(
    `<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" xmlns:xhtml="http://www.w3.org/1999/xhtml">${urls.join("")}</urlset>`,
    { headers: { "Content-Type": "application/xml" } },
  );
}
