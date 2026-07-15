"use client";

import { Mic, MicOff, Video as VideoIcon, VideoOff } from "lucide-react";

import type { UserSummary } from "@/lib/types";
import { cn, initials } from "@/lib/utils";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";

interface VideoTileProps {
  user: UserSummary;
  /** Marks the local participant's tile. */
  isYou?: boolean;
  muted?: boolean;
  cameraOff?: boolean;
  className?: string;
}

/**
 * Placeholder video tile for the Phase 1 prototype. Renders an avatar in a
 * 16:9 frame with mute/camera indicators; real LiveKit tracks land in Phase 5.
 */
export function VideoTile({
  user,
  isYou = false,
  muted = false,
  cameraOff = false,
  className,
}: VideoTileProps) {
  return (
    <div
      className={cn(
        "relative flex aspect-video w-full items-center justify-center overflow-hidden rounded-lg border border-border bg-muted/40",
        className,
      )}
    >
      {cameraOff ? (
        <div className="flex flex-col items-center gap-2 text-muted-foreground">
          <VideoOff className="size-8" />
          <span className="text-sm">Camera off</span>
        </div>
      ) : (
        <Avatar className="size-20">
          <AvatarFallback className="text-xl">
            {initials(user.username)}
          </AvatarFallback>
        </Avatar>
      )}

      {/* Name plate */}
      <div className="absolute bottom-2 left-2 flex items-center gap-1.5 rounded-md bg-background/80 px-2 py-1 text-xs font-medium backdrop-blur">
        {muted ? (
          <MicOff className="size-3.5 text-destructive" />
        ) : (
          <Mic className="size-3.5" />
        )}
        <span>
          {user.username}
          {isYou && " (you)"}
        </span>
      </div>

      {/* Mock indicator so nobody mistakes this for a live stream. */}
      <span className="absolute top-2 right-2 rounded-md bg-background/80 px-2 py-0.5 text-[10px] tracking-wide text-muted-foreground uppercase backdrop-blur">
        <VideoIcon className="mr-1 inline size-3" />
        mock
      </span>
    </div>
  );
}
