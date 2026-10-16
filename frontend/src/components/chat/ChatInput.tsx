import React, { useState, useRef, useEffect } from "react";
import { ArrowUp, Loader2 } from "lucide-react";

interface ChatInputProps {
  onSendMessage: (query: string) => void;
  isLoading: boolean;
}

export const ChatInput: React.FC<ChatInputProps> = ({ onSendMessage, isLoading }) => {
  const [query, setQuery] = useState("");
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
      textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 160)}px`;
    }
  }, [query]);

  const handleSubmit = (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    if (!query.trim() || isLoading) return;
    onSendMessage(query.trim());
    setQuery("");
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  return (
    <div className="border-t border-border-warm/60 bg-espresso/95 px-4 py-3 sm:py-4">
      <div className="max-w-4xl mx-auto">
        <form
          onSubmit={handleSubmit}
          className="relative flex items-end gap-2 bg-surface border border-border-warm rounded-2xl p-2 sm:p-2.5 shadow-sm focus-within:border-marigold/60 focus-within:ring-1 focus-within:ring-marigold/20 transition-all duration-150"
        >
          <textarea
            ref={textareaRef}
            rows={1}
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={handleKeyDown}
            disabled={isLoading}
            placeholder="Ask Finova about markets, options, SIPs, or concepts..."
            className="w-full bg-transparent text-ivory placeholder-muted-warm/60 text-xs sm:text-sm px-3 py-1.5 focus:outline-none resize-none max-h-40 leading-relaxed font-sans"
          />

            <button
              type="submit"
              disabled={!query.trim() || isLoading}
              className={`w-8 h-8 rounded-xl transition-all duration-150 shrink-0 flex items-center justify-center font-bold ${
                query.trim() && !isLoading
                  ? "bg-marigold text-espresso hover:bg-marigold-hover shadow-xs cursor-pointer active:scale-95"
                  : "bg-elevated border border-border-warm text-muted-warm/40 cursor-not-allowed"
              }`}
              title="Send inquiry (Enter)"
            >
              {isLoading ? (
                <Loader2 className="w-4 h-4 animate-spin text-espresso" />
              ) : (
                <ArrowUp className="w-4 h-4 stroke-[2.5]" />
              )}
            </button>
        </form>

        <p className="text-[10px] sm:text-[11px] text-muted-warm/75 text-center mt-2.5 font-sans tracking-wide">
          Finova is an educational companion, not investment advice.
        </p>
      </div>
    </div>
  );
};
