import { createFileRoute, Link } from "@tanstack/react-router";
import { ArrowLeft, Shield } from "lucide-react";

export const Route = createFileRoute("/privacy")({
  head: () => ({ meta: [{ title: "Privacy Policy — VerseID" }] }),
  component: Privacy,
});

function Privacy() {
  return (
    <div className="min-h-screen bg-background">
      <div className="mx-auto max-w-2xl px-5 py-8">
        <div className="flex items-center gap-3 mb-8">
          <Link to="/" className="h-10 w-10 rounded-full glass grid place-items-center">
            <ArrowLeft className="h-4.5 w-4.5" />
          </Link>
          <div className="h-10 w-10 rounded-full bg-gradient-primary grid place-items-center">
            <Shield className="h-5 w-5 text-white" />
          </div>
          <div>
            <h1 className="font-display text-xl font-semibold">Privacy Policy</h1>
            <p className="text-xs text-muted-foreground">Effective: January 2025</p>
          </div>
        </div>

        <div className="prose prose-sm max-w-none space-y-8 text-foreground">
          <Section title="Who we are">
            VerseID is a Bible verse identification app that helps you find any verse from a few spoken
            or typed words. We take your privacy seriously and collect only what is necessary to provide
            the service.
          </Section>

          <Section title="What we collect">
            <ul className="space-y-2 list-disc list-inside text-muted-foreground">
              <li>
                <strong className="text-foreground">Account information</strong> — your name, email
                address, and (if you use Google Sign-In) your Google account ID and profile photo.
              </li>
              <li>
                <strong className="text-foreground">Search queries</strong> — the text of each verse
                identification you perform, stored so we can show your search history and calculate
                your streak.
              </li>
              <li>
                <strong className="text-foreground">Saved verses</strong> — the verse references you
                save to your library.
              </li>
              <li>
                <strong className="text-foreground">Settings and preferences</strong> — your chosen
                Bible version, notification preferences, and notification schedule.
              </li>
              <li>
                <strong className="text-foreground">Profile photo</strong> — if you upload one, stored
                securely on our servers and never shared with third parties.
              </li>
              <li>
                <strong className="text-foreground">Payment reference</strong> — if you subscribe to
                Pro, we store the Paystack transaction reference and your subscription status. We never
                see or store your card number — all card data is handled entirely by Paystack.
              </li>
            </ul>
          </Section>

          <Section title="Voice and speech">
            When you use the voice search feature, your speech is processed entirely by your browser's
            built-in Web Speech API. Audio is never uploaded to our servers — only the text transcript
            that your browser produces is sent to us to find a matching verse.
          </Section>

          <Section title="How we use your data">
            <ul className="space-y-2 list-disc list-inside text-muted-foreground">
              <li>To identify Bible verses from your queries and return results.</li>
              <li>To maintain your search history, saved verses, and reading streak.</li>
              <li>To send you the daily verse notification (if you've enabled it).</li>
              <li>To manage your Pro subscription and enforce free-tier search limits.</li>
              <li>We never sell your data. We never show you ads.</li>
            </ul>
          </Section>

          <Section title="Third-party services">
            <ul className="space-y-2 list-disc list-inside text-muted-foreground">
              <li>
                <strong className="text-foreground">Google Identity Services</strong> — for optional
                Google Sign-In. If you use this, Google's privacy policy applies to the sign-in step.
              </li>
              <li>
                <strong className="text-foreground">Paystack</strong> — for Pro subscription
                payments. Paystack is PCI-DSS compliant and handles all card data. Their privacy policy
                is at paystack.com/privacy.
              </li>
              <li>
                <strong className="text-foreground">DiceBear</strong> — generates a default avatar
                image from your name if you don't have a Google profile photo and haven't uploaded one.
                No personal data is shared — only an anonymous seed word.
              </li>
            </ul>
          </Section>

          <Section title="Data retention">
            Your account data is retained for as long as your account exists. You can delete your
            account at any time from Settings, which permanently removes all your data from our
            servers within 24 hours.
          </Section>

          <Section title="Your rights">
            You can export or delete your data at any time by contacting us at{" "}
            <a href="mailto:privacy@verseid.app" className="text-primary">
              privacy@verseid.app
            </a>{" "}
            or by deleting your account in Settings → Delete account.
          </Section>

          <Section title="Contact">
            Questions about this policy? Email{" "}
            <a href="mailto:privacy@verseid.app" className="text-primary">
              privacy@verseid.app
            </a>
            .
          </Section>
        </div>

        <div className="mt-12 flex gap-4 text-xs text-muted-foreground">
          <Link to="/terms" className="hover:text-foreground transition">Terms of Service</Link>
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
      <div className="text-sm text-muted-foreground leading-relaxed">{children}</div>
    </div>
  );
}
