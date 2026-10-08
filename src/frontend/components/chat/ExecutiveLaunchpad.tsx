"use client";

import React from "react";
import {
  TrendingUp,
  ShoppingBag,
  Undo2,
  Warehouse,
  Tag,
  ArrowRight,
  Sparkles,
} from "lucide-react";

export interface StarterQuestion {
  id: string;
  category: string;
  title: string;
  prompt: string;
  icon: React.ReactNode;
  badge: string;
}

export const STARTER_QUESTIONS: StarterQuestion[] = [
  {
    id: "omnichannel-sales",
    category: "Kênh Bán Hàng",
    title: "Doanh thu thuần Đa kênh",
    prompt:
      "So sánh tổng doanh thu thuần (Net Paid) giữa 3 kênh store_sales, web_sales và catalog_sales trong năm 2003 kèm tỷ trọng phần trăm.",
    icon: <ShoppingBag className="w-4 h-4 text-blue-400" />,
    badge: "store_sales + web_sales + catalog_sales",
  },
  {
    id: "return-rate",
    category: "Chất Lượng & Hoàn Hàng",
    title: "Tỷ lệ Hoàn hàng",
    prompt:
      "Liệt kê Top 10 mặt hàng có tỷ lệ hoàn hàng (Return Rate) cao nhất giữa store_returns và web_returns kèm lý do trả hàng chính trong quý 3.",
    icon: <Undo2 className="w-4 h-4 text-amber-400" />,
    badge: "store_returns + web_returns",
  },
  {
    id: "inventory-alert",
    category: "Chuỗi Cung Ứng",
    title: "Tồn kho & Kho hàng",
    prompt:
      "Phân tích lượng tồn kho trung bình tại các warehouse miền Tây và cảnh báo những mặt hàng có số lượng tồn kho dưới mức an toàn 500 đơn vị.",
    icon: <Warehouse className="w-4 h-4 text-emerald-400" />,
    badge: "inventory + warehouse",
  },
  {
    id: "promotion-roi",
    category: "Tiếp Thị & Khuyến Mãi",
    title: "Hiệu quả Khuyến mãi",
    prompt:
      "Đánh giá tác động của các chiến dịch promotion đến doanh thu thuần và biên lợi nhuận của kênh bán hàng trực tiếp (store_sales) năm 2003.",
    icon: <Tag className="w-4 h-4 text-purple-400" />,
    badge: "promotion + store_sales",
  },
];

export interface ExecutiveLaunchpadProps {
  currentRole?: string;
  onSelectPrompt: (prompt: string) => void;
  className?: string;
}

export function ExecutiveLaunchpad({
  currentRole = "Analyst",
  onSelectPrompt,
  className = "",
}: ExecutiveLaunchpadProps) {
  const getGreeting = () => {
    const hour = new Date().getHours();
    const persona = currentRole === "Analyst" ? "An (Supply Chain Analyst)" : "Bình (Data Lead)";
    if (hour < 12) return `Chào buổi sáng, ${persona}`;
    if (hour < 18) return `Chào buổi chiều, ${persona}`;
    return `Chào buổi tối, ${persona}`;
  };

  return (
    <div
      className={`w-full max-w-2xl mx-auto flex flex-col items-center text-center px-4 py-3 sm:py-5 animate-in fade-in duration-300 ${className}`}
    >
      {/* Top Badge: System Status & Benchmark */}
      <div className="inline-flex items-center gap-2 px-2.5 py-0.5 rounded-full bg-slate-100 dark:bg-surface-secondary border border-slate-200 dark:border-surface-border text-[11px] text-slate-700 dark:text-slate-300 mb-3 shadow-sm">
        <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
        <span className="font-medium">TPC-DS Benchmark • 24 Bảng Omnichannel</span>
        <span className="text-slate-400 dark:text-slate-500">|</span>
        <span className="text-blue-600 dark:text-brand-400 font-mono text-[10px] font-semibold">DuckDB In-Memory</span>
      </div>

      {/* Greeting & Headline */}
      <div className="space-y-1 mb-4 max-w-xl">
        <div className="text-[11px] font-bold uppercase tracking-wider text-slate-600 dark:text-slate-400 font-mono">
          {getGreeting()}
        </div>
        <h1 className="text-lg sm:text-2xl font-extrabold tracking-tight text-slate-900 dark:text-white font-sans-ui">
          Khám phá số liệu kho dữ liệu{" "}
          <span className="bg-clip-text text-transparent bg-gradient-to-r from-blue-600 via-indigo-600 to-cyan-600 dark:from-blue-400 dark:via-indigo-300 dark:to-cyan-400 font-black">
            TPC-DS Enterprise
          </span>
        </h1>
        <p className="text-xs text-slate-600 dark:text-slate-400 leading-relaxed max-w-lg mx-auto font-medium">
          Đặt câu hỏi kinh doanh bằng tiếng Việt tự nhiên. Hệ thống DeepAgents tự động kiểm tra an toàn AST (SELECT-only) và tổng hợp báo cáo.
        </p>
      </div>

      {/* 4 Curated Starter Question Cards - Compact & Clean */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5 w-full text-left">
        {STARTER_QUESTIONS.map((item) => (
          <button
            key={item.id}
            type="button"
            onClick={() => onSelectPrompt(item.prompt)}
            className="group relative p-2.5 sm:p-3 rounded-xl bg-white dark:bg-surface border border-slate-200 dark:border-surface-border hover:border-blue-500/50 hover:bg-slate-50 dark:hover:bg-surface-secondary/70 transition-all duration-150 flex items-center justify-between shadow-xs hover:shadow-md text-left gap-2.5"
          >
            <div className="flex items-start gap-2.5 min-w-0">
              <div className="p-1.5 rounded-lg bg-slate-100 dark:bg-surface-secondary border border-slate-200 dark:border-surface-border group-hover:border-blue-500/30 transition-colors flex-shrink-0 mt-0.5">
                {item.icon}
              </div>
              <div className="min-w-0">
                <div className="flex items-center gap-1.5 mb-0.5">
                  <span className="text-[10px] font-bold text-blue-700 dark:text-blue-400 uppercase tracking-wide">
                    {item.category}
                  </span>
                </div>
                <h3 className="text-xs font-bold text-slate-900 dark:text-slate-200 group-hover:text-blue-600 dark:group-hover:text-white transition-colors truncate font-sans-ui">
                  {item.title}
                </h3>
                <p className="text-[11px] text-slate-600 dark:text-slate-400 line-clamp-1 leading-snug">
                  {item.prompt}
                </p>
              </div>
            </div>

            <ArrowRight className="w-3.5 h-3.5 text-slate-400 dark:text-slate-500 group-hover:text-blue-600 dark:group-hover:text-brand-400 group-hover:translate-x-0.5 transition-all flex-shrink-0" />
          </button>
        ))}
      </div>
    </div>
  );
}
