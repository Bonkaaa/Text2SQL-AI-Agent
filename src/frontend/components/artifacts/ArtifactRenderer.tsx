"use client";

import React, { useMemo } from "react";
import type {
  ArtifactItem,
  ArtifactLayout,
  KpiArtifact,
} from "../../types/artifacts";
import { KPIArtifactGrid } from "./KPIArtifactGrid";
import { ExecutiveSummaryCard } from "./ExecutiveSummaryCard";
import { EvidenceCard } from "./EvidenceCard";
import { CalloutCard } from "./CalloutCard";
import { FileCard } from "./FileCard";
import { DynamicChart } from "../analytics/DynamicChart";
import { DataTable } from "../analytics/DataTable";

export interface ArtifactRendererProps {
  artifacts: ArtifactItem[];
  layout?: ArtifactLayout;
  directAnswer?: string | null;
  detailedInsight?: string[] | null;
  className?: string;
}

export const ArtifactRenderer: React.FC<ArtifactRendererProps> = ({
  artifacts,
  layout = "stacked",
  directAnswer,
  detailedInsight,
  className = "",
}) => {
  const hasSummary = Boolean(
    (directAnswer && directAnswer.trim().length > 0) ||
      (detailedInsight && detailedInsight.length > 0)
  );

  // Tách các thẻ KPI ra để hiển thị dạng lưới ở trên cùng
  const { kpis, otherArtifacts } = useMemo(() => {
    const kpiList: KpiArtifact[] = [];
    const others: ArtifactItem[] = [];

    (artifacts || []).forEach((art) => {
      if (art.type === "kpi") {
        kpiList.push(art);
      } else {
        others.push(art);
      }
    });

    return { kpis: kpiList, otherArtifacts: others };
  }, [artifacts]);

  if (!hasSummary && kpis.length === 0 && otherArtifacts.length === 0) {
    return null;
  }

  // Render từng primitive artifact theo discriminated type
  const renderArtifactItem = (item: ArtifactItem, index: number) => {
    switch (item.type) {
      case "chart":
        return <DynamicChart key={`chart-${index}`} artifact={item} />;
      case "table":
        return <DataTable key={`table-${index}`} artifact={item} />;
      case "evidence":
        return <EvidenceCard key={`evidence-${index}`} artifact={item} />;
      case "callout":
        return <CalloutCard key={`callout-${index}`} artifact={item} />;
      case "file":
        return <FileCard key={`file-${index}`} artifact={item} />;
      default:
        return null;
    }
  };

  const isGrid = layout === "dashboard_grid";

  return (
    <div className={`space-y-4 my-2 ${className}`}>
      {/* 1. Executive Summary: Nhận định điều hành trực diện */}
      {hasSummary && (
        <ExecutiveSummaryCard
          directAnswer={directAnswer}
          detailedInsight={detailedInsight}
        />
      )}

      {/* 2. KPI Metric Cards Grid: Chỉ số định lượng */}
      {kpis.length > 0 && <KPIArtifactGrid kpis={kpis} />}

      {/* 3. Phối cảnh các Artifacts trực quan (Charts, Tables, Evidences, Files, Callouts) */}
      {otherArtifacts.length > 0 && (
        <div
          className={
            isGrid
              ? "grid grid-cols-1 lg:grid-cols-2 gap-4 items-start"
              : "flex flex-col gap-4"
          }
        >
          {otherArtifacts.map((item, idx) => (
            <div
              key={idx}
              className={
                isGrid && item.type === "table" ? "lg:col-span-2" : "w-full"
              }
            >
              {renderArtifactItem(item, idx)}
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default ArtifactRenderer;
