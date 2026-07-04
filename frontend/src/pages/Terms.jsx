// Terms of Service stub page. Public route — anyone can read it without an account.
// This is a basic-coverage template. Have a lawyer review before relying on it
// for binding terms. Keep the structure flat + scannable; long walls of legal
// text actively reduce trust.
import React from "react";
import { Link } from "react-router-dom";
import Footer from "@/components/Footer";

export default function Terms() {
  return (
    <div className="min-h-screen bg-[var(--bg-app)] flex flex-col" data-testid="terms-page">
      <header className="bg-[var(--surface)] border-b border-[var(--border)]">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
          <Link to="/" className="font-heading text-base text-[var(--ink)]">
            Pro-Quote Estimating Tool
          </Link>
          <Link to="/" className="text-xs uppercase tracking-wider text-[var(--ink-2)] hover:text-[var(--ink)]">
            ← Back
          </Link>
        </div>
      </header>

      <main className="flex-1 max-w-3xl mx-auto px-4 sm:px-6 lg:px-8 py-10">
        <div className="text-xs uppercase tracking-[0.2em] text-[var(--muted)] mb-1">Legal</div>
        <h1 className="font-heading text-4xl text-[var(--ink)] mb-2">Terms of Service</h1>
        <p className="text-xs text-[var(--muted)] mb-8">
          Last updated: {new Date().toLocaleDateString("en-US", { month: "long", day: "numeric", year: "numeric" })}
        </p>

        <div className="prose prose-sm text-[var(--ink-2)] space-y-6 leading-relaxed">
          <section>
            <h2 className="font-heading text-xl text-[var(--ink)] mb-2">1. Acceptance</h2>
            <p>
              By creating an account or using Pro-Quote Estimating Tool (the &ldquo;Service&rdquo;), you agree to these Terms.
              If you do not agree, do not use the Service. You must be at least 18 years old and authorized to
              act on behalf of the contracting business you represent.
            </p>
          </section>

          <section>
            <h2 className="font-heading text-xl text-[var(--ink)] mb-2">2. Account &amp; Access</h2>
            <p>
              Access to the Service requires a valid signup code provided by Alside Supply (the &ldquo;Supplier&rdquo;)
              or an invite code from an existing company owner. You are responsible for keeping your login
              credentials secure and for all activity that occurs under your account.
            </p>
          </section>

          <section>
            <h2 className="font-heading text-xl text-[var(--ink)] mb-2">3. Permitted Use</h2>
            <p>
              The Service is provided to you as a tool to create, manage, and send job estimates to your customers.
              You may not:
            </p>
            <ul className="list-disc pl-6 space-y-1 mt-2">
              <li>Reverse-engineer, decompile, or attempt to extract the source code of the Service</li>
              <li>Copy, resell, or sublicense the Service or its content</li>
              <li>Use the Service to send spam, phishing emails, or other unsolicited communications</li>
              <li>Misrepresent the source of the pricing data or claim authorship of the application</li>
              <li>Use the Service for any illegal purpose or in violation of any applicable law</li>
            </ul>
          </section>

          <section>
            <h2 className="font-heading text-xl text-[var(--ink)] mb-2">4. Pricing &amp; Catalog</h2>
            <p>
              Material prices in the catalog are set by the Supplier and are provided for estimating purposes only.
              They do not constitute a binding offer to sell, and pricing is subject to change without notice. Labor
              costs are set by each contractor and are entirely the contractor&apos;s responsibility. Quotes generated
              by the Service are a contract between the contractor and the homeowner — the Supplier and the Service
              are not party to that contract.
            </p>
          </section>

          <section>
            <h2 className="font-heading text-xl text-[var(--ink)] mb-2">5. Your Content</h2>
            <p>
              You retain ownership of estimates, customer information, branding assets, and other content you upload.
              You grant us a limited license to store, transmit, and display that content solely to operate the Service
              on your behalf. You are responsible for ensuring you have the legal right to upload any content,
              including customer information.
            </p>
          </section>

          <section>
            <h2 className="font-heading text-xl text-[var(--ink)] mb-2">6. Intellectual Property</h2>
            <p>
              The Service&apos;s software, design, layout, copy, logos, and trademarks are owned by Howard&apos;s
              Estimating Tool and protected by U.S. copyright and trademark laws. You are granted a limited,
              non-exclusive, non-transferable license to use the Service while your account is in good standing.
            </p>
          </section>

          <section>
            <h2 className="font-heading text-xl text-[var(--ink)] mb-2">7. Disclaimer &amp; Limitation of Liability</h2>
            <p>
              The Service is provided &ldquo;as is&rdquo; without warranty of any kind. We do not guarantee that
              estimates produced are accurate, that emails will be delivered, or that the Service will be
              uninterrupted or error-free. To the maximum extent allowed by law, our total liability to you is
              limited to the amount you have paid for the Service in the prior 12 months (which may be $0).
            </p>
          </section>

          <section>
            <h2 className="font-heading text-xl text-[var(--ink)] mb-2">8. Termination</h2>
            <p>
              We may suspend or terminate your access at any time for violation of these Terms. You may close
              your account at any time. Upon termination, your data may be deleted after a reasonable period.
            </p>
          </section>

          <section>
            <h2 className="font-heading text-xl text-[var(--ink)] mb-2">9. Changes</h2>
            <p>
              We may update these Terms from time to time. Continued use of the Service after changes are posted
              constitutes acceptance of the new Terms.
            </p>
          </section>

          <section>
            <h2 className="font-heading text-xl text-[var(--ink)] mb-2">10. Contact</h2>
            <p>
              Questions about these Terms? Reach out to{" "}
              <a href="mailto:hhunt6677@yahoo.com" className="text-[var(--brand-text)] hover:underline">
                hhunt6677@yahoo.com
              </a>.
            </p>
          </section>

          <p className="text-xs text-[var(--muted)] mt-10 pt-6 border-t border-[var(--border)]">
            This is a general-purpose template. Consult a licensed attorney to tailor it to your specific business
            and jurisdiction before relying on it as a binding agreement.
          </p>
        </div>
      </main>

      <Footer />
    </div>
  );
}
