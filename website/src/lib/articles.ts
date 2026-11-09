import { getCollection } from 'astro:content';
import { z } from 'astro/zod';
import {
  locales,
  route,
  articleTopics,
  type ArticleTopic,
  type Locale
} from './site';
export { articleTopics, type ArticleTopic } from './site';
export interface ArticleMetadata {
  lang: Locale;
  topic: ArticleTopic;
  title: string;
  description: string;
  updated: string;
}
const text = z.string().trim().min(1);
const copySchema = z.strictObject({
  title: text,
  indexTitle: text,
  description: text,
  updatedLabel: text,
  relatedLabel: text,
  contentsLabel: text,
  homeLabel: text
});
const translations = import.meta.glob('./article-copy/*.json', {
  eager: true,
  import: 'default'
});
export const articleCopy = Object.fromEntries(
  locales.map((lang) => [
    lang,
    copySchema.parse(translations[`./article-copy/${lang}.json`])
  ])
) as Record<Locale, z.infer<typeof copySchema>>;
export const articleRoute = (lang: Locale, topic?: ArticleTopic) =>
  `${route(lang)}articles/${topic ? topic + '/' : ''}`;

export async function getArticles() {
  const entries = await getCollection('articles');
  for (const lang of locales) {
    for (const topic of articleTopics) {
      if (
        entries.filter(
          (entry) => entry.data.lang === lang && entry.data.topic === topic
        ).length !== 1
      ) {
        throw new Error(`Expected one article for ${lang}/${topic}`);
      }
    }
  }
  return entries.sort(
    (a, b) =>
      articleTopics.indexOf(a.data.topic) - articleTopics.indexOf(b.data.topic)
  );
}
