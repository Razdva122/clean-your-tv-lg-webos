import translations from './locales.json';
import { support } from './support';
export const locales = Object.keys(
  translations
) as (keyof typeof translations)[];
export type Locale = (typeof locales)[number];
export const copy = translations;
export const sections = [
  '',
  'install',
  'editions',
  'compatibility',
  'themes',
  'help'
] as const;
export type Section = (typeof sections)[number];
export const articleTopics = [
  'change-lg-webos-home-screen',
  'lg-tv-home-screen-ads',
  'root-vs-no-root',
  'lg-developer-mode'
] as const;
export type ArticleTopic = (typeof articleTopics)[number];
export const base = '/clean-your-tv-lg-webos/';
export const origin = 'https://razdva122.github.io';
export const repo = 'https://github.com/Razdva122/clean-your-tv-lg-webos';
export const route = (lang: Locale, section: Section = '') =>
  `${base}${lang}/${section ? section + '/' : ''}`;
export function description(lang: Locale, section: Section) {
  const t = copy[lang];
  return {
    '': t.summary,
    install: t.installDescription,
    editions: support[lang].editionDescription,
    compatibility: t.compatibility,
    themes: t.themes,
    help: support[lang].helpDescription
  }[section];
}
