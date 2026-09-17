"use client";

import React, { useEffect, useRef, useState } from "react";
import {
  Check,
  ChevronDown,
  ShieldCheck,
  TrendingUp,
} from "lucide-react";
import { useAppContext } from "@/context/AppContext";
import { UserRole } from "@/types/api";

interface RoleOption {
  id: UserRole;
  label: string;
  personaName: string;
  title: string;
  description: string;
  themeColor: "brand" | "amber";
}

const ROLES: RoleOption[] = [
  {
    id: "ANALYST",
    label: "Analyst",
    personaName: "Nguyễn Văn An",
    title: "Supply Chain & Sales Analyst",
    description: "Tra cứu báo cáo bán hàng & chuỗi cung ứng TPC-H. Bị chặn truy cập các trường PII (số điện thoại, số dư tài khoản).",
    themeColor: "brand",
  },
  {
    id: "ADMIN",
    label: "Admin",
    personaName: "Trần Thị Bình",
    title: "Data Lead & Governance Admin",
    description: "Toàn quyền truy cập mọi bảng/cột. Mở khóa trang Nhật ký Kiểm toán (Audit Trail) và giám sát chi phí quét.",
    themeColor: "amber",
  },
];

export function RoleSwitcher() {
  const { currentRole, setCurrentRole, showToast } = useAppContext();
  const [isOpen, setIsOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  // Chuẩn hóa role hiện tại (hỗ trợ cả chữ hoa hoặc viết hoa chữ cái đầu)
  const isAnalyst = currentRole === "ANALYST" || currentRole === "Analyst";
  const activeRoleConfig = ROLES.find(
    (r) => r.id === (isAnalyst ? "ANALYST" : "ADMIN")
  ) || ROLES[0];

  // Đóng menu khi click ra ngoài (Click Outside)
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (
        dropdownRef.current &&
        !dropdownRef.current.contains(event.target as Node)
      ) {
        setIsOpen(false);
      }
    }

    function handleKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") {
        setIsOpen(false);
      }
    }

    if (isOpen) {
      document.addEventListener("mousedown", handleClickOutside);
      document.addEventListener("keydown", handleKeyDown);
    }
    return () => {
      document.removeEventListener("mousedown", handleClickOutside);
      document.removeEventListener("keydown", handleKeyDown);
    };
  }, [isOpen]);

  const handleSelectRole = (role: UserRole) => {
    if (role === currentRole) {
      setIsOpen(false);
      return;
    }

    setCurrentRole(role);
    setIsOpen(false);

    const isNewRoleAnalyst = role === "ANALYST" || role === "Analyst";
    if (isNewRoleAnalyst) {
      showToast(
        "Đã chuyển sang vai trò: Analyst (Nguyễn Văn An) — Áp dụng chính sách bảo mật che PII",
        "info",
        4000
      );
    } else {
      showToast(
        "Đã chuyển sang vai trò: Admin (Trần Thị Bình) — Mở khóa Nhật ký Kiểm toán (/audit)",
        "success",
        4000
      );
    }
  };

  return (
    <div className="relative inline-block text-left" ref={dropdownRef}>
      {/* ================================================================= */}
      {/* TRIGGER BUTTON */}
      {/* ================================================================= */}
      <button
        onClick={() => setIsOpen((prev) => !prev)}
        className={`flex items-center gap-2 px-3 py-1.5 rounded-xl text-xs font-semibold border transition-all duration-200 ${
          isAnalyst
            ? "bg-brand-500/10 text-brand-300 border-brand-500/30 hover:bg-brand-500/20 hover:border-brand-500/50"
            : "bg-amber-500/10 text-amber-300 border-amber-500/30 hover:bg-amber-500/20 hover:border-amber-500/50"
        }`}
        title={`Đang đăng nhập vai trò: ${activeRoleConfig.label} (${activeRoleConfig.personaName})`}
        aria-haspopup="true"
        aria-expanded={isOpen}
      >
        <span
          className={`h-2 w-2 rounded-full ${
            isAnalyst ? "bg-brand-400" : "bg-amber-400"
          }`}
        ></span>

        <span className="flex items-center gap-1.5">
          {isAnalyst ? (
            <TrendingUp className="w-3.5 h-3.5 text-brand-400" />
          ) : (
            <ShieldCheck className="w-3.5 h-3.5 text-amber-400" />
          )}
          <span>{activeRoleConfig.label}</span>
          <span className="text-slate-400 font-normal hidden lg:inline">
            ({activeRoleConfig.personaName.split(" ").slice(-1)[0]})
          </span>
        </span>

        <ChevronDown
          className={`w-3.5 h-3.5 opacity-70 transition-transform duration-200 ${
            isOpen ? "rotate-180" : ""
          }`}
        />
      </button>

      {/* ================================================================= */}
      {/* DROPDOWN POPOVER MENU */}
      {/* ================================================================= */}
      {isOpen && (
        <div className="absolute right-0 mt-2 w-80 sm:w-96 rounded-2xl glass-card shadow-card p-2 z-50 border border-surface-border animate-in fade-in zoom-in-95 duration-150">
          <div className="px-3 py-2 border-b border-surface-border mb-1.5">
            <div className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">
              Mô phỏng Phân quyền (RBAC)
            </div>
            <div className="text-xs text-slate-300 font-medium mt-0.5">
              Chọn vai trò để trải nghiệm cơ chế kiểm duyệt dữ liệu:
            </div>
          </div>

          <div className="space-y-1">
            {ROLES.map((role) => {
              const isSelected =
                (role.id === "ANALYST" && isAnalyst) ||
                (role.id === "ADMIN" && !isAnalyst);

              return (
                <button
                  key={role.id}
                  onClick={() => handleSelectRole(role.id)}
                  className={`w-full flex items-start gap-3 p-3 rounded-xl text-left transition-all duration-150 ${
                    isSelected
                      ? role.themeColor === "brand"
                        ? "bg-brand-500/15 border border-brand-500/40 text-white"
                        : "bg-amber-500/15 border border-amber-500/40 text-white"
                      : "hover:bg-surface-subtle/80 text-slate-300 border border-transparent"
                  }`}
                >
                  {/* Icon Avatar */}
                  <div
                    className={`mt-0.5 p-2 rounded-lg flex-shrink-0 ${
                      role.themeColor === "brand"
                        ? "bg-brand-500/20 text-brand-300"
                        : "bg-amber-500/20 text-amber-300"
                    }`}
                  >
                    {role.id === "ANALYST" ? (
                      <TrendingUp className="w-4 h-4" />
                    ) : (
                      <ShieldCheck className="w-4 h-4" />
                    )}
                  </div>

                  {/* Role Content */}
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center justify-between">
                      <span className="text-sm font-semibold text-white">
                        {role.label} • {role.personaName}
                      </span>
                      {isSelected && (
                        <Check
                          className={`w-4 h-4 ${
                            role.themeColor === "brand"
                              ? "text-brand-400"
                              : "text-amber-400"
                          }`}
                        />
                      )}
                    </div>

                    <div className="text-[11px] font-medium text-slate-400 mt-0.5">
                      {role.title}
                    </div>

                    <div className="text-[11px] text-slate-400/90 leading-relaxed mt-1 line-clamp-2">
                      {role.description}
                    </div>
                  </div>
                </button>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}
