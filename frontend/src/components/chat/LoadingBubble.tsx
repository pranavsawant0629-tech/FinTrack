import React from "react";
import { Loader2, Sparkles } from "lucide-react";

interface LoadingBubbleProps {
  elapsedSeconds: number;
}

export const LoadingBubble: React.FC<LoadingBubbleProps> = ({ elapsedSeconds }) => {
  return (
    <div className="flex items-start gap-3 py-4 max-w-4xl mx-auto w-full animate-in fade-in duration-200">
      <div className="w-8 h-8 rounded-full bg-surface border border-border-warm flex items-center justify-center shrink-0 text-marigold shadow-xs">
        <Sparkles className="w-4 h-4" />
      </div>

      <div className="bg-surface border border-border-warm rounded-2xl rounded-tl-sm px-4 py-3 shadow-xs max-w-xl">
        <div className="flex items-center gap-2.5 text-xs text-ivory">
          <Loader2 className="w-3.5 h-3.5 animate-spin text-marigold" />
          <span className="font-medium font-serif text-sm">Finova is thinking...</span>
          <span className="font-mono text-muted-warm bg-elevated px-2 py-0.5 rounded text-[11px] border border-border-warm">
            {elapsedSeconds.toFixed(1)}s
          </span>
        </div>
      </div>
    </div>
  );
};
