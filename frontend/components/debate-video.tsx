"use client";

import { useCallback, useEffect, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { useAuth } from "@clerk/nextjs";
import {
  LiveKitRoom,
  RoomAudioRenderer,
  VideoTrack,
  useConnectionState,
  useIsMuted,
  useLocalParticipant,
  useRemoteParticipants,
  useTracks,
} from "@livekit/components-react";
import { ConnectionState, Track, type Participant } from "livekit-client";
import {
  AlertCircle,
  Loader2,
  Mic,
  MicOff,
  Video as VideoIcon,
  VideoOff,
} from "lucide-react";

import type { DebateRoom, UserSummary } from "@/lib/types";
import { cn, initials } from "@/lib/utils";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { Button } from "@/components/ui/button";
import { FactCheckDialog } from "@/components/fact-check-dialog";
import { ApiError } from "@/services/api-client";
import { getRoomToken, videoKeys } from "@/services/video";

interface DebateVideoProps {
  room: DebateRoom;
  onFactCheck: (claim: string) => Promise<void>;
}

/**
 * Live video for a debate.
 *
 * Fetches a room-scoped token, connects to LiveKit, and renders both participants. The
 * media failure states — permission denied, no device, connection lost — are handled
 * explicitly: a black rectangle tells the user nothing, and these are the common cases when
 * strangers meet.
 */
export function DebateVideo({ room, onFactCheck }: DebateVideoProps) {
  const { getToken } = useAuth();

  const {
    data: credentials,
    isPending,
    isError,
    error,
    refetch,
  } = useQuery({
    queryKey: videoKeys.token(room.id),
    queryFn: async () => getRoomToken(room.id, await getToken()),
    // A token is a credential, not a cacheable read; refetching one on a window focus would
    // reconnect the call for no reason.
    staleTime: Infinity,
    refetchOnWindowFocus: false,
    retry: 1,
  });

  if (isPending) {
    return (
      <VideoFrame>
        <div className="flex flex-col items-center gap-3 text-muted-foreground">
          <Loader2 className="size-6 animate-spin" />
          <p className="text-sm">Connecting video…</p>
        </div>
      </VideoFrame>
    );
  }

  if (isError || !credentials) {
    const unavailable = error instanceof ApiError && error.status === 503;
    return (
      <VideoFrame>
        <div className="flex max-w-sm flex-col items-center gap-3 text-center">
          <AlertCircle className="size-7 text-destructive" />
          <p className="font-medium">
            {unavailable ? "Video isn't set up on this server" : "Couldn't start video"}
          </p>
          <p className="text-sm text-muted-foreground">
            {error instanceof Error ? error.message : "Something went wrong."}
          </p>
          <Button variant="outline" size="sm" onClick={() => refetch()}>
            Try again
          </Button>
        </div>
      </VideoFrame>
    );
  }

  return (
    <LiveKitRoom
      serverUrl={credentials.url}
      token={credentials.token}
      connect
      // Ask for both on join; DebateStage surfaces it clearly if either is refused.
      video
      audio
    >
      <RoomAudioRenderer />
      <DebateStage room={room} onFactCheck={onFactCheck} />
    </LiveKitRoom>
  );
}

/** The tiles and controls, rendered inside LiveKit's room context. */
function DebateStage({ room, onFactCheck }: DebateVideoProps) {
  const connection = useConnectionState();
  const { localParticipant } = useLocalParticipant();
  const [mediaError, setMediaError] = useState<string | null>(null);

  const tracks = useTracks([Track.Source.Camera], { onlySubscribed: false });
  const localTrack = tracks.find((t) => t.participant.isLocal);
  const remoteTrack = tracks.find((t) => !t.participant.isLocal);

  // Presence comes from the participant list, never from whether a camera track exists.
  // Turning a camera off unpublishes its track, so "no track" and "not here" look identical
  // from `useTracks` alone — which made a debater with their camera off appear, to the other
  // side only, as though they had never joined. A debate is 1v1, so there is at most one.
  const [opponent] = useRemoteParticipants();

  const micOn = localParticipant.isMicrophoneEnabled;
  const cameraOn = localParticipant.isCameraEnabled;

  // Report a device that was refused or is missing, rather than showing an empty frame.
  useEffect(() => {
    const onFailure = (error: unknown) => {
      const name = error instanceof Error ? error.name : "";
      setMediaError(
        name === "NotAllowedError"
          ? "Camera and microphone are blocked. Allow them in your browser's address bar, then rejoin."
          : name === "NotFoundError"
            ? "No camera or microphone found on this device."
            : "Couldn't start your camera or microphone.",
      );
    };
    localParticipant.on("mediaDevicesError", onFailure);
    return () => {
      localParticipant.off("mediaDevicesError", onFailure);
    };
  }, [localParticipant]);

  const toggle = useCallback(
    async (kind: "mic" | "camera") => {
      try {
        if (kind === "mic") {
          await localParticipant.setMicrophoneEnabled(!micOn);
        } else {
          await localParticipant.setCameraEnabled(!cameraOn);
        }
        setMediaError(null);
      } catch {
        setMediaError("Couldn't change your camera or microphone.");
      }
    },
    [localParticipant, micOn, cameraOn],
  );

  const reconnecting =
    connection === ConnectionState.Reconnecting || connection === ConnectionState.Connecting;

  return (
    <div className="flex flex-col gap-4">
      {reconnecting && (
        <p className="flex items-center justify-center gap-2 rounded-lg border border-border bg-muted/40 py-2 text-sm text-muted-foreground">
          <Loader2 className="size-4 animate-spin" />
          {connection === ConnectionState.Reconnecting ? "Reconnecting…" : "Connecting…"}
        </p>
      )}
      {connection === ConnectionState.Disconnected && (
        <p className="flex items-center justify-center gap-2 rounded-lg border border-destructive/50 py-2 text-sm text-destructive">
          <AlertCircle className="size-4" />
          Disconnected from the call. Reload to rejoin.
        </p>
      )}
      {mediaError && (
        <p className="flex items-center justify-center gap-2 rounded-lg border border-destructive/50 px-3 py-2 text-center text-sm text-destructive">
          <AlertCircle className="size-4 shrink-0" />
          {mediaError}
        </p>
      )}

      <div className="grid gap-4 sm:grid-cols-2">
        {opponent ? (
          <RemoteParticipantFrame
            user={room.opponent}
            participant={opponent}
            track={remoteTrack}
          />
        ) : (
          <ParticipantFrame user={room.opponent} waitingLabel="Waiting for them to join…" />
        )}
        <ParticipantFrame user={room.you} track={localTrack} isYou muted={!micOn} />
      </div>

      <div className="flex flex-wrap items-center justify-center gap-2">
        <Button
          variant={micOn ? "outline" : "destructive"}
          size="icon"
          onClick={() => void toggle("mic")}
          aria-label={micOn ? "Mute microphone" : "Unmute microphone"}
          aria-pressed={!micOn}
        >
          {micOn ? <Mic className="size-4" /> : <MicOff className="size-4" />}
        </Button>
        <Button
          variant={cameraOn ? "outline" : "destructive"}
          size="icon"
          onClick={() => void toggle("camera")}
          aria-label={cameraOn ? "Turn camera off" : "Turn camera on"}
          aria-pressed={!cameraOn}
        >
          {cameraOn ? <VideoIcon className="size-4" /> : <VideoOff className="size-4" />}
        </Button>
        <FactCheckDialog onSubmitClaim={onFactCheck} />
      </div>
    </div>
  );
}

/**
 * The opponent's frame, once they are actually in the room.
 *
 * Split out because the mute indicator needs a hook, and hooks cannot be called
 * conditionally — there is no participant to ask about until someone has joined. Rendering
 * a different component in that case is fine; calling `useIsMuted` conditionally is not.
 */
function RemoteParticipantFrame({
  user,
  participant,
  track,
}: {
  user: UserSummary;
  participant: Participant;
  track?: ReturnType<typeof useTracks>[number];
}) {
  // Their real microphone state. Without this the opponent's tile always showed an
  // unmuted mic, however loudly the icon on their own screen disagreed.
  const muted = useIsMuted({ participant, source: Track.Source.Microphone });

  return <ParticipantFrame user={user} track={track} muted={muted} />;
}

/** One participant's frame: their video when publishing, their avatar when not. */
function ParticipantFrame({
  user,
  track,
  isYou = false,
  muted = false,
  waitingLabel,
}: {
  user: UserSummary;
  track?: ReturnType<typeof useTracks>[number];
  isYou?: boolean;
  muted?: boolean;
  waitingLabel?: string;
}) {
  const hasVideo = track?.publication && !track.publication.isMuted;

  return (
    <div className="relative aspect-video overflow-hidden rounded-lg border border-border bg-muted/40">
      {hasVideo ? (
        <VideoTrack
          trackRef={track}
          className={cn("size-full object-cover", isYou && "-scale-x-100")}
        />
      ) : (
        <div className="flex size-full flex-col items-center justify-center gap-2">
          <Avatar className="size-16">
            {user.avatarUrl && <AvatarImage src={user.avatarUrl} alt="" />}
            <AvatarFallback>{initials(user.username)}</AvatarFallback>
          </Avatar>
          {waitingLabel && <p className="text-xs text-muted-foreground">{waitingLabel}</p>}
        </div>
      )}

      <div className="absolute bottom-2 left-2 flex items-center gap-1.5 rounded-md bg-background/80 px-2 py-1 text-xs backdrop-blur">
        {muted ? <MicOff className="size-3 text-destructive" /> : <Mic className="size-3" />}
        <span>
          {user.username}
          {isYou && " (you)"}
        </span>
      </div>
    </div>
  );
}

function VideoFrame({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex aspect-video w-full items-center justify-center rounded-lg border border-border bg-muted/40">
      {children}
    </div>
  );
}
