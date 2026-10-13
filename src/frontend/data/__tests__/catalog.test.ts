import { describe, it, expect } from "vitest";
import {
  TPCH_TABLES,
  getTablesByCategory,
  searchTables,
  getTableByName,
} from "../tpchCatalog";

describe("TPC-H Catalog & Schema Metadata (TDD Suite)", () => {
  it("should contain exactly 8 benchmark tables", () => {
    expect(TPCH_TABLES).toBeDefined();
    expect(TPCH_TABLES.length).toBe(8);
    const tableNames = TPCH_TABLES.map((t) => t.name);
    expect(tableNames).toEqual(
      expect.arrayContaining([
        "orders",
        "lineitem",
        "customer",
        "part",
        "partsupp",
        "supplier",
        "nation",
        "region",
      ])
    );
  });

  it("should cover key fact and dimension tables with rich columns and PK/FK constraints", () => {
    // 1. Lineitem table
    const lineitem = getTableByName("lineitem");
    expect(lineitem).toBeDefined();
    expect(lineitem?.category).toBe("transactions");
    expect(lineitem?.primaryKey).toEqual(["l_orderkey", "l_linenumber"]);
    expect(lineitem?.columns.some((c) => c.name === "l_extendedprice")).toBe(true);
    expect(lineitem?.columns.some((c) => c.name === "l_discount")).toBe(true);
    expect(lineitem?.columns.some((c) => c.name === "l_shipdate")).toBe(true);
    expect(lineitem?.sampleQuestions.length).toBeGreaterThan(0);

    // 2. Orders table
    const orders = getTableByName("orders");
    expect(orders).toBeDefined();
    expect(orders?.category).toBe("transactions");
    expect(orders?.primaryKey).toEqual(["o_orderkey"]);
    expect(orders?.columns.some((c) => c.name === "o_orderdate")).toBe(true);
    expect(orders?.columns.some((c) => c.name === "o_totalprice")).toBe(true);

    // 3. Customer table
    const customer = getTableByName("customer");
    expect(customer).toBeDefined();
    expect(customer?.category).toBe("partners_customers");
    expect(customer?.columns.some((c) => c.name === "c_mktsegment")).toBe(true);

    // 4. PartSupp table (composite PK)
    const partsupp = getTableByName("partsupp");
    expect(partsupp).toBeDefined();
    expect(partsupp?.category).toBe("products_inventory");
    expect(partsupp?.primaryKey).toEqual(["ps_partkey", "ps_suppkey"]);

    // 5. Region table
    const region = getTableByName("region");
    expect(region).toBeDefined();
    expect(region?.category).toBe("geography");
    expect(region?.primaryKey).toEqual(["r_regionkey"]);
  });

  it("should filter tables by 4 supply-chain categories", () => {
    const transactions = getTablesByCategory("transactions");
    expect(transactions.map((t) => t.name).sort()).toEqual(["lineitem", "orders"]);

    const products = getTablesByCategory("products_inventory");
    expect(products.map((t) => t.name).sort()).toEqual(["part", "partsupp"]);

    const partners = getTablesByCategory("partners_customers");
    expect(partners.map((t) => t.name).sort()).toEqual(["customer", "supplier"]);

    const geography = getTablesByCategory("geography");
    expect(geography.map((t) => t.name).sort()).toEqual(["nation", "region"]);
  });

  it("should search tables by query string on name, displayName, and columns", () => {
    // Search table name
    const custResults = searchTables("customer");
    expect(custResults.some((t) => t.name === "customer")).toBe(true);

    // Search column name
    const lineitemResults = searchTables("l_extendedprice");
    expect(lineitemResults.some((t) => t.name === "lineitem")).toBe(true);

    // Search description/Vietnamese keyword
    const nationResults = searchTables("quốc gia");
    expect(nationResults.some((t) => t.name === "nation")).toBe(true);
  });
});
