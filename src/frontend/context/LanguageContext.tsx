"use client";

import React, { createContext, useContext, useState, useEffect, useCallback } from "react";
import { Locale, TranslationKey, translations, defaultLocale } from "@/locales";

interface LanguageContextType {
  locale: Locale;
  setLocale: (locale: Locale) => void;
  toggleLocale: () => void;
  t: (key: TranslationKey | string, fallback?: string) => string;
}

const STORAGE_KEY = "querypilot_locale";

const LanguageContext = createContext<LanguageContextType | undefined>(undefined);

export function LanguageProvider({
  children,
  initialLocale,
}: {
  children: React.ReactNode;
  initialLocale?: Locale;
}) {
  const [locale, setLocaleState] = useState<Locale>(() => {
    if (initialLocale) return initialLocale;
    if (typeof window !== "undefined") {
      try {
        const stored = localStorage.getItem(STORAGE_KEY);
        if (stored === "vi" || stored === "en") {
          return stored;
        }
      } catch {
        // Fallback
      }
    }
    return defaultLocale;
  });

  const setLocale = useCallback((newLocale: Locale) => {
    setLocaleState(newLocale);
    if (typeof window !== "undefined") {
      try {
        localStorage.setItem(STORAGE_KEY, newLocale);
      } catch {
        // Ignore storage errors
      }
    }
  }, []);

  const toggleLocale = useCallback(() => {
    setLocale(locale === "vi" ? "en" : "vi");
  }, [locale, setLocale]);

  const t = useCallback(
    (key: TranslationKey | string, fallback?: string): string => {
      const currentDict = translations[locale];
      if (currentDict && key in currentDict) {
        return currentDict[key as TranslationKey];
      }
      // Fallback to English dictionary
      const enDict = translations.en;
      if (enDict && key in enDict) {
        return enDict[key as TranslationKey];
      }
      return fallback || key;
    },
    [locale]
  );

  return (
    <LanguageContext.Provider value={{ locale, setLocale, toggleLocale, t }}>
      {children}
    </LanguageContext.Provider>
  );
}

const defaultContextValue: LanguageContextType = {
  locale: defaultLocale,
  setLocale: () => {},
  toggleLocale: () => {},
  t: (key: TranslationKey | string, fallback?: string) => {
    const enDict = translations.en;
    if (enDict && key in enDict) {
      return enDict[key as TranslationKey];
    }
    return fallback || key;
  },
};

export function useLanguage() {
  const context = useContext(LanguageContext);
  return context || defaultContextValue;
}
