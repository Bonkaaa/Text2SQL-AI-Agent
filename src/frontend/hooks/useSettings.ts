"use client";

import { useState, useCallback } from "react";

export interface WorkspaceSettings {
  readOnly: boolean;
  defaultRowLimit: number;
  showTrace: boolean;
  requireHitlApproval: boolean;
}

export const DEFAULT_SETTINGS: WorkspaceSettings = {
  readOnly: true,
  defaultRowLimit: 100,
  showTrace: true,
  requireHitlApproval: true,
};

export const SETTINGS_STORAGE_KEY = "querypilot_settings";

export function getStoredSettings(): WorkspaceSettings {
  if (typeof window === "undefined") return DEFAULT_SETTINGS;
  try {
    const raw = localStorage.getItem(SETTINGS_STORAGE_KEY);
    if (!raw) return DEFAULT_SETTINGS;
    return { ...DEFAULT_SETTINGS, ...JSON.parse(raw) };
  } catch {
    return DEFAULT_SETTINGS;
  }
}

export function useSettings() {
  const [settings, setSettings] = useState<WorkspaceSettings>(() => {
    return getStoredSettings();
  });

  const updateSettings = useCallback(
    (partial: Partial<WorkspaceSettings>) => {
      setSettings((prev) => {
        const next = { ...prev, ...partial };
        if (typeof window !== "undefined") {
          try {
            localStorage.setItem(SETTINGS_STORAGE_KEY, JSON.stringify(next));
          } catch {
            // Ignore storage quota errors
          }
        }
        return next;
      });
    },
    []
  );

  const resetSettings = useCallback(() => {
    setSettings(DEFAULT_SETTINGS);
    if (typeof window !== "undefined") {
      try {
        localStorage.setItem(
          SETTINGS_STORAGE_KEY,
          JSON.stringify(DEFAULT_SETTINGS)
        );
      } catch {
        // Ignore
      }
    }
  }, []);

  return {
    settings,
    updateSettings,
    resetSettings,
  };
}
