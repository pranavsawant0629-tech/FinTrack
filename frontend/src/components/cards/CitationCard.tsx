import React from "react";
import { BookOpen, ExternalLink } from "lucide-react";
import type { Citation } from "../../api/types";

interface Props {
  citations: Citation[];
}

export const CitationCard: React.FC<Props> = ({ citations }) => {
  if (!citations || citations.length === 0) return null;

  return (
    <div className="mt-3 p-3.5 sm:p-4 rounded-xl bg-surface border border-border-warm text-xs shadow-xs animate-in fade-in duration-150">
      <div className="flex items-center gap-2 font-serif font-medium text-ivory mb-2.5">
        <BookOpen className="w-4 h-4 text-teal" />
        <span className="text-sm">Authoritative Regulatory & Market Sources ({citations.length})</span>
      </div>
      <div className="space-y-2">
        {citations.map((c) => (
          <div
            key={c.citation_id}
            className="p-3 rounded-lg bg-elevated border border-border-warm/60 hover:border-marigold/40 transition-colors"
          >
            <div className="flex items-start justify-between gap-2">
              <div className="flex items-center gap-2">
                <span className="inline-flex items-center justify-center w-4 h-4 rounded-full bg-teal/20 text-teal font-mono text-[10px] font-bold border border-teal/40">
                  {c.citation_id}
                </span>
                <span className="font-serif font-medium text-ivory text-xs sm:text-[13px]">{c.title || c.doc_id}</span>
              </div>
              <div className="flex items-center gap-1.5 flex-shrink-0">
                {c.source && (
                  <span className="px-2 py-0.5 rounded bg-surface border border-border-warm text-muted-warm font-mono text-[10px]">
                    {c.source}
                  </span>
                )}
                {c.authority_level && (
                  <span className="px-2 py-0.5 rounded bg-teal/20 text-teal border border-teal/40 font-mono text-[10px]">
                    {c.authority_level}
                  </span>
                )}
              </div>
            </div>

            <div className="mt-2 flex items-center justify-between text-muted-warm text-[11px] font-sans">
              <div>
                {c.page_numbers && c.page_numbers.length > 0 && (
                  <span className="font-mono">Pages: {c.page_numbers.join(", ")}</span>
                )}
                {c.similarity_score > 0 && (
                  <span className="ml-2 text-muted-warm/60 font-mono">
                    Score: {(c.similarity_score * 100).toFixed(1)}%
                  </span>
                )}
              </div>

              {c.url && (
                <a
                  href={c.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-1 text-marigold hover:text-marigold-hover hover:underline transition-colors"
                >
                  <span>View Source</span>
                  <ExternalLink className="w-3 h-3" />
                </a>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};
