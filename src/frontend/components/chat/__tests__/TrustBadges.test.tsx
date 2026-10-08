import { render, screen } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import React from "react";
import { TrustBadges } from "../TrustBadges";

describe("TrustBadges component", () => {
  it("1. should render AST Sanitized badge when astVerified is true", () => {
    render(<TrustBadges astVerified={true} />);

    const badge = screen.getByText("AST Sanitized");
    expect(badge).toBeInTheDocument();
    expect(badge.parentElement?.className).toContain("text-emerald-400");
  });

  it("2. should render RBAC Enforced badge with user role", () => {
    render(<TrustBadges rbacEnforced={true} role="Admin" />);

    const badge = screen.getByText(/RBAC: Admin|RBAC Enforced/i);
    expect(badge).toBeInTheDocument();
  });

  it("3. should render PII Protected badge when piiProtected is true", () => {
    render(<TrustBadges piiProtected={true} />);

    const badge = screen.getByText("PII Protected");
    expect(badge).toBeInTheDocument();
    expect(badge.parentElement?.className).toContain("text-amber-400");
  });

  it("4. should render multiple active badges simultaneously", () => {
    render(
      <TrustBadges
        astVerified={true}
        rbacEnforced={true}
        role="Analyst"
        piiProtected={true}
      />
    );

    expect(screen.getByText("AST Sanitized")).toBeInTheDocument();
    expect(screen.getByText(/RBAC: Analyst|RBAC Enforced/i)).toBeInTheDocument();
    expect(screen.getByText("PII Protected")).toBeInTheDocument();
  });

  it("5. should return null if no security flags are enabled", () => {
    const { container } = render(<TrustBadges />);
    expect(container.firstChild).toBeNull();
  });
});
