export type TableCategory = "sales" | "returns" | "inventory" | "dimensions";

export interface ColumnMetadata {
  name: string;
  type: string;
  nullable: boolean;
  isPrimaryKey?: boolean;
  isForeignKey?: boolean;
  references?: string;
  description: string;
}

export interface TableMetadata {
  name: string;
  displayName: string;
  category: TableCategory;
  categoryLabel: string;
  rowCountEstimate: number;
  description: string;
  primaryKey: string[];
  columns: ColumnMetadata[];
  sampleQuestions: string[];
}
