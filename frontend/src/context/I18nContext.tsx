import { createContext, useContext, useMemo, type ReactNode } from "react";
import { useSettings } from "@/hooks/queries/usePreferences";
import { useLanguages, useUITranslations } from "@/hooks/queries/useBible";

interface I18nContextValue {
  /**
   * Translates a UI chrome string by key, e.g. t("nav.home", "Home").
   * The second argument is both the fallback (shown before the language's
   * cache has loaded, or for any key not yet covered by
   * backend/bible/ui_strings.py) and the English source of truth — so a
   * screen that hasn't been wired into the translation system yet just
   * always renders its English string, rather than breaking.
   */
  t: (key: string, fallback: string) => string;
  languageCode: string | undefined;
}

const I18nContext = createContext<I18nContextValue>({
  t: (_key, fallback) => fallback,
  languageCode: undefined,
});

export function I18nProvider({ children }: { children: ReactNode }) {
  const { data: settings } = useSettings();
  const { data: languages = [] } = useLanguages();

  const languageCode = useMemo(() => {
    if (!settings?.language || settings.language === "English") return undefined;
    return languages.find((l) => l.name === settings.language)?.code;
  }, [settings?.language, languages]);

  const { data: translations = {} } = useUITranslations(languageCode);

  const value = useMemo<I18nContextValue>(
    () => ({
      t: (key, fallback) => translations[key] ?? fallback,
      languageCode,
    }),
    [translations, languageCode],
  );

  return <I18nContext.Provider value={value}>{children}</I18nContext.Provider>;
}

export function useT() {
  return useContext(I18nContext).t;
}
