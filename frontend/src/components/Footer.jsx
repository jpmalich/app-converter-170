// Tiny global footer: copyright + Terms + Privacy links. Mounted inside Layout
// (so authed contractors see it) AND on the public Login + Accept pages via
// direct import. Kept small + unobtrusive so it doesn't dominate the layout.
import React from "react";
import { Link } from "react-router-dom";

export default function Footer() {
  const year = new Date().getFullYear();
  return (
    <footer
      className="mt-12 py-6 border-t border-[var(--border)] bg-[var(--surface)]"
      data-testid="site-footer"
    >
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex flex-col sm:flex-row items-center justify-between gap-3 text-xs text-[var(--muted)]">
        <div>
          © {year} Pro-Quote Estimating Tool. All rights reserved.
        </div>
        <div className="flex items-center gap-4">
          <Link to="/terms" className="hover:text-[var(--ink)]" data-testid="footer-terms">
            Terms of Service
          </Link>
          <Link to="/privacy" className="hover:text-[var(--ink)]" data-testid="footer-privacy">
            Privacy Policy
          </Link>
        </div>
      </div>
    </footer>
  );
}
