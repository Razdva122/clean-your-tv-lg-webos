import { defineCollection } from 'astro:content';
import { z } from 'astro/zod';
import { glob } from 'astro/loaders';
import { locales, articleTopics } from './lib/site';
export const collections = {
  articles: defineCollection({
    loader: glob({ pattern: '**/*.md', base: './src/content/articles' }),
    schema: z.object({
      lang: z.enum(locales),
      topic: z.enum(articleTopics),
      title: z.string().trim().min(1),
      description: z.string().trim().min(30),
      updated: z.iso.date()
    })
  }),
  guides: defineCollection({
    loader: glob({
      pattern: '*.md',
      base: '../docs/i18n',
      generateId: ({ entry }) => entry.replace(/\.md$/, '')
    })
  })
};
