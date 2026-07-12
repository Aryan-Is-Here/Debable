"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { MessagesSquare } from "lucide-react";

import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { ThemeToggle } from "@/components/theme-toggle";

/** Primary navigation targets. Some routes arrive in later Phase 1 sub-steps. */
const navItems = [
  { href: "/", label: "Home" },
  { href: "/browse", label: "Browse" },
  { href: "/create", label: "Create" },
] as const;

export function SiteHeader() {
  const pathname = usePathname();

  return (
    <header className="sticky top-0 z-40 w-full border-b border-border bg-background/80 backdrop-blur supports-[backdrop-filter]:bg-background/60">
      <div className="mx-auto flex h-16 w-full max-w-6xl items-center gap-6 px-4 sm:px-6">
        <Link href="/" className="flex items-center gap-2 font-semibold">
          <MessagesSquare className="size-5 text-primary" />
          <span>DebateMatch</span>
        </Link>

        <nav className="hidden items-center gap-1 sm:flex">
          {navItems.map((item) => {
            const isActive =
              item.href === "/"
                ? pathname === "/"
                : pathname.startsWith(item.href);
            return (
              <Button
                key={item.href}
                render={<Link href={item.href} />}
                variant="ghost"
                size="sm"
                className={cn(
                  "text-muted-foreground",
                  isActive && "text-foreground",
                )}
              >
                {item.label}
              </Button>
            );
          })}
        </nav>

        <div className="ml-auto flex items-center gap-2">
          <ThemeToggle />
          {/* Placeholder — real auth is wired to Clerk in Phase 2. */}
          <Button variant="outline" size="sm" disabled title="Available after Phase 2 (Clerk)">
            Sign in
          </Button>
        </div>
      </div>
    </header>
  );
}
