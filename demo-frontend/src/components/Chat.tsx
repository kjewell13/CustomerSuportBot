// demo component for testing purposes

import { useEffect, useRef, useState } from "react";

type Msg = { id: string; role: "user" | "assistant"; text: string };

const uid = () => Math.random().toString(36).slice(2) + Date.now().toString(36);

export default function Chat() {
  const [status, setStatus] = useState<"connecting" | "connected" | "disconnected">("connecting");
  const [messages, setMessages] = useState<Msg[]>([
    { id: uid(), role: "assistant", text: "Hi! Ask me about an order, a refund, or a policy question." },
  ]);
  const [input, setInput] = useState("");
  const wsRef = useRef<WebSocket | null>(null);
  const bottomRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    const ws = new WebSocket("/ws"); // <-- proxied by Vite
    wsRef.current = ws;

    ws.onopen = () => setStatus("connected");
    ws.onclose = () => setStatus("disconnected");
    ws.onerror = () => setStatus("disconnected");

    ws.onmessage = (e) => {
      setMessages((prev) => [...prev, { id: uid(), role: "assistant", text: String(e.data ?? "") }]);
    };

    return () => ws.close();
  }, []);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages.length]);

  const send = () => {
    const text = input.trim();
    if (!text) return;

    setMessages((prev) => [...prev, { id: uid(), role: "user", text }]);
    setInput("");

    const ws = wsRef.current;
    if (!ws || ws.readyState !== WebSocket.OPEN) {
      setMessages((prev) => [...prev, { id: uid(), role: "assistant", text: "Not connected yet—try again in a second." }]);
      return;
    }
    ws.send(text);
  };

  return (
    <div className="min-h-screen bg-zinc-950 text-zinc-100">
      <div className="mx-auto flex min-h-screen max-w-3xl flex-col p-4">
        <div className="mb-4 rounded-2xl border border-zinc-800 bg-zinc-900/60 p-4">
          <div className="text-lg font-semibold">Demo Support Chat</div>
          <div className="text-sm text-zinc-400">
            {status === "connected" ? "Connected" : status === "connecting" ? "Connecting…" : "Disconnected"}
          </div>
        </div>

        <div className="flex-1 overflow-hidden rounded-2xl border border-zinc-800 bg-zinc-900/40">
          <div className="h-full overflow-y-auto p-4">
            <div className="space-y-3">
              {messages.map((m) => (
                <div key={m.id} className={`flex ${m.role === "user" ? "justify-end" : "justify-start"}`}>
                  <div className={`max-w-[85%] whitespace-pre-wrap rounded-2xl px-4 py-3 text-sm ${
                    m.role === "user" ? "bg-blue-600 text-white" : "bg-zinc-800 text-zinc-100"
                  }`}>
                    {m.text}
                  </div>
                </div>
              ))}
              <div ref={bottomRef} />
            </div>
          </div>
        </div>

        <div className="mt-4 flex gap-3 rounded-2xl border border-zinc-800 bg-zinc-900/60 p-3">
          <input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter") send();
            }}
            placeholder={status === "connected" ? "Type a message…" : "Connecting…"}
            disabled={status !== "connected"}
            className="flex-1 rounded-xl border border-zinc-800 bg-zinc-950 px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-blue-600/60 disabled:opacity-60"
          />
          <button
            onClick={send}
            disabled={status !== "connected" || !input.trim()}
            className="rounded-xl bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-500 disabled:opacity-50"
          >
            Send
          </button>
        </div>
      </div>
    </div>
  );
}