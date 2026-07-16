import type { Metadata } from "next";

import { SettingsView } from "@/components/settings-view";

export const metadata: Metadata = {
  title: "Settings",
};

export default function SettingsPage() {
  return (
    <div className="mx-auto w-full max-w-2xl px-4 py-12 sm:px-6">
      <header className="mb-8">
        <h1 className="text-3xl font-semibold tracking-tight">Settings</h1>
        <p className="mt-1 text-muted-foreground">
          Appearance, account, and notification preferences.
        </p>
      </header>

      <SettingsView />
    </div>
  );
}
