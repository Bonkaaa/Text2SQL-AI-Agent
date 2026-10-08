import { describe, it, expect } from "vitest";
import tailwindConfig from "../tailwind.config";
import fs from "fs";
import path from "path";

describe("Design Tokens & Typography Specification (Task 1.1)", () => {
  it("should define enterprise Slate/Zinc surface colors and brand tokens in tailwind.config", () => {
    const theme = tailwindConfig.theme?.extend;
    expect(theme).toBeDefined();

    // Check background & surface tokens
    expect(theme?.colors).toBeDefined();
    const colors = theme?.colors as Record<string, any>;

    // Background should be deep obsidian/slate #0B0F17
    expect(colors.background).toBe("#0B0F17");

    // Surface levels (Enterprise Slate/Zinc)
    expect(colors.surface).toBeDefined();
    expect(colors.surface.DEFAULT).toBe("#111827"); // surface-primary (Gray 900)
    expect(colors.surface.secondary).toBe("#1F2937"); // Gray 800
    expect(colors.surface.tertiary).toBe("#374151"); // Gray 700
  });

  it("should define an accessible 6-series Data Viz Palette in tailwind.config", () => {
    const theme = tailwindConfig.theme?.extend;
    const colors = theme?.colors as Record<string, any>;

    expect(colors.viz).toBeDefined();
    expect(colors.viz[1]).toBe("#3B82F6"); // Electric Blue
    expect(colors.viz[2]).toBe("#10B981"); // Emerald Teal
    expect(colors.viz[3]).toBe("#F59E0B"); // Warm Amber
    expect(colors.viz[4]).toBe("#8B5CF6"); // Royal Violet
    expect(colors.viz[5]).toBe("#06B6D4"); // Bright Cyan
    expect(colors.viz[6]).toBe("#EC4899"); // Vibrant Coral
  });

  it("should configure Plus Jakarta Sans and JetBrains Mono fonts", () => {
    const theme = tailwindConfig.theme?.extend;
    const fontFamily = theme?.fontFamily as Record<string, any>;

    expect(fontFamily).toBeDefined();
    expect(fontFamily.sans).toEqual(
      expect.arrayContaining([expect.stringContaining("Plus Jakarta Sans")])
    );
    expect(fontFamily.mono).toEqual(
      expect.arrayContaining([expect.stringContaining("JetBrains Mono")])
    );
  });

  it("should have tabular-nums utility in globals.css and no legacy .orb-3d class", () => {
    const globalsCssPath = path.resolve(__dirname, "../app/globals.css");
    const cssContent = fs.readFileSync(globalsCssPath, "utf-8");

    // Should contain tabular-nums for numeric precision
    expect(cssContent).toContain("tabular-nums");
    expect(cssContent).toContain(".font-mono-data");

    // Should NOT contain legacy AI cliches: .orb-3d or animate-pulse-glow
    expect(cssContent).not.toContain(".orb-3d");
    expect(cssContent).not.toContain(".animate-pulse-glow");
  });
});
