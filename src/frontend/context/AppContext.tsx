"use client";

import React, {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
} from "react";
import { checkBackendHealth } from "@/services/api";
import { UserRole } from "@/types/api";

export interface ToastItem {
  id: string;
  message: string;
  type: "info" | "success" | "warning" | "error";
  durationMs?: number;
}

export interface BackendHealthState {
  isConnected: boolean;
  status: string;
  database: string;
  version: string;
  latencyMs: number;
  lastChecked?: Date;
}

export interface SessionRecord {
  id: string;
  title: string;
  createdAt: string; // ISO string
  messageCount: number;
}

interface AppContextType {
  // 1. Phân quyền người dùng (User & Role)
  currentRole: UserRole;
  setCurrentRole: (role: UserRole) => void;

  // 2. Định danh phiên làm việc & Lịch sử phiên (Session Management)
  currentSessionId: string;
  setCurrentSessionId: (id: string) => void;
  startNewSession: () => string;
  sessionHistory: SessionRecord[];
  deleteSession: (id: string) => void;
  updateSessionTitle: (id: string, title: string) => void;

  // 3. Ngăn tra cứu Schema TPC-H bên phải
  isSchemaDrawerOpen: boolean;
  setSchemaDrawerOpen: (open: boolean) => void;
  toggleSchemaDrawer: () => void;

  // 4. Thanh Sidebar bên trái
  isSidebarOpen: boolean;
  setSidebarOpen: (open: boolean) => void;
  toggleSidebar: () => void;

  // 5. Trạng thái kết nối Warehouse (Health)
  health: BackendHealthState;
  refreshHealth: () => Promise<void>;

  // 6. Hệ thống thông báo Toast
  toasts: ToastItem[];
  showToast: (
    message: string,
    type?: "info" | "success" | "warning" | "error",
    durationMs?: number
  ) => void;
  removeToast: (id: string) => void;
}

const AppContext = createContext<AppContextType | undefined>(undefined);

function generateSessionId(): string {
  const timestamp = Date.now().toString(36);
  const randomPart = Math.random().toString(36).substring(2, 8);
  return `sess_${timestamp}_${randomPart}`;
}

