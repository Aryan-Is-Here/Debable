"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useAuth } from "@clerk/nextjs";
import { Loader2, PhoneOff } from "lucide-react";

import type { ChatMessage, DebateRoom } from "@/lib/types";
import { mockFactCheck } from "@/lib/mock/debate";
import { endRoom, matchKeys } from "@/services/match";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { ChatPanel } from "@/components/chat-panel";
import { DebateVideo } from "@/components/debate-video";

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
  const queryClient = useQueryClient();
  const { getToken } = useAuth();
  const [messages, setMessages] = useState<ChatMessage[]>(initialMessages);

  const { mutate: endDebate, isPending: isEnding } = useMutation({
    mutationFn: async () => endRoom(room.id, await getToken()),
    // Navigate either way: if the room was already closed by the opponent, the debate is
    // over regardless and stranding the user here would be worse than a silent failure.
    onSettled: () => {
      queryClient.removeQueries({ queryKey: matchKeys.state });
      router.push(`/debate/${room.id}/results`);
    },
  });

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
          disabled={isEnding}
          onClick={() => endDebate()}
        >
          {isEnding ? (
            <Loader2 className="size-4 animate-spin" />
          ) : (
            <PhoneOff className="size-4" />
          )}
          End debate
        </Button>
      </header>

      {/* Video + chat */}
      <div className="grid min-h-0 flex-1 gap-4 lg:grid-cols-[2fr_1fr]">
        <DebateVideo room={room} onFactCheck={handleFactCheck} />

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
