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
    title: "Top 10 Khách Hàng Chi Tiêu Cao Nhất Năm 1995",
    question: "Which 10 customers spent the most money on orders in 1995?",
    sql: `SELECT c.c_custkey, c.c_name, SUM(l.l_extendedprice * (1 - l.l_discount)) AS total_spent
FROM customer c
JOIN orders o ON c.c_custkey = o.o_custkey
JOIN lineitem l ON o.o_orderkey = l.l_orderkey
WHERE EXTRACT(year FROM o.o_orderdate) = 1995
GROUP BY 1, 2 ORDER BY 3 DESC LIMIT 10;`,
    tag: "Khách hàng",
    createdAt: "2026-10-08 09:30",
    owner: "Alex Chen",
  },
  {
    id: "sq_2",
    title: "Doanh Thu Theo Từng Phân Khúc Thị Trường 1995",
    question: "Compare revenue across market segments in 1995.",
    sql: `SELECT c.c_mktsegment, SUM(l.l_extendedprice * (1 - l.l_discount)) AS segment_revenue
FROM customer c
JOIN orders o ON c.c_custkey = o.o_custkey
JOIN lineitem l ON o.o_orderkey = l.l_orderkey
WHERE EXTRACT(year FROM o.o_orderdate) = 1995
GROUP BY 1 ORDER BY 2 DESC;`,
    tag: "Phân khúc",
    createdAt: "2026-10-08 14:15",
    owner: "Alex Chen",
  },
  {
    id: "sq_3",
    title: "Phân Tích Tỷ Lệ Đổi Trả Theo Phương Thức Vận Chuyển",
    question: "Which ship modes have the highest return rate?",
    sql: `SELECT l.l_shipmode, COUNT(*) AS total_items, SUM(CASE WHEN l.l_returnflag = 'R' THEN 1 ELSE 0 END) AS returned_items
FROM lineitem l
GROUP BY 1 ORDER BY 2 DESC;`,
    tag: "Đổi Trả",
    createdAt: "2026-10-09 11:20",
    owner: "Sarah Data Lead",
  },
];

export const PRESET_HISTORY_ITEMS: HistoryItem[] = [
  {
    id: "hist_1",
    question: "Which 10 customers spent the most money on orders in 1995?",
    sql: "SELECT c.c_custkey, c.c_name, SUM(l.l_extendedprice * (1 - l.l_discount)) AS total_spent FROM customer c JOIN orders o ON c.c_custkey = o.o_custkey JOIN lineitem l ON o.o_orderkey = l.l_orderkey WHERE EXTRACT(year FROM o.o_orderdate) = 1995 GROUP BY 1, 2 ORDER BY 3 DESC LIMIT 10;",
    status: "SUCCESS",
    rowCount: 10,
    executionTimeMs: 186,
    timestamp: "2026-10-09 14:22",
    userRole: "Analyst",
  },
  {
    id: "hist_2",
    question: "Compare revenue across market segments in 1995.",
    sql: "SELECT c.c_mktsegment, SUM(l.l_extendedprice * (1 - l.l_discount)) AS segment_revenue FROM customer c JOIN orders o ON c.c_custkey = o.o_custkey JOIN lineitem l ON o.o_orderkey = l.l_orderkey WHERE EXTRACT(year FROM o.o_orderdate) = 1995 GROUP BY 1 ORDER BY 2 DESC;",
    status: "SUCCESS",
    rowCount: 5,
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
    question: "Tồn kho các mặt hàng linh kiện có số lượng dưới 100",
    sql: "SELECT p_partkey, ps_suppkey, ps_availqty FROM partsupp WHERE ps_availqty < 100 LIMIT 20;",
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