export function AppProvider({ children }: { children: React.ReactNode }) {
  // State 1: Role
  const [currentRole, setCurrentRoleState] = useState<UserRole>("ANALYST");

  // State 2: Session ID & Session History
  const [currentSessionId, setCurrentSessionIdState] = useState<string>("");
  const [sessionHistory, setSessionHistory] = useState<SessionRecord[]>([]);

  // State 3: Schema Drawer
  const [isSchemaDrawerOpen, setSchemaDrawerOpen] = useState<boolean>(false);

  // State 4: Sidebar
  const [isSidebarOpen, setSidebarOpen] = useState<boolean>(true);

  // State 5: Health
  const [health, setHealth] = useState<BackendHealthState>({
    isConnected: false,
    status: "checking",
    database: "unknown",
    version: "1.0.0",
    latencyMs: 0,
  });

  // State 6: Toast notifications
  const [toasts, setToasts] = useState<ToastItem[]>([]);

  // Đọc dữ liệu từ localStorage khi component mount phía client (an toàn Hydration)
  useEffect(() => {
    try {
      const savedRole = localStorage.getItem("text2sql_user_role") as UserRole;
      if (savedRole && (savedRole === "ANALYST" || savedRole === "ADMIN")) {
        setCurrentRoleState(savedRole);
      }

      // Khôi phục danh sách phiên
      const savedHistoryStr = localStorage.getItem("text2sql_session_history");
      let historyList: SessionRecord[] = [];
      if (savedHistoryStr) {
        historyList = JSON.parse(savedHistoryStr);
        setSessionHistory(historyList);
      }

      // Khôi phục hoặc tạo phiên hiện tại
      const savedSession = localStorage.getItem("text2sql_active_session");
      if (savedSession) {
        setCurrentSessionIdState(savedSession);
      } else {
        const newSessionId = generateSessionId();
        setCurrentSessionIdState(newSessionId);
        localStorage.setItem("text2sql_active_session", newSessionId);

        const initialRecord: SessionRecord = {
          id: newSessionId,
          title: "Phiên phân tích mới",
          createdAt: new Date().toISOString(),
          messageCount: 0,
        };
        const updatedHistory = [initialRecord, ...historyList];
        setSessionHistory(updatedHistory);
        localStorage.setItem(
          "text2sql_session_history",
          JSON.stringify(updatedHistory)
        );
      }
    } catch {
      setCurrentSessionIdState(generateSessionId());
    }
  }, []);

  const setCurrentRole = useCallback((role: UserRole) => {
    setCurrentRoleState(role);
    try {
      localStorage.setItem("text2sql_user_role", role);
    } catch {
      // Ignore
    }
  }, []);

  const setCurrentSessionId = useCallback((id: string) => {
    setCurrentSessionIdState(id);
    try {
      localStorage.setItem("text2sql_active_session", id);
    } catch {
      // Ignore
    }
  }, []);

  const startNewSession = useCallback((): string => {
    const newId = generateSessionId();
    setCurrentSessionId(newId);

    const newRecord: SessionRecord = {
      id: newId,
      title: "Phiên phân tích mới",
      createdAt: new Date().toISOString(),
      messageCount: 0,
    };

    setSessionHistory((prev) => {
      const updated = [newRecord, ...prev.filter((s) => s.id !== newId)];
      try {
        localStorage.setItem(
          "text2sql_session_history",
          JSON.stringify(updated)
        );
      } catch {
        // Ignore
      }
      return updated;
    });

    return newId;
  }, [setCurrentSessionId]);

  const deleteSession = useCallback(
    (id: string) => {
      setSessionHistory((prev) => {
        const updated = prev.filter((s) => s.id !== id);
        try {
          localStorage.setItem(
            "text2sql_session_history",
            JSON.stringify(updated)
          );
        } catch {
          // Ignore
        }
        return updated;
      });

      // Nếu xóa đúng phiên hiện tại đang mở, tự động chuyển sang phiên khác hoặc tạo mới
      if (id === currentSessionId) {
        startNewSession();
      }
    },
    [currentSessionId, startNewSession]
  );

  const updateSessionTitle = useCallback((id: string, title: string) => {
    setSessionHistory((prev) => {
      const updated = prev.map((s) => (s.id === id ? { ...s, title } : s));
      try {
        localStorage.setItem(
          "text2sql_session_history",
          JSON.stringify(updated)
        );
      } catch {
        // Ignore
      }
      return updated;
    });
  }, []);

  const toggleSchemaDrawer = useCallback(() => {
    setSchemaDrawerOpen((prev) => !prev);
  }, []);

  const toggleSidebar = useCallback(() => {
    setSidebarOpen((prev) => !prev);
  }, []);

  // Kiểm tra sức khỏe kết nối Backend
  const refreshHealth = useCallback(async () => {
    const startTime = performance.now();
    try {
      const result = await checkBackendHealth();
      const latencyMs = Math.round(performance.now() - startTime);

      setHealth({
        isConnected: result.status === "healthy" || result.status === "ok",
        status: result.status,
        database: result.database || "duckdb",
        version: result.version || "1.0.0",
        latencyMs,
        lastChecked: new Date(),
      });
    } catch {
      setHealth((prev) => ({
        ...prev,
        isConnected: false,
        status: "disconnected",
        latencyMs: 0,
        lastChecked: new Date(),
      }));
    }
  }, []);

  // Tự động kiểm tra sức khỏe khi nạp trang
  useEffect(() => {
    refreshHealth();
    const timer = setInterval(refreshHealth, 60000);
    return () => clearInterval(timer);
  }, [refreshHealth]);

  // Quản lý Toast
  const removeToast = useCallback((id: string) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  }, []);

  const showToast = useCallback(
    (
      message: string,
      type: "info" | "success" | "warning" | "error" = "info",
      durationMs: number = 3500
    ) => {
      const id = Math.random().toString(36).substring(2, 9);
      const newToast: ToastItem = { id, message, type, durationMs };

      setToasts((prev) => [...prev, newToast]);

      if (durationMs > 0) {
        setTimeout(() => {
          removeToast(id);
        }, durationMs);
      }
    },
    [removeToast]
  );

  return (
    <AppContext.Provider
      value={{
        currentRole,
        setCurrentRole,
        currentSessionId,
        setCurrentSessionId,
        startNewSession,
        sessionHistory,
        deleteSession,
        updateSessionTitle,
        isSchemaDrawerOpen,
        setSchemaDrawerOpen,
        toggleSchemaDrawer,
        isSidebarOpen,
        setSidebarOpen,
        toggleSidebar,
        health,
        refreshHealth,
        toasts,
        showToast,
        removeToast,
      }}
    >
      {children}
    </AppContext.Provider>
  );
}

/**
 * Custom hook truy cập AppContext.
 */
export function useAppContext(): AppContextType {
  const context = useContext(AppContext);
  if (!context) {
    throw new Error("useAppContext phải được sử dụng bên trong một <AppProvider>");
  }
  return context;
}
