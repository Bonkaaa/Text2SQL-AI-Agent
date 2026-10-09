export interface SavedQueryItem {
  id: string;
  title: string;
  question: string;
  sql?: string;
  tag?: string;
  createdAt: string;
  owner?: string;
}

export interface HistoryItem {
  id: string;
  question: string;
  sql?: string;
  status: "SUCCESS" | "BLOCKED" | "ERROR" | "PENDING";
  rowCount?: number;
  executionTimeMs?: number;
  timestamp: string;
  userRole?: string;
}

const SAVED_QUERIES_KEY = "querypilot_saved_queries";
const QUERY_HISTORY_KEY = "querypilot_query_history";

export const PRESET_SAVED_QUERIES: SavedQueryItem[] = [
  {
    id: "sq_1",
    title: "Top 10 Sản Phẩm Doanh Thu Cao Nhất 2003",
    question: "Which 10 products generated the most revenue in 2003?",
    sql: `SELECT i.i_item_id, i.i_item_desc, SUM(ss.ss_net_paid) AS total_revenue
FROM store_sales ss
JOIN item i ON ss.ss_item_sk = i.i_item_sk
JOIN date_dim d ON ss.ss_sold_date_sk = d.d_date_sk
WHERE d.d_year = 2003
GROUP BY 1, 2 ORDER BY 3 DESC LIMIT 10;`,
    tag: "Doanh thu",
    createdAt: "2026-10-08 09:30",
    owner: "Alex Chen",
  },
  {
    id: "sq_2",
    title: "So Sánh Doanh Số Kênh Cửa Hàng vs Kênh Web 2002",
    question: "Compare monthly sales between store channel and web channel in 2002.",
    sql: `SELECT d.d_moy AS month, SUM(ss.ss_net_paid) AS store_revenue, SUM(ws.ws_net_paid) AS web_revenue
FROM date_dim d
LEFT JOIN store_sales ss ON ss.ss_sold_date_sk = d.d_date_sk
LEFT JOIN web_sales ws ON ws.ws_sold_date_sk = d.d_date_sk
WHERE d.d_year = 2002 GROUP BY 1 ORDER BY 1;`,
    tag: "Đa kênh",
    createdAt: "2026-10-08 14:15",
    owner: "Alex Chen",
  },
  {
    id: "sq_3",
    title: "Phân Tích Tỷ Lệ Đổi Trả Theo Nhóm Học Vấn",
    question: "Which customer income demographics show the highest item return rate?",
    sql: `SELECT cd.cd_education_status, COUNT(sr.sr_item_sk) AS return_count, SUM(sr.sr_return_amt) AS total_refunded
FROM store_returns sr
JOIN customer c ON sr.sr_customer_sk = c.c_customer_sk
JOIN customer_demographics cd ON c.c_current_cdemo_sk = cd.cd_demo_sk
GROUP BY 1 ORDER BY 3 DESC;`,
    tag: "Đổi trả",
    createdAt: "2026-10-09 11:20",
    owner: "Sarah Data Lead",
  },
];

export const PRESET_HISTORY_ITEMS: HistoryItem[] = [
  {
    id: "hist_1",
    question: "Which 10 products generated the most revenue in 2003?",
    sql: "SELECT i_item_id, SUM(ss_net_paid) AS total_revenue FROM store_sales GROUP BY 1 LIMIT 10;",
    status: "SUCCESS",
    rowCount: 10,
    executionTimeMs: 186,
    timestamp: "2026-10-09 14:22",
    userRole: "Analyst",
  },
  {
    id: "hist_2",
    question: "Compare monthly sales between store channel and web channel in 2002.",
    sql: "SELECT d_moy, SUM(ss_net_paid), SUM(ws_net_paid) FROM date_dim ...",
    status: "SUCCESS",
    rowCount: 12,
    executionTimeMs: 342,
    timestamp: "2026-10-09 13:45",
    userRole: "Analyst",
  },
  {
    id: "hist_3",
    question: "DROP TABLE customer;",
    sql: "DROP TABLE customer;",
    status: "BLOCKED",
    rowCount: 0,
    executionTimeMs: 12,
    timestamp: "2026-10-09 11:05",
    userRole: "Analyst",
  },
  {
    id: "hist_4",
    question: "Tồn kho các mặt hàng thuộc nhóm Apparel tại kho số 1",
    sql: "SELECT i_item_id, inv_quantity_on_hand FROM inventory WHERE inv_warehouse_sk = 1 LIMIT 20;",
    status: "SUCCESS",
    rowCount: 20,
    executionTimeMs: 154,
    timestamp: "2026-10-09 09:12",
    userRole: "Admin",
  },
];

