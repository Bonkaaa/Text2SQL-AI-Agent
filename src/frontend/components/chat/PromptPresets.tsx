"use client";

import React from "react";
import { TrendingUp, Users, Truck, Percent, LucideIcon } from "lucide-react";

export interface PromptPresetItem {
  id: string;
  category: string;
  label: string;
  query: string;
  icon: LucideIcon;
  colorClass?: string;
}

export const TPCH_PROMPT_PRESETS: PromptPresetItem[] = [
  {
    id: "revenue-region",
    category: "Doanh thu",
    label: "Doanh số 5 khu vực",
    query: "Phân tích doanh thu thuần theo 5 khu vực địa lý",
    icon: TrendingUp,
    colorClass: "text-emerald-400 group-hover:text-emerald-300",
  },
  {
    id: "top-customers",
    category: "Khách hàng",
    label: "Top 5 khách hàng",
    query: "Top 5 khách hàng có tổng chi tiêu lớn nhất năm 1995",
    icon: Users,
    colorClass: "text-brand-400 group-hover:text-brand-300",
  },
  {
    id: "late-delivery",
    category: "Vận chuyển",
    label: "Đơn giao trễ",
    query: "Tỷ lệ đơn hàng giao trễ theo phương thức vận chuyển (AIR, TRUCK, SHIP)",
    icon: Truck,
    colorClass: "text-amber-400 group-hover:text-amber-300",
  },
  {
    id: "discount-inventory",
    category: "Chiết khấu",
    label: "Chiết khấu trung bình",
    query: "Mức chiết khấu trung bình của các dòng sản phẩm TPC-H",
    icon: Percent,
    colorClass: "text-purple-400 group-hover:text-purple-300",
  },
];

export interface PromptPresetsProps {
  onSelectPrompt: (promptText: string) => void;
  disabled?: boolean;
  className?: string;
  presets?: PromptPresetItem[];
}

export function PromptPresets({
  onSelectPrompt,
  disabled = false,
  className = "",
  presets = TPCH_PROMPT_PRESETS,
}: PromptPresetsProps) {
  const handleKeyDown = (e: React.KeyboardEvent<HTMLButtonElement>, query: string) => {
    if (e.key === "Enter" || e.key === " ") {
      e.preventDefault();
      if (!disabled) {
        onSelectPrompt(query);
      }
    }
  };

  return (
    <div
      className={`flex items-center justify-center flex-wrap gap-2.5 max-w-2xl px-4 ${className}`}
      role="group"
      aria-label="Các câu hỏi mẫu TPC-H gợi ý"
    >
      {presets.map((item) => {
        const IconComponent = item.icon;
        return (
          <button
            key={item.id}
            type="button"
            disabled={disabled}
            onClick={() => onSelectPrompt(item.query)}
            onKeyDown={(e) => handleKeyDown(e, item.query)}
            title={item.query}
            className="group flex items-center gap-2 px-3.5 py-2 rounded-full text-xs font-medium text-slate-300 bg-[#141824]/90 hover:bg-[#1c2236] hover:text-white border border-white/10 hover:border-brand-500/40 shadow-sm transition-all duration-200 active:scale-95 disabled:opacity-40 disabled:cursor-not-allowed disabled:pointer-events-none focus:outline-none focus:ring-2 focus:ring-brand-500/30"
          >
            <IconComponent className={`w-3.5 h-3.5 transition-colors ${item.colorClass || "text-brand-400"}`} />
            <span>{item.label}</span>
          </button>
        );
      })}
    </div>
  );
}

export default PromptPresets;
