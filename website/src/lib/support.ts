import { z } from 'astro/zod';
import translations from './support.json';
const text = z.string().trim().min(1);
const pair = z.tuple([text, text]);
const schema = z.strictObject({
  reportsTitle: text,
  firmwareLabel: text,
  webosLabel: text,
  releaseLabel: text,
  helpTitle: text,
  helpDescription: text,
  editionDescription: text,
  quickTitle: text,
  steps: z.array(text).length(3),
  tableHint: text,
  tableLabels: z.array(text).length(6),
  access: pair,
  keep: pair,
  resume: pair,
  updates: pair,
  checksTitle: text,
  checks: z.array(text).length(3),
  referenceLabel: text,
  help: z.array(pair).length(5)
});
// Validate the entire translation set before generating any page.
export const support = z.record(z.string(), schema).parse(translations);
export const topics = [
  {
    id: 'connection',
    reference: 'docs/INSTALL.md#2-prepare-your-tv-and-computer'
  },
  {
    id: 'developer-mode',
    reference: 'docs/INSTALL.md#set-up-developer-mode-no-root'
  },
  { id: 'home-button', reference: 'docs/RECOVERY.md#return-to-lg-home' },
  {
    id: 'interrupted',
    reference: 'docs/RECOVERY.md#interrupted-setup-or-removal'
  },
  { id: 'update-remove', reference: 'docs/MAINTENANCE.md' }
] as const;
