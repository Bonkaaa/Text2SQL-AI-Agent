"use client";

import React, { useState, useMemo } from "react";
import { useRouter } from "next/navigation";
import {
  Bookmark,
  Search,
  ArrowUpRight,
  Trash2,
  Copy,
  Check,
  Code2,
  Tag,
  Plus,
} from "lucide-react";
import Link from "next/link";
import { useSavedQueries } from "@/hooks/useSavedQueries";
import { SavedQueryItem } from "@/lib/storage";

export default function SavedQueriesPage() {
  const router = useRouter();
  const { savedQueries, removeQuery } = useSavedQueries();
  const [search, setSearch] = useState("");
  const [selectedTag, setSelectedTag] = useState<string>("All");
  const [copiedId, setCopiedId] = useState<string | null>(null);

  const tags = useMemo(() => {
    const set = new Set<string>();
    savedQueries.forEach((q) => {
      if (q.tag) set.add(q.tag);
    });
    return ["All", ...Array.from(set)];
  }, [savedQueries]);

  const filteredQueries = useMemo(() => {
    return savedQueries.filter((item) => {
      const matchTag = selectedTag === "All" || item.tag === selectedTag;
      if (!matchTag) return false;

      if (!search.trim()) return true;
      const term = search.toLowerCase();
      return (
        item.title.toLowerCase().includes(term) ||
        item.question.toLowerCase().includes(term) ||
        (item.sql && item.sql.toLowerCase().includes(term))
      );
    });
  }, [savedQueries, selectedTag, search]);

  const handleOpen = (item: SavedQueryItem) => {
    router.push(`/workspace?q=${encodeURIComponent(item.question)}`);
  };

  const handleCopySQL = async (item: SavedQueryItem) => {
    if (!item.sql) return;
    try {
      await navigator.clipboard.writeText(item.sql);
      setCopiedId(item.id);
      setTimeout(() => setCopiedId(null), 2000);
    } catch {
      // Fallback
    }
  };

  return (
    <div className="space-y-6">
      {/* Page Heading & Header Actions */}
      <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-4">
        <div>
          <div className="text-primary text-[10px] font-extrabold uppercase tracking-widest mb-1.5">
            Reusable analytics library
          </div>
          <h1 className="text-2xl md:text-3xl font-extrabold tracking-tight text-foreground">
            Saved queries
          </h1>
          <p className="text-muted text-xs md:text-sm mt-1 max-w-2xl leading-relaxed">
            Keep verified business questions and their SQL close at hand. Rerun them whenever data updates.
          </p>
        </div>

        <Link
          href="/workspace"
          className="inline-flex items-center gap-2 bg-primary hover:bg-primary-strong text-white px-3.5 py-2 rounded-lg text-xs font-bold transition shadow-sm"
        >
          <Plus className="w-4 h-4" />
          <span>New query in Workspace</span>
        </Link>
      </div>

      {/* Filter and Search Bar */}
      <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3">
        {/* Tag Filter Chips */}
        <div className="flex items-center gap-1.5 overflow-x-auto">
          {tags.map((tag) => (
            <button
              key={tag}
              type="button"
              onClick={() => setSelectedTag(tag)}
              className={`px-3 py-1.5 rounded-lg text-xs font-semibold whitespace-nowrap transition ${
                selectedTag === tag
                  ? "bg-primary text-white font-bold shadow-xs"
                  : "bg-surface border border-line text-muted hover:text-foreground hover:bg-surface-2"
              }`}
            >
              {tag}
            </button>
          ))}
        </div>

        {/* Search */}
        <div className="flex items-center gap-2 border border-line rounded-lg px-2.5 h-9 bg-surface text-xs text-muted w-full sm:w-72">
          <Search className="w-3.5 h-3.5 text-muted shrink-0" />
          <input
            type="text"
            placeholder="Search saved queries..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full bg-transparent border-0 outline-none text-xs text-foreground placeholder:text-muted"
          />
        </div>
      </div>

      {/* Saved Queries Table */}
      <div className="bg-surface border border-line rounded-xl shadow-card overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs whitespace-nowrap">
            <thead className="bg-surface-2 text-muted text-[10px] font-bold uppercase border-b border-line">
              <tr>
                <th className="p-3">Query Title & Question</th>
                <th className="p-3">Category</th>
                <th className="p-3">Saved Date</th>
                <th className="p-3">Owner</th>
                <th className="p-3 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-line">
              {filteredQueries.length === 0 ? (
                <tr>
                  <td colSpan={5} className="p-8 text-center text-xs text-muted">
                    No saved queries found. You can bookmark queries directly from Workspace.
                  </td>
                </tr>
              ) : (
                filteredQueries.map((item) => (
                  <tr key={item.id} className="hover:bg-surface-2/60 transition">
                    <td className="p-3 max-w-md">
                      <strong className="text-foreground block text-xs truncate">
                        {item.title}
                      </strong>
                      <span className="text-muted text-[11px] block mt-0.5 truncate">
                        “{item.question}”
                      </span>
                    </td>

                    <td className="p-3">
                      {item.tag ? (
                        <span className="text-[10px] bg-primary-soft text-primary font-bold px-2 py-0.5 rounded-full inline-flex items-center gap-1 border border-primary/20">
                          <Tag className="w-2.5 h-2.5" />
                          {item.tag}
                        </span>
                      ) : (
                        <span className="text-muted text-[11px]">—</span>
                      )}
                    </td>

                    <td className="p-3 font-mono text-[11px] text-muted">
                      {item.createdAt}
                    </td>

                    <td className="p-3 text-[11px] text-foreground font-semibold">
                      {item.owner || "Analyst"}
                    </td>

                    <td className="p-3 text-right">
                      <div className="inline-flex items-center gap-1.5">
                        {item.sql && (
                          <button
                            type="button"
                            onClick={() => handleCopySQL(item)}
                            title="Copy SQL"
                            className="p-1.5 rounded-lg border border-line hover:bg-surface-2 text-muted hover:text-foreground transition"
                          >
                            {copiedId === item.id ? (
                              <Check className="w-3.5 h-3.5 text-emerald" />
                            ) : (
                              <Copy className="w-3.5 h-3.5" />
                            )}
                          </button>
                        )}

                        <button
                          type="button"
                          onClick={() => handleOpen(item)}
                          className="inline-flex items-center gap-1 bg-primary-soft hover:bg-primary-soft/80 text-primary border border-primary/20 px-2.5 py-1.5 rounded-lg text-xs font-bold transition"
                        >
                          <span>Open</span>
                          <ArrowUpRight className="w-3 h-3" />
                        </button>

                        <button
                          type="button"
                          onClick={() => removeQuery(item.id)}
                          title="Delete saved query"
                          className="p-1.5 rounded-lg border border-line hover:bg-rose-soft/40 text-muted hover:text-rose transition"
                        >
                          <Trash2 className="w-3.5 h-3.5" />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
