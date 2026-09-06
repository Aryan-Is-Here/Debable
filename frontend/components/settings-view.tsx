"use client";

import { useState, useSyncExternalStore } from "react";
import { useUser } from "@clerk/nextjs";
import { useTheme } from "next-themes";
import { Monitor, Moon, Sun } from "lucide-react";
import { toast } from "sonner";

import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Switch } from "@/components/ui/switch";
import { Field, FieldDescription, FieldLabel } from "@/components/ui/field";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";

const themeOptions = [
  { value: "light", label: "Light", icon: Sun },
  { value: "dark", label: "Dark", icon: Moon },
  { value: "system", label: "System", icon: Monitor },
] as const;

/**
 * Settings screen. Appearance is fully functional (next-themes); account
 * fields are read-only until Clerk lands (Phase 2); notifications and the
 * danger zone are mock-only.
 */
export function SettingsView() {
  const { theme, setTheme } = useTheme();
  const { user } = useUser();
  // Em dashes rather than empty inputs while Clerk loads: a blank field reads as "you have
  // no username", which is a different and wrong statement.
  const username = user?.username ?? user?.firstName ?? "—";
  const email = user?.primaryEmailAddress?.emailAddress ?? "—";
  // Theme is unknown until hydration; treat server render as "not mounted" so
  // the selected state only appears client-side (avoids a hydration mismatch).
  const mounted = useSyncExternalStore(
    () => () => {},
    () => true,
    () => false,
  );

  const [notifyMatches, setNotifyMatches] = useState(true);
  const [notifyRatings, setNotifyRatings] = useState(false);
  const [deleteOpen, setDeleteOpen] = useState(false);

  return (
    <div className="space-y-6">
      {/* Appearance */}
      <Card>
        <CardHeader>
          <CardTitle>Appearance</CardTitle>
          <CardDescription>How Debable looks on this device.</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-3 gap-3" role="radiogroup" aria-label="Theme">
            {themeOptions.map((option) => {
              const selected = mounted && theme === option.value;
              return (
                <button
                  key={option.value}
                  type="button"
                  role="radio"
                  aria-checked={selected}
                  onClick={() => setTheme(option.value)}
                  className={cn(
                    "flex flex-col items-center gap-2 rounded-lg border border-border p-4 text-sm transition-colors outline-none",
                    "hover:bg-muted focus-visible:ring-3 focus-visible:ring-ring/50",
                    selected && "border-primary bg-primary/5",
                  )}
                >
                  <option.icon className="size-5" />
                  {option.label}
                </button>
              );
            })}
          </div>
        </CardContent>
      </Card>

      {/* Account */}
      <Card>
        <CardHeader>
          <CardTitle>Account</CardTitle>
          <CardDescription>
            Read-only here: Clerk owns your identity, so changes are made in its
            account dialog rather than duplicated in a form that could disagree
            with it.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <Field>
            <FieldLabel htmlFor="username">Username</FieldLabel>
            <Input id="username" value={username} disabled />
          </Field>
          <Field>
            <FieldLabel htmlFor="email">Email</FieldLabel>
            <Input id="email" value={email} disabled />
            <FieldDescription>
              Managed by your sign-in provider.
            </FieldDescription>
          </Field>
        </CardContent>
      </Card>

      {/* Notifications */}
      <Card>
        <CardHeader>
          <CardTitle>Notifications</CardTitle>
          <CardDescription>
            Prototype-only toggles — delivery arrives with the backend.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <Field orientation="horizontal">
            <FieldLabel htmlFor="notify-matches">Match found</FieldLabel>
            <Switch
              id="notify-matches"
              checked={notifyMatches}
              onCheckedChange={setNotifyMatches}
            />
          </Field>
          <Field orientation="horizontal">
            <FieldLabel htmlFor="notify-ratings">New rating received</FieldLabel>
            <Switch
              id="notify-ratings"
              checked={notifyRatings}
              onCheckedChange={setNotifyRatings}
            />
          </Field>
        </CardContent>
      </Card>

      {/* Danger zone */}
      <Card className="border-destructive/40">
        <CardHeader>
          <CardTitle>Danger zone</CardTitle>
          <CardDescription>Irreversible account actions.</CardDescription>
        </CardHeader>
        <CardContent>
          <Dialog open={deleteOpen} onOpenChange={setDeleteOpen}>
            <DialogTrigger render={<Button variant="destructive" />}>
              Delete account
            </DialogTrigger>
            <DialogContent>
              <DialogHeader>
                <DialogTitle>Delete account?</DialogTitle>
                <DialogDescription>
                  This would permanently remove your profile, topics, and
                  debate history. (Mock only — nothing is deleted in the
                  prototype.)
                </DialogDescription>
              </DialogHeader>
              <DialogFooter>
                <Button variant="ghost" onClick={() => setDeleteOpen(false)}>
                  Cancel
                </Button>
                <Button
                  variant="destructive"
                  onClick={() => {
                    setDeleteOpen(false);
                    toast("Account deletion is mocked in the prototype.");
                  }}
                >
                  Delete
                </Button>
              </DialogFooter>
            </DialogContent>
          </Dialog>
        </CardContent>
      </Card>
    </div>
  );
}
