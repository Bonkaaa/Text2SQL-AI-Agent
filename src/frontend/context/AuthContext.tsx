"use client";

import React, { createContext, useContext, useState, useEffect } from "react";
import { UserRole } from "@/types/api";

export interface UserProfile {
  id: string;
  name: string;
  email: string;
  role: UserRole;
  adminToken?: string;
  avatarUrl?: string;
}

export type PersonaType = "analyst" | "admin" | "business";

export const PRESET_PERSONAS: Record<PersonaType, UserProfile> = {
  analyst: {
    id: "analyst_alex",
    name: "Alex Chen",
    email: "alex.chen@enterprise.ai",
    role: "Analyst",
  },
  admin: {
    id: "admin_lead",
    name: "Sarah Data Lead",
    email: "sarah.lead@enterprise.ai",
    role: "Admin",
    adminToken: "admin_secret_token_2026",
  },
  business: {
    id: "business_marcus",
    name: "Marcus Brody",
    email: "marcus.brody@enterprise.ai",
    role: "Business_User",
  },
};

const STORAGE_KEY = "querypilot_auth_user";

interface AuthContextType {
  user: UserProfile;
  isAuthenticated: boolean;
  login: (persona: PersonaType, customProfile?: Partial<UserProfile>) => void;
  logout: () => void;
  switchRole: (role: UserRole) => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<UserProfile>(() => {
    if (typeof window !== "undefined") {
      try {
        const stored = localStorage.getItem(STORAGE_KEY);
        if (stored) {
          return JSON.parse(stored);
        }
      } catch {
        // Fallback
      }
    }
    return PRESET_PERSONAS.analyst;
  });

  const [isAuthenticated, setIsAuthenticated] = useState<boolean>(() => {
    if (typeof window !== "undefined") {
      try {
        return localStorage.getItem(STORAGE_KEY) !== null || true;
      } catch {
        return true;
      }
    }
    return true;
  });

  const login = (persona: PersonaType, customProfile?: Partial<UserProfile>) => {
    const base = PRESET_PERSONAS[persona] || PRESET_PERSONAS.analyst;
    const updated: UserProfile = {
      ...base,
      ...customProfile,
    };
    setUser(updated);
    setIsAuthenticated(true);
    if (typeof window !== "undefined") {
      try {
        localStorage.setItem(STORAGE_KEY, JSON.stringify(updated));
      } catch {
        // Ignore storage errors
      }
    }
  };

  const switchRole = (role: UserRole) => {
    const updated: UserProfile = {
      ...user,
      role,
      adminToken: role === "Admin" ? "admin_secret_token_2026" : undefined,
    };
    setUser(updated);
    if (typeof window !== "undefined") {
      try {
        localStorage.setItem(STORAGE_KEY, JSON.stringify(updated));
      } catch {
        // Ignore
      }
    }
  };

  const logout = () => {
    setIsAuthenticated(false);
    setUser(PRESET_PERSONAS.analyst);
    if (typeof window !== "undefined") {
      try {
        localStorage.removeItem(STORAGE_KEY);
      } catch {
        // Ignore
      }
    }
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        isAuthenticated,
        login,
        logout,
        switchRole,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
}
