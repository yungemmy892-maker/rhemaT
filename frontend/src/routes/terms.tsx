import { createFileRoute, Link } from "@tanstack/react-router";
import { ArrowLeft, FileText } from "lucide-react";

export const Route = createFileRoute("/terms")({
  head: () => ({ meta: [{ title: "Terms of Service — VerseID" }] }),
  component: Terms,
});

function Terms() {
  return (
    <div className="min-h-screen bg-background">
      <div className="mx-auto max-w-2xl px-5 py-8">
        <div className="flex items-center gap-3 mb-8">
          <Link to="/" className="h-10 w-10 rounded-full glass grid place-items-center">
            <ArrowLeft className="h-4.5 w-4.5" />
          </Link>
          <div className="h-10 w-10 rounded-full bg-gradient-primary grid place-items-center">
            <FileText className="h-5 w-5 text-white" />
          </div>
          <div>
            <h1 className="font-display text-xl font-semibold">Terms of Service</h1>
            <p className="text-xs text-muted-foreground">Effective: January 2025</p>
          </div>
        </div>

        <div className="space-y-8 text-foreground">
          <Section title="Agreement">
            By creating a VerseID account or using the app you agree to these terms. If you do not
            agree, do not use VerseID.
          </Section>

          <Section title="The service">
            VerseID helps you identify Bible verses from voice or text input. The matching engine
            searches the public-domain King James Version (KJV) and World English Bible (WEB) texts.
            We make no guarantee that every verse will be identified correctly — fuzzy text matching
            has inherent limitations, especially for archaic KJV phrasing quoted in modern language.
          </Section>

          <Section title="Free plan">
            The free plan allows up to{" "}
            <strong>20 verse identifications per day</strong> (UTC). The limit resets automatically
            at midnight UTC each day. Saved verses, search history, and collections are available on
            the free plan with no limit.
          </Section>

          <Section title="Pro plan">
            <p>
              Pro removes the daily search limit and grants access to all current and future premium
              features. Pricing is in Nigerian Naira (₦):
            </p>
            <ul className="mt-2 space-y-1 list-disc list-inside text-muted-foreground">
              <li>Monthly: ₦1,000/month</li>
              <li>Annual: ₦9,000/year (saves ₦3,000 vs monthly)</li>
            </ul>
            <p className="mt-2">
              Payment is processed by Paystack. Subscriptions renew automatically. You may cancel at
              any time from the Subscription screen — your Pro access continues until the end of the
              current billing period, after which you revert to the free plan.
            </p>
            <p className="mt-2">
              Prices are subject to change. We will give at least 30 days' notice of any price increase
              by email before the change takes effect on your subscription.
            </p>
          </Section>

          <Section title="Refunds">
            Refunds are not available for partial billing periods. If you experience a technical
            failure that prevents you from using Pro features you were charged for, contact us within
            7 days and we will review your case.
          </Section>

          <Section title="Accounts">
            <ul className="space-y-1 list-disc list-inside text-muted-foreground">
              <li>You must be at least 13 years old to create an account.</li>
              <li>You are responsible for keeping your login credentials secure.</li>
              <li>
                Each account is for a single user. Sharing accounts or attempting to circumvent the
                daily search limit through multiple accounts is not permitted.
              </li>
            </ul>
          </Section>

          <Section title="Content and Bible text">
            The KJV and WEB Bible texts used by VerseID are in the public domain. The VerseID app,
            its matching engine, UI, and associated code are proprietary. You may not copy, scrape,
            or reverse-engineer any part of VerseID.
          </Section>

          <Section title="Disclaimers">
            VerseID is provided "as is." We do not warrant that the service will be uninterrupted or
            error-free. Verse identifications are best-effort and should not be relied on for
            theological scholarship without independent verification.
          </Section>

          <Section title="Governing law">
            These terms are governed by the laws of the Federal Republic of Nigeria. Any disputes
            will be resolved in the courts of Lagos State, Nigeria.
          </Section>

          <Section title="Contact">
            Questions about these terms? Email{" "}
            <a href="mailto:legal@verseid.app" className="text-primary">
              legal@verseid.app
            </a>
            .
          </Section>
        </div>

        <div className="mt-12 flex gap-4 text-xs text-muted-foreground">
          <Link to="/privacy" className="hover:text-foreground transition">Privacy Policy</Link>
          <Link to="/help" className="hover:text-foreground transition">Help</Link>
          <Link to="/" className="hover:text-foreground transition">Home</Link>
        </div>
      </div>
    </div>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div>
      <h2 className="font-display text-base font-semibold mb-2">{title}</h2>
      <div className="text-sm text-muted-foreground leading-relaxed space-y-2">{children}</div>
    </div>
  );
}
