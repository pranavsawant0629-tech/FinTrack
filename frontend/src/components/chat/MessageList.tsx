import React, { useEffect, useRef } from "react";
import type { ChatMessage } from "../../hooks/useChat";
import type { TutorSectionId } from "../../api/types";
import { MessageItem } from "./MessageItem";
import { LoadingBubble } from "./LoadingBubble";
import { TutorLanding } from "./TutorLanding";
import { ShieldCheck, Zap, Scale, Sparkles } from "lucide-react";

interface MessageListProps {
  messages: ChatMessage[];
  isLoading: boolean;
  elapsedSeconds: number;
  error: string | null;
  activeSection?: TutorSectionId;
  displayName?: string;
  userId?: string;
  onSelectPrompt: (prompt: string) => void;
  onContinueLearning?: (conversationId: string) => void;
  onRetry?: (query: string) => void;
}

export const MessageList: React.FC<MessageListProps> = ({
  messages,
  isLoading,
  elapsedSeconds,
  error,
  activeSection = "general",
  displayName,
  userId,
  onSelectPrompt,
  onContinueLearning,
  onRetry,
}) => {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isLoading]);

  return (
    <div className="flex-1 overflow-y-auto px-4 sm:px-6 py-6 scroll-smooth">
      {messages.length === 0 ? (
        isLoading ? (
          <div className="flex-1 flex flex-col items-center justify-center min-h-[360px] text-center p-8 animate-in fade-in duration-200">
            <div className="w-10 h-10 rounded-full bg-surface border border-border-warm flex items-center justify-center text-marigold mb-3 shadow-xs animate-pulse">
              <Sparkles className="w-5 h-5" />
            </div>
            <h3 className="font-serif text-base font-bold text-ivory">Loading your conversation...</h3>
            <p className="text-xs text-muted-warm font-sans mt-1">Retrieving persistent learning history</p>
          </div>
        ) : (
          <div>
            <TutorLanding
              sectionId={activeSection}
              userId={userId}
              onSelectPrompt={onSelectPrompt}
              onContinueLearning={onContinueLearning}
            />

          {/* Trust Badges */}
          <div className="pt-6 pb-4 flex flex-wrap items-center justify-center gap-4 sm:gap-8 text-[11px] text-muted-warm font-sans">
            <span className="inline-flex items-center gap-1.5">
              <ShieldCheck className="w-3.5 h-3.5 text-teal" />
              <span>Grounded sources</span>
            </span>
            <span className="hidden sm:inline text-border-warm">•</span>
            <span className="inline-flex items-center gap-1.5">
              <Zap className="w-3.5 h-3.5 text-marigold" />
              <span>Educational simulations</span>
            </span>
            <span className="hidden sm:inline text-border-warm">•</span>
            <span className="inline-flex items-center gap-1.5">
              <Scale className="w-3.5 h-3.5 text-terracotta" />
              <span>Clear financial explanations</span>
            </span>
          </div>
        </div>
        )
      ) : (
        <div className="space-y-4 max-w-4xl mx-auto">
          {messages.map((msg, idx) => {
            const precedingUser = messages
              .slice(0, idx)
              .reverse()
              .find((m) => m.role === "user");

            return (
              <MessageItem
                key={msg.id}
                message={msg}
                displayName={displayName}
                userId={userId}
                isLatest={idx === messages.length - 1}
                onSelectPrompt={onSelectPrompt}
                onRetry={
                  onRetry && precedingUser
                    ? () => onRetry(precedingUser.content)
                    : undefined
                }
              />
            );
          })}

          {isLoading && <LoadingBubble elapsedSeconds={elapsedSeconds} />}

          {error && (
            <div className="max-w-3xl mx-auto my-3 p-3.5 rounded-xl bg-terracotta/15 border border-terracotta/40 text-ivory text-xs flex items-center justify-between">
              <span className="font-sans">{error}</span>
            </div>
          )}

          <div ref={bottomRef} />
        </div>
      )}
    </div>
  );
};
