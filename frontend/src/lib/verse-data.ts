export type Verse = {
  id: string;
  book: string;
  chapter: number;
  verse: number;
  text: string;
  version: string;
};

export const BIBLE_VERSES: Verse[] = [
  {
    id: "john-3-16",
    book: "John",
    chapter: 3,
    verse: 16,
    text: "For God so loved the world that he gave his one and only Son, that whoever believes in him shall not perish but have eternal life.",
    version: "NIV",
  },
  {
    id: "psalm-23-1",
    book: "Psalm",
    chapter: 23,
    verse: 1,
    text: "The Lord is my shepherd, I lack nothing.",
    version: "NIV",
  },
  {
    id: "phil-4-13",
    book: "Philippians",
    chapter: 4,
    verse: 13,
    text: "I can do all this through him who gives me strength.",
    version: "NIV",
  },
  {
    id: "rom-8-28",
    book: "Romans",
    chapter: 8,
    verse: 28,
    text: "And we know that in all things God works for the good of those who love him.",
    version: "NIV",
  },
  {
    id: "prov-3-5",
    book: "Proverbs",
    chapter: 3,
    verse: 5,
    text: "Trust in the Lord with all your heart and lean not on your own understanding.",
    version: "NIV",
  },
  {
    id: "isa-40-31",
    book: "Isaiah",
    chapter: 40,
    verse: 31,
    text: "But those who hope in the Lord will renew their strength. They will soar on wings like eagles.",
    version: "NIV",
  },
  {
    id: "jer-29-11",
    book: "Jeremiah",
    chapter: 29,
    verse: 11,
    text: "For I know the plans I have for you, declares the Lord, plans to prosper you and not to harm you.",
    version: "NIV",
  },
  {
    id: "matt-11-28",
    book: "Matthew",
    chapter: 11,
    verse: 28,
    text: "Come to me, all you who are weary and burdened, and I will give you rest.",
    version: "NIV",
  },
  {
    id: "psalm-46-10",
    book: "Psalm",
    chapter: 46,
    verse: 10,
    text: "Be still, and know that I am God.",
    version: "NIV",
  },
  {
    id: "1cor-13-4",
    book: "1 Corinthians",
    chapter: 13,
    verse: 4,
    text: "Love is patient, love is kind. It does not envy, it does not boast, it is not proud.",
    version: "NIV",
  },
];

export type SearchResult = {
  verse: Verse;
  confidence: number;
};

// Naive fuzzy matcher for demo purposes
export function matchVerse(query: string): SearchResult | null {
  const q = query.toLowerCase().trim();
  if (!q) return null;
  const words = q.split(/\s+/).filter(Boolean);

  let best: { verse: Verse; score: number } | null = null;
  for (const v of BIBLE_VERSES) {
    const hay = `${v.text} ${v.book} ${v.chapter}:${v.verse}`.toLowerCase();
    let hits = 0;
    for (const w of words) if (hay.includes(w)) hits++;
    const phraseBoost = hay.includes(q) ? 0.35 : 0;
    const score = hits / Math.max(words.length, 1) + phraseBoost;
    if (!best || score > best.score) best = { verse: v, score };
  }
  if (!best || best.score === 0) return null;
  const confidence = Math.min(0.99, 0.55 + best.score * 0.4);
  return { verse: best.verse, confidence };
}

export type RecentSearch = {
  id: string;
  query: string;
  verseId: string;
  timestamp: number;
};

const RECENT_KEY = "verseid_recent";
const SAVED_KEY = "verseid_saved";

export function getRecent(): RecentSearch[] {
  if (typeof window === "undefined") return [];
  try {
    return JSON.parse(localStorage.getItem(RECENT_KEY) || "[]");
  } catch {
    return [];
  }
}
export function addRecent(item: RecentSearch) {
  const list = [item, ...getRecent().filter((r) => r.verseId !== item.verseId)].slice(0, 10);
  localStorage.setItem(RECENT_KEY, JSON.stringify(list));
}
export function getSaved(): string[] {
  if (typeof window === "undefined") return [];
  try {
    return JSON.parse(localStorage.getItem(SAVED_KEY) || "[]");
  } catch {
    return [];
  }
}
export function toggleSaved(id: string) {
  const list = getSaved();
  const next = list.includes(id) ? list.filter((x) => x !== id) : [...list, id];
  localStorage.setItem(SAVED_KEY, JSON.stringify(next));
  return next;
}
