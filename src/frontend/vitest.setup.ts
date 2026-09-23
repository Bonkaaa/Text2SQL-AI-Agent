import "@testing-library/jest-dom/vitest";

// Mock ResizeObserver for Recharts ResponsiveContainer in jsdom environment
class ResizeObserverMock {
  observe() {}
  unobserve() {}
  disconnect() {}
}

if (typeof window !== "undefined") {
  window.ResizeObserver = ResizeObserverMock;
}
global.ResizeObserver = ResizeObserverMock;
