import { describe, it, expect } from "vitest";
import {
  TPCDS_TABLES,
  getTablesByCategory,
  searchTables,
  getTableByName,
} from "../tpcdsCatalog";

describe("TPC-DS Catalog & Schema Metadata (TDD Suite 2)", () => {
  it("should contain exactly 24 benchmark tables", () => {
    expect(TPCDS_TABLES).toBeDefined();
    expect(TPCDS_TABLES.length).toBe(24);
  });

  it("should cover key fact and dimension tables with rich columns", () => {
    const storeSales = getTableByName("store_sales");
    expect(storeSales).toBeDefined();
    expect(storeSales?.category).toBe("sales");
    expect(storeSales?.columns.some((c) => c.name === "ss_net_paid")).toBe(true);
    expect(storeSales?.sampleQuestions.length).toBeGreaterThan(0);

    const dateDim = getTableByName("date_dim");
    expect(dateDim).toBeDefined();
    expect(dateDim?.category).toBe("dimensions");
    expect(dateDim?.columns.some((c) => c.isPrimaryKey && c.name === "d_date_sk")).toBe(true);

    const inventory = getTableByName("inventory");
    expect(inventory).toBeDefined();
    expect(inventory?.category).toBe("inventory");
  });

  it("should filter tables by category", () => {
    const salesTables = getTablesByCategory("sales");
    expect(salesTables.map((t) => t.name)).toEqual(
      expect.arrayContaining(["store_sales", "catalog_sales", "web_sales"])
    );
    expect(salesTables.length).toBe(3);

    const returnTables = getTablesByCategory("returns");
    expect(returnTables.map((t) => t.name)).toEqual(
      expect.arrayContaining(["store_returns", "catalog_returns", "web_returns"])
    );
    expect(returnTables.length).toBe(3);
  });

  it("should search tables by query string", () => {
    const results = searchTables("customer");
    expect(results.length).toBeGreaterThanOrEqual(3);
    expect(results.some((t) => t.name === "customer")).toBe(true);
    expect(results.some((t) => t.name === "customer_address")).toBe(true);
  });
});
