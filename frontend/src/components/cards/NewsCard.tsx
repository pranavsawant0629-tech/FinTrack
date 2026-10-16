import React from "react";
import { Newspaper, ExternalLink, Clock, Tag } from "lucide-react";

export const NewsCard: React.FC<{ articles: Array<Record<string, any>> }> = ({ articles }) => {
  if (!articles || articles.length === 0) return null;

  return (
    <div className="bg-surface border border-border-warm rounded-xl p-4 sm:p-5 shadow-xs my-3 animate-in fade-in duration-150">
      <div className="flex items-center justify-between border-b border-border-warm/60 pb-2.5 mb-3.5">
        <div className="flex items-center gap-2">
          <Newspaper className="w-4 h-4 text-marigold" />
          <h4 className="font-serif font-semibold text-ivory text-sm tracking-tight">
            Market News & Editorial Updates
          </h4>
        </div>
        <span className="text-xs text-muted-warm font-mono">
          {articles.length} {articles.length === 1 ? "article" : "articles"}
        </span>
      </div>

      <div className="space-y-3">
        {articles.map((art, idx) => (
          <div
            key={art.id || idx}
            className="p-3.5 rounded-lg bg-elevated border border-border-warm/60 hover:border-marigold/40 transition-all duration-150"
          >
            <div className="flex items-start justify-between gap-2 mb-1.5">
              <h5 className="text-xs sm:text-sm font-serif font-medium text-ivory hover:text-marigold transition-colors">
                {art.url ? (
                  <a
                    href={art.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="inline-flex items-center gap-1.5 group"
                  >
                    <span>{art.title}</span>
                    <ExternalLink className="w-3 h-3 text-muted-warm group-hover:text-marigold transition-colors shrink-0" />
                  </a>
                ) : (
                  art.title
                )}
              </h5>
            </div>

            {art.summary && (
              <p className="text-xs text-muted-warm/90 line-clamp-2 mb-2.5 leading-relaxed font-sans font-light">
                {art.summary}
              </p>
            )}

            <div className="flex flex-wrap items-center gap-2 text-[10px] text-muted-warm">
              <span className="font-medium text-ivory/80 bg-surface px-2 py-0.5 rounded border border-border-warm font-mono">
                {art.source}
              </span>
              {art.source_type && (
                <span className="capitalize text-muted-warm flex items-center gap-1">
                  <Tag className="w-2.5 h-2.5" />
                  {art.source_type}
                </span>
              )}
              {art.symbol && (
                <span className="font-mono text-ivory bg-teal/20 px-2 py-0.5 rounded border border-teal/40 font-semibold">
                  {art.symbol}
                </span>
              )}
              {art.published_at && (
                <span className="flex items-center gap-1 text-muted-warm/60 ml-auto font-mono">
                  <Clock className="w-2.5 h-2.5" />
                  {art.published_at.slice(0, 10)}
                </span>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};
