import { en, TranslationKey } from "./en";
import { vi } from "./vi";

export type Locale = "en" | "vi";
export type { TranslationKey };

export const translations: Record<Locale, Record<TranslationKey, string>> = {
  en,
  vi,
};

export const defaultLocale: Locale = "en";
