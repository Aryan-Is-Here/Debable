"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useAuth } from "@clerk/nextjs";

import type { ChatMessage } from "@/lib/types";
import {
  chatSocketUrl,
  getMessages,
  toChatMessage,
  type ClientFrame,
  type ServerFrame,
  type WireMessage,
} from "@/services/chat";

export type ChatStatus =
  | "connecting"
  | "connected"
  | "reconnecting"
  /** The server refused this connection and retrying would be refused identically. */
  | "refused";

export interface DebateChat {
  messages: ChatMessage[];
  status: ChatStatus;
  /** The last refusal from the server, or null. Cleared by a successful send. */
  error: string | null;
  send: (content: string) => void;
  /** Development-only readout; see the note on instrumentation below. */
  debug: string;
}

/** Backoff between reconnection attempts, capped so it never gives up entirely. */
const BASE_RETRY_MS = 1000;
const MAX_RETRY_MS = 15000;

/**
 * Application close codes are 4400–4499 here (see `backend/app/websocket/protocol.py`).
 * They mean the server considered and refused the connection — a wrong room, an outsider,
 * a bad token — so reconnecting would be refused identically. Everything else (a dropped
 * network, a restarted backend) is worth retrying.
 */
function isRefusal(code: number): boolean {
  return code >= 4400 && code < 4500;
}

function byTimeThenId(a: WireMessage, b: WireMessage): number {
  if (a.createdAt !== b.createdAt) return a.createdAt < b.createdAt ? -1 : 1;
  return a.id < b.id ? -1 : 1;
}

/**
 * Live chat for one debate room.
 *
 * Opens the socket, authenticates with a first frame, and on `ready` loads history over
 * REST while buffering anything that arrives in the meantime. Messages are reconciled **by
 * id**, never by position, so a reconnect cannot duplicate the conversation.
 *
 * Two Phase 4 lessons are load-bearing here:
 *
 * 1. Clerk's `getToken` identity changes as the session settles, and React runs an effect's
 *    cleanup when dependencies change — not only on unmount. An effect depending on it
 *    would tear down and rebuild the socket underneath someone mid-sentence. It is mirrored
 *    into a ref instead, and the socket effect depends on `roomId` alone.
 * 2. History is loaded regardless of the socket's state. A read must never be gated on a
 *    write path succeeding.
 */
export function useDebateChat(roomId: string): DebateChat {
  const { getToken } = useAuth();
  const getTokenRef = useRef(getToken);

  const [wireMessages, setWireMessages] = useState<WireMessage[]>([]);
  const [status, setStatus] = useState<ChatStatus>("connecting");
  const [error, setError] = useState<string | null>(null);
  const [youId, setYouId] = useState<string | null>(null);
  const [lastEventAt, setLastEventAt] = useState<number | null>(null);

  const socketRef = useRef<WebSocket | null>(null);

  // Refreshed in an effect rather than during render: writing a ref while rendering is a
  // side effect, and the lint rules here catch it.
  useEffect(() => {
    getTokenRef.current = getToken;
  }, [getToken]);

  useEffect(() => {
    let cancelled = false;
    let socket: WebSocket | null = null;
    let retryTimer: ReturnType<typeof setTimeout> | undefined;
    let attempt = 0;

    // True once this connection's history has been merged; until then live frames are
    // buffered rather than dropped, so nothing sent during the fetch goes missing.
    let historyLoaded = false;
    let buffered: WireMessage[] = [];

    function merge(incoming: WireMessage[]) {
      if (incoming.length === 0) return;
      setWireMessages((previous) => {
        const byId = new Map(previous.map((message) => [message.id, message]));
        let added = false;
        for (const message of incoming) {
          if (byId.has(message.id)) continue;
          byId.set(message.id, message);
          added = true;
        }
        // Returning the same array when nothing is new keeps a reconnect from re-rendering
        // the whole transcript.
        if (!added) return previous;
        return [...byId.values()].sort(byTimeThenId);
      });
      setLastEventAt(Date.now());
    }

    async function loadHistory() {
      try {
        const token = await getTokenRef.current();
        const history = await getMessages(roomId, token);
        if (cancelled) return;
        historyLoaded = true;
        merge([...history, ...buffered]);
        buffered = [];
      } catch {
        // Leave `historyLoaded` false so the next `ready` tries again; live messages keep
        // buffering meanwhile rather than rendering a transcript with a hole in it.
      }
    }

    function scheduleRetry() {
      if (cancelled) return;
      setStatus("reconnecting");
      const delay = Math.min(BASE_RETRY_MS * 2 ** attempt, MAX_RETRY_MS);
      attempt += 1;
      retryTimer = setTimeout(() => void open(), delay);
    }

    function handleFrame(frame: ServerFrame) {
      if (frame.type === "ready") {
        attempt = 0;
        historyLoaded = false;
        buffered = [];
        setYouId(frame.userId);
        setStatus("connected");
        setError(null);
        setLastEventAt(Date.now());
        void loadHistory();
        return;
      }
      if (frame.type === "message") {
        if (historyLoaded) merge([frame.message]);
        else buffered.push(frame.message);
        setLastEventAt(Date.now());
        return;
      }
      setError(frame.message);
      setLastEventAt(Date.now());
    }

    async function open() {
      if (cancelled) return;

      let token: string | null = null;
      try {
        token = await getTokenRef.current();
      } catch {
        token = null;
      }
      if (cancelled) return;
      if (!token) {
        scheduleRetry();
        return;
      }

      const ws = new WebSocket(chatSocketUrl(roomId));
      socket = ws;
      socketRef.current = ws;

      ws.onopen = () => {
        const frame: ClientFrame = { type: "auth", token };
        ws.send(JSON.stringify(frame));
      };

      ws.onmessage = (event) => {
        let frame: ServerFrame;
        try {
          frame = JSON.parse(event.data as string) as ServerFrame;
        } catch {
          return;
        }
        handleFrame(frame);
      };

      ws.onclose = (event) => {
        if (socketRef.current === ws) socketRef.current = null;
        if (cancelled) return;
        if (isRefusal(event.code)) {
          setStatus("refused");
          setError(event.reason || "The server refused this chat connection.");
          return;
        }
        scheduleRetry();
      };

      // `onclose` always follows `onerror`, so retrying is handled in one place.
      ws.onerror = () => {};
    }

    void open();

    return () => {
      cancelled = true;
      if (retryTimer !== undefined) clearTimeout(retryTimer);
      socketRef.current = null;
      socket?.close();
    };
  }, [roomId]);

  const send = useCallback((content: string) => {
    const trimmed = content.trim();
    if (!trimmed) return;

    const ws = socketRef.current;
    if (!ws || ws.readyState !== WebSocket.OPEN) {
      setError("Not connected — your message was not sent.");
      return;
    }

    const frame: ClientFrame = { type: "message", content: trimmed };
    ws.send(JSON.stringify(frame));
    setError(null);
  }, []);

  const messages = useMemo(
    () => wireMessages.map((message) => toChatMessage(message, youId)),
    [wireMessages, youId],
  );

  /**
   * A silent chat panel looks identical whether the socket is connected, reconnecting, or
   * dead. That ambiguity cost three rounds of debugging in Phase 4, and the waiting room
   * still carries the readout that ended it — this is the same idea for the socket.
   */
  const debug = `ws=${status} · msgs=${messages.length} · you=${youId ? "yes" : "no"} · last=${
    lastEventAt ? new Date(lastEventAt).toLocaleTimeString() : "never"
  }`;

  return { messages, status, error, send, debug };
}