// --- Saved Queries Repository ---

export function getSavedQueries(): SavedQueryItem[] {
  if (typeof window === "undefined") return PRESET_SAVED_QUERIES;
  try {
    const raw = localStorage.getItem(SAVED_QUERIES_KEY);
    if (!raw) {
      localStorage.setItem(SAVED_QUERIES_KEY, JSON.stringify(PRESET_SAVED_QUERIES));
      return PRESET_SAVED_QUERIES;
    }
    return JSON.parse(raw);
  } catch {
    return PRESET_SAVED_QUERIES;
  }
}

export function saveQueryItem(
  item: Omit<SavedQueryItem, "id" | "createdAt">
): SavedQueryItem {
  const current = getSavedQueries();
  const existing = current.find(
    (q) => q.question.trim().toLowerCase() === item.question.trim().toLowerCase()
  );
  if (existing) {
    return existing;
  }

  const newItem: SavedQueryItem = {
    ...item,
    id: `sq_${Date.now()}`,
    createdAt: new Date().toISOString().replace("T", " ").substring(0, 16),
  };

  const updated = [newItem, ...current];
  if (typeof window !== "undefined") {
    try {
      localStorage.setItem(SAVED_QUERIES_KEY, JSON.stringify(updated));
    } catch {
      // Ignore
    }
  }
  return newItem;
}

export function deleteSavedQuery(id: string): void {
  const current = getSavedQueries();
  const filtered = current.filter((q) => q.id !== id);
  if (typeof window !== "undefined") {
    try {
      localStorage.setItem(SAVED_QUERIES_KEY, JSON.stringify(filtered));
    } catch {
      // Ignore
    }
  }
}

export function isQuerySaved(question: string): boolean {
  const current = getSavedQueries();
  return current.some(
    (q) => q.question.trim().toLowerCase() === question.trim().toLowerCase()
  );
}

// --- Query History Repository ---

export function getHistoryItems(): HistoryItem[] {
  if (typeof window === "undefined") return PRESET_HISTORY_ITEMS;
  try {
    const raw = localStorage.getItem(QUERY_HISTORY_KEY);
    if (!raw) {
      localStorage.setItem(QUERY_HISTORY_KEY, JSON.stringify(PRESET_HISTORY_ITEMS));
      return PRESET_HISTORY_ITEMS;
    }
    return JSON.parse(raw);
  } catch {
    return PRESET_HISTORY_ITEMS;
  }
}

export function addHistoryItem(
  item: Omit<HistoryItem, "id">
): HistoryItem {
  const current = getHistoryItems();
  const newItem: HistoryItem = {
    ...item,
    id: `hist_${Date.now()}`,
  };

  const updated = [newItem, ...current].slice(0, 50); // Keep latest 50
  if (typeof window !== "undefined") {
    try {
      localStorage.setItem(QUERY_HISTORY_KEY, JSON.stringify(updated));
    } catch {
      // Ignore
    }
  }
  return newItem;
}

export function clearHistory(): void {
  if (typeof window !== "undefined") {
    try {
      localStorage.setItem(QUERY_HISTORY_KEY, JSON.stringify([]));
    } catch {
      // Ignore
    }
  }
}
