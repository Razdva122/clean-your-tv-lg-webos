import { defineCollection } from "astro:content";
import { glob } from "astro/loaders";
export const collections = {
  guides: defineCollection({
    loader: glob({
      pattern: "*.md",
      base: "../docs/i18n",
      generateId: ({ entry }) => entry.replace(/\.md$/, ""),
    }),
  }),
};
