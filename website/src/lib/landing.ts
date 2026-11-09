import { z } from 'astro/zod';
import translations from './landing.json';
import { locales, type Locale } from './site';
const text = z.string().trim().min(1);
const schema = z.strictObject({
  headline: text,
  intro: text,
  tryLabel: text,
  installLabel: text,
  chooseLabel: text,
  demoLabel: text,
  startLabel: text,
  loadingLabel: text,
  errorLabel: text,
  remoteLabel: text,
  homeHint: text,
  navigateHint: text,
  readyLabel: text,
  fullDemoLabel: text,
  pressLeftLabel: text,
  pressRightLabel: text,
  pressOkLabel: text
});
export const landingCopy = Object.fromEntries(
  locales.map((lang) => [lang, schema.parse(translations[lang])])
) as Record<Locale, z.infer<typeof schema>>;
export const showcaseThemes = [
  { id: 'classic', title: 'Classic' },
  { id: 'liquid-glass', title: 'Liquid Glass' },
  { id: 'ribbon', title: 'Ribbon' }
] as const;
