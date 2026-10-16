import React from "react";
import { ArrowRight, Tag } from "lucide-react";

interface RelatedConceptsProps {
  concepts: string[];
  activeTopic?: string | null;
  onSelectConcept: (prompt: string) => void;
  disabled?: boolean;
}

export const RelatedConcepts: React.FC<RelatedConceptsProps> = ({
  concepts,
  activeTopic,
  onSelectConcept,
  disabled = false,
}) => {
  if (!concepts || concepts.length === 0) return null;

  return (
    <div className="pt-2 pb-1" aria-label="Related financial concepts">
      <div className="flex items-center gap-2 mb-1.5">
        <div className="flex items-center gap-1.5 text-[11px] font-mono uppercase tracking-widest text-muted-warm/80">
          <Tag className="w-3.5 h-3.5 text-teal" />
          <span>Explore Related Concepts</span>
        </div>
        <div className="h-px flex-1 bg-border-warm/40" />
      </div>

      <div className="flex flex-wrap items-center gap-1.5 sm:gap-2">
        {concepts.map((concept, idx) => {
          const prompt = activeTopic
            ? `Explain ${concept} and how it connects to ${activeTopic}`
            : `What is ${concept} and how does it work?`;

          return (
            <button
              key={idx}
              type="button"
              disabled={disabled}
              onClick={() => onSelectConcept(prompt)}
              title={`Explore: ${prompt}`}
              className="inline-flex items-center gap-1 px-2.5 py-1 rounded-md text-xs font-mono bg-surface border border-border-warm hover:border-teal/50 hover:bg-teal/10 hover:text-teal-light text-ivory/80 transition-all duration-150 cursor-pointer select-none disabled:opacity-50 disabled:cursor-not-allowed group"
            >
              <span>{concept}</span>
              <ArrowRight className="w-3 h-3 text-muted-warm group-hover:text-teal group-hover:translate-x-0.5 transition-all opacity-70" />
            </button>
          );
        })}
      </div>
    </div>
  );
};
