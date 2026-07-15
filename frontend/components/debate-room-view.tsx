"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Mic, MicOff, PhoneOff, Video as VideoIcon, VideoOff } from "lucide-react";

import type { ChatMessage, DebateRoom } from "@/lib/types";
import { mockFactCheck } from "@/lib/mock/debate";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { VideoTile } from "@/components/video-tile";
import { ChatPanel } from "@/components/chat-panel";
import { FactCheckDialog } from "@/components/fact-check-dialog";

interface DebateRoomViewProps {
  room: DebateRoom;
  initialMessages: ChatMessage[];
}

/** Simulated AI latency for the mock fact-check (ms). */
const FACT_CHECK_DELAY_MS = 1200;

/**
 * Debate Room orchestrator: owns chat + control state and wires the
 * fact-check flow. Video, chat transport, and the AI service are all mocked
 * in Phase 1 (they arrive in Phases 5–7).
 */
export function DebateRoomView({ room, initialMessages }: DebateRoomViewProps) {
  const router = useRouter();
  const [messages, setMessages] = useState<ChatMessage[]>(initialMessages);
  const [muted, setMuted] = useState(false);
  const [cameraOff, setCameraOff] = useState(false);

  function appendMessage(message: ChatMessage) {
    setMessages((prev) => [...prev, message]);
  }

  function handleSend(content: string) {
    appendMessage({
      id: `m_${Date.now()}`,
      author: "you",
      content,
      createdAt: new Date().toISOString(),
    });
  }

  async function handleFactCheck(claim: string) {
    // Mock the AI service round-trip; result lands in chat as a system message.
    await new Promise((resolve) => setTimeout(resolve, FACT_CHECK_DELAY_MS));
    appendMessage({
      id: `m_fc_${Date.now()}`,
      author: "system",
      content: "",
      createdAt: new Date().toISOString(),
      factCheck: mockFactCheck(claim),
    });
  }

  return (
    <div className="mx-auto flex min-h-[calc(100dvh-4rem)] w-full max-w-6xl flex-col gap-4 px-4 py-6 sm:px-6">
      {/* Room header */}
      <header className="flex flex-wrap items-center justify-between gap-2">
        <div className="flex min-w-0 items-center gap-2">
          <Badge variant="outline">{room.topic.category}</Badge>
          <h1 className="truncate font-medium">{room.topic.title}</h1>
        </div>
        <Button
          variant="destructive"
          size="sm"
          onClick={() => router.push(`/debate/${room.id}/results`)}
        >
          <PhoneOff className="size-4" />
          End debate
        </Button>
      </header>

      {/* Video + chat */}
      <div className="grid min-h-0 flex-1 gap-4 lg:grid-cols-[2fr_1fr]">
        <div className="flex flex-col gap-4">
          <div className="grid gap-4 sm:grid-cols-2">
            <VideoTile user={room.opponent} muted={false} />
            <VideoTile
              user={room.you}
              isYou
              muted={muted}
              cameraOff={cameraOff}
            />
          </div>

          {/* Controls */}
          <div className="flex flex-wrap items-center justify-center gap-2">
            <Button
              variant={muted ? "destructive" : "outline"}
              size="icon"
              onClick={() => setMuted((m) => !m)}
              aria-label={muted ? "Unmute microphone" : "Mute microphone"}
              aria-pressed={muted}
            >
              {muted ? <MicOff className="size-4" /> : <Mic className="size-4" />}
            </Button>
            <Button
              variant={cameraOff ? "destructive" : "outline"}
              size="icon"
              onClick={() => setCameraOff((c) => !c)}
              aria-label={cameraOff ? "Turn camera on" : "Turn camera off"}
              aria-pressed={cameraOff}
            >
              {cameraOff ? (
                <VideoOff className="size-4" />
              ) : (
                <VideoIcon className="size-4" />
              )}
            </Button>
            <FactCheckDialog onSubmitClaim={handleFactCheck} />
          </div>
        </div>

        <ChatPanel
          room={room}
          messages={messages}
          onSend={handleSend}
          className="min-h-[24rem] lg:min-h-0"
        />
      </div>
    </div>
  );
}
