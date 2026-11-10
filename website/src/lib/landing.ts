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
  featureTitle: text,
  features: z.array(text).length(3),
  pauseLabel: text,
  playLabel: text,
  closeTitle: text
});
export const landingCopy = Object.fromEntries(
  locales.map((lang) => [lang, schema.parse(translations[lang])])
) as Record<Locale, z.infer<typeof schema>>;
export const showcaseThemes = [
  { id: 'classic', title: 'Classic' },
  { id: 'liquid-glass', title: 'Liquid Glass' },
  { id: 'ribbon', title: 'Ribbon' }
] as const;
