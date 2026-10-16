import { useRef, useState } from "react";
import { apiClient } from "../api/client";
import type { OrchestratorResponse } from "../api/types";

export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  timestamp: string;
  status?: "complete" | "failed";
  response?: OrchestratorResponse;
  elapsedSeconds?: number;
  error?: string;
}

export function useChat(userId: string, initialDomain: string = "general") {
  const [activeConversationId, setActiveConversationId] = useState<string | null>(null);
  const [activeDomain, setActiveDomain] = useState<string>(initialDomain);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [activeElapsed, setActiveElapsed] = useState<number>(0);
  const [error, setError] = useState<string | null>(null);

  const timerRef = useRef<number | null>(null);

  const formatTimestamp = (isoOrTime?: string) => {
    if (!isoOrTime) return new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
    try {
      const d = new Date(isoOrTime);
      if (isNaN(d.getTime())) return isoOrTime;
      return d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
    } catch {
      return isoOrTime;
    }
  };

  const sendMessage = async (queryText: string, domainOverride?: string) => {
    const trimmed = queryText.trim();
    if (!trimmed || isLoading) return;

    setError(null);
    const tempUserMsgId = `temp_${Date.now()}_user`;
    const userMessage: ChatMessage = {
      id: tempUserMsgId,
      role: "user",
      content: trimmed,
      timestamp: formatTimestamp(),
      status: "complete",
    };

    // Optimistically show user message
    setMessages((prev) => [...prev, userMessage]);
    setIsLoading(true);
    setActiveElapsed(0);

    const startTime = performance.now();
    timerRef.current = window.setInterval(() => {
      const sec = (performance.now() - startTime) / 1000;
      setActiveElapsed(parseFloat(sec.toFixed(1)));
    }, 100);

    try {
      // Call persistent transactional send turn, passing activeDomain
      const targetDomain = (domainOverride || activeDomain || "general").toLowerCase();
      const turnRes = await apiClient.sendTurn(userId, trimmed, activeConversationId, targetDomain);
      const totalElapsed = (performance.now() - startTime) / 1000;

      // Ensure activeConversationId is updated if this was turn 1
      if (!activeConversationId && turnRes.conversation_id) {
        setActiveConversationId(turnRes.conversation_id);
      }

      const userMsg: ChatMessage = {
        id: turnRes.user_message.message_id,
        role: "user",
        content: turnRes.user_message.content,
        timestamp: formatTimestamp(turnRes.user_message.timestamp),
        status: turnRes.user_message.status,
      };

      const isFailed = turnRes.assistant_message.status === "failed";
      const assistantMsg: ChatMessage = {
        id: turnRes.assistant_message.message_id,
        role: "assistant",
        content: turnRes.assistant_message.content,
        timestamp: formatTimestamp(turnRes.assistant_message.timestamp),
        status: turnRes.assistant_message.status,
        response: turnRes.orchestrator_response || (turnRes.assistant_message.metadata as OrchestratorResponse | undefined),
        elapsedSeconds: parseFloat(totalElapsed.toFixed(2)),
        error: isFailed ? (turnRes.assistant_message.metadata?.error || "Inquiry turn encountered an issue.") : undefined,
      };

      if (isFailed) {
        setError(assistantMsg.error || "Turn could not be completed. Message saved.");
      }

      // Replace the optimistic user message with the real persisted pair
      setMessages((prev) => {
        const withoutTemp = prev.filter((m) => m.id !== tempUserMsgId);
        return [...withoutTemp, userMsg, assistantMsg];
      });
    } catch (err: any) {
      const totalElapsed = (performance.now() - startTime) / 1000;
      const errMsg = err?.message || "Failed to communicate with Finova AI backend.";
      setError(errMsg);

      const errorMsg: ChatMessage = {
        id: `err_${Date.now()}_assistant`,
        role: "assistant",
        content: "I encountered an error contacting the Finova AI engine. Your inquiry was saved locally.",
        timestamp: formatTimestamp(),
        status: "failed",
        error: errMsg,
        elapsedSeconds: parseFloat(totalElapsed.toFixed(2)),
      };

      setMessages((prev) => [...prev, errorMsg]);
    } finally {
      if (timerRef.current) {
        clearInterval(timerRef.current);
        timerRef.current = null;
      }
      setIsLoading(false);
    }
  };

  const loadConversation = async (conversationId: string): Promise<string | null> => {
    setIsLoading(true);
    setError(null);
    try {
      const detail = await apiClient.getConversation(conversationId, userId);
      setActiveConversationId(detail.conversation.conversation_id);

      // Invariant: Stored conversation domain is authoritative!
      // Reopening a conversation must automatically switch active domain to stored domain
      const storedDomain = (detail.conversation.domain || "general").toLowerCase();
      setActiveDomain(storedDomain);

      const loadedMessages: ChatMessage[] = (detail.messages || []).map((m) => {
        const isAssistant = m.role === "assistant";
        const meta = m.metadata;

        let reconstructedResponse: OrchestratorResponse | undefined = undefined;
        if (isAssistant && m.status === "complete" && meta) {
          reconstructedResponse = {
            query: "",
            answer: m.content,
            grounding_status: meta.grounding_status || "ungrounded",
            citations: meta.citations || [],
            market_data: meta.market_data,
            market_data_list: meta.market_data_list || (meta.market_data ? [meta.market_data] : []),
            crypto_data: meta.crypto_data,
            derivatives_data: meta.derivatives_data,
            portfolio_data: meta.portfolio_data,
            news_data: meta.news_data,
            quiz_data: meta.quiz_data,
            onboarding_data: meta.onboarding_data,
            grounding_sources: meta.grounding_sources || [],
            domain_detected: meta.domain_detected || "GENERAL",
            sub_tasks: meta.sub_tasks || [],
            agent_name: meta.agent_name || "Finova AI",
            disclaimer: "Finova AI is an educational financial intelligence platform, not a SEBI-registered advisor.",
            model_used: meta.model_used || "",
            latency_ms: meta.latency_ms || 0,
            topic: meta.topic || null,
            related_concepts: meta.related_concepts || [],
            suggested_next: meta.suggested_next || [],
          };
        }

        return {
          id: m.message_id,
          role: m.role,
          content: m.content,
          timestamp: formatTimestamp(m.timestamp),
          status: m.status,
          response: reconstructedResponse,
          error: m.status === "failed" ? (meta?.error || "Inquiry encountered an issue.") : undefined,
        };
      });

      setMessages(loadedMessages);
      return storedDomain;
    } catch (err: any) {
      setError(err?.message || "Failed to load conversation history.");
      return null;
    } finally {
      setIsLoading(false);
    }
  };

  const newConversation = (targetDomain?: string) => {
    setActiveConversationId(null);
    setMessages([]);
    setError(null);
    if (targetDomain) {
      setActiveDomain(targetDomain.toLowerCase());
    }
  };

  return {
    activeConversationId,
    activeDomain,
    setActiveDomain,
    messages,
    isLoading,
    activeElapsed,
    error,
    sendMessage,
    loadConversation,
    newConversation,
    clearMessages: newConversation,
  };
}
