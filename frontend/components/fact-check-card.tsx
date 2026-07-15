import {
  BadgeCheck,
  BadgeX,
  CircleHelp,
  ExternalLink,
  TriangleAlert,
} from "lucide-react";

import type { FactCheck, FactCheckVerdict } from "@/lib/types";
import { cn } from "@/lib/utils";

const verdictConfig: Record<
  FactCheckVerdict,
  { label: string; icon: typeof BadgeCheck; className: string }
> = {
  true: {
    label: "True",
    icon: BadgeCheck,
    className:
      "text-green-700 bg-green-500/10 border-green-500/30 dark:text-green-400",
  },
  false: {
    label: "False",
    icon: BadgeX,
    className:
      "text-red-700 bg-red-500/10 border-red-500/30 dark:text-red-400",
  },
  misleading: {
    label: "Misleading",
    icon: TriangleAlert,
    className:
      "text-amber-700 bg-amber-500/10 border-amber-500/30 dark:text-amber-400",
  },
  unverified: {
    label: "Unverified",
    icon: CircleHelp,
    className:
      "text-muted-foreground bg-muted/50 border-border",
  },
};

interface FactCheckCardProps {
  factCheck: FactCheck;
}

/** AI fact-check result as shown inline in the debate chat. */
export function FactCheckCard({ factCheck }: FactCheckCardProps) {
  const config = verdictConfig[factCheck.verdict];
  const Icon = config.icon;

  return (
    <div className="rounded-lg border border-border bg-card p-3 text-sm">
      <div className="flex items-center justify-between gap-2">
        <span className="text-xs font-medium tracking-wide text-muted-foreground uppercase">
          AI fact-check
        </span>
        <span
          className={cn(
            "inline-flex items-center gap-1 rounded-md border px-1.5 py-0.5 text-xs font-medium",
            config.className,
          )}
        >
          <Icon className="size-3.5" />
          {config.label}
        </span>
      </div>

      <p className="mt-2 border-l-2 border-border pl-2 text-muted-foreground italic">
        “{factCheck.claim}”
      </p>

      <p className="mt-2">{factCheck.explanation}</p>

      {factCheck.sources.length > 0 && (
        <ul className="mt-2 space-y-1">
          {factCheck.sources.map((source) => (
            <li key={source.url}>
              <a
                href={source.url}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-1 text-xs text-primary hover:underline"
              >
                <ExternalLink className="size-3" />
                {source.title}
              </a>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
