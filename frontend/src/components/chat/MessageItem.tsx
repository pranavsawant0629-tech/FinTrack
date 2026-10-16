import React from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { User, Sparkles, Cpu, Clock, AlertTriangle } from "lucide-react";
import type { ChatMessage } from "../../hooks/useChat";
import { GroundingBadge } from "../cards/GroundingBadge";
import { CitationCard } from "../cards/CitationCard";
import { MarketQuoteCard } from "../cards/MarketQuoteCard";
import { CryptoCard } from "../cards/CryptoCard";
import { PayoffTableCard } from "../cards/PayoffTableCard";
import { PortfolioCard } from "../cards/PortfolioCard";
import { NewsCard } from "../cards/NewsCard";
import { QuizCard } from "../cards/QuizCard";
import { SubtasksSummary } from "../cards/SubtasksSummary";
import { LearningActions } from "./LearningActions";
import { RelatedConcepts } from "./RelatedConcepts";

interface MessageItemProps {
  message: ChatMessage;
  displayName?: string;
  userId?: string;
  isLatest?: boolean;
  onSelectPrompt?: (prompt: string) => void;
  onRetry?: () => void;
}

export const MessageItem: React.FC<MessageItemProps> = ({
  message,
  displayName = "Learner",
  userId,
  isLatest = false,
  onSelectPrompt,
  onRetry,
}) => {
  const isUser = message.role === "user";
  const resp = message.response;

  if (isUser) {
    return (
      <div className="flex justify-end py-3 max-w-4xl mx-auto w-full">
        <div className="flex items-start gap-2.5 max-w-2xl">
          <div className="bg-elevated border border-border-warm text-ivory px-4 py-2.5 rounded-2xl rounded-tr-xs shadow-xs text-xs sm:text-sm leading-relaxed whitespace-pre-wrap font-sans">
            {message.content}
          </div>
          <div
            className="w-8 h-8 rounded-full bg-surface border border-border-warm flex items-center justify-center shrink-0 text-muted-warm text-xs font-serif font-bold shadow-xs"
            title={displayName}
          >
            {displayName.slice(0, 2).toUpperCase() || <User className="w-4 h-4" />}
          </div>
        </div>
      </div>
    );
  }

  // Failed Assistant turn handling (Section 6a)
  if (message.status === "failed" || message.error) {
    return (
      <div className="flex items-start gap-3 py-4 max-w-4xl mx-auto w-full animate-in fade-in duration-200">
        <div className="w-8 h-8 rounded-full bg-terracotta/20 border border-terracotta/50 flex items-center justify-center shrink-0 text-terracotta mt-0.5 shadow-xs">
          <AlertTriangle className="w-4 h-4" />
        </div>
        <div className="flex-1 space-y-2.5 min-w-0 bg-surface border border-terracotta/40 rounded-2xl p-4 sm:p-5">
          <div className="flex items-center justify-between">
            <span className="font-serif font-semibold text-xs text-ivory">
              Inquiry Saved • Response Incomplete
            </span>
            <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-terracotta/20 text-terracotta border border-terracotta/30">
              RETRYABLE
            </span>
          </div>
          <p className="text-xs sm:text-sm text-ivory/90 leading-relaxed font-sans">
            {message.content}
          </p>
          {message.error && (
            <p className="text-[11px] font-mono text-muted-warm pt-0.5">
              Notice: {message.error}
            </p>
          )}
          {onRetry && (
            <div className="pt-1.5">
              <button
                type="button"
                onClick={onRetry}
                className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium bg-marigold text-espresso hover:bg-marigold-hover transition-colors cursor-pointer"
              >
                Retry Response
              </button>
            </div>
          )}
        </div>
      </div>
    );
  }

  // Assistant response
  const marketList = resp?.market_data_list && resp.market_data_list.length > 0
    ? resp.market_data_list
    : resp?.market_data
    ? [resp.market_data]
    : [];

  return (
    <div className="flex items-start gap-3 py-4 max-w-4xl mx-auto w-full animate-in fade-in duration-200">
      <div className="w-8 h-8 rounded-full bg-surface border border-border-warm flex items-center justify-center shrink-0 text-marigold mt-0.5 shadow-xs">
        <Sparkles className="w-4 h-4" />
      </div>

      <div className="flex-1 space-y-3 min-w-0">
        {/* Header Metadata Bar */}
        <div className="flex flex-wrap items-center justify-between gap-2 pb-1">
          <div className="flex items-center gap-2">
            <span className="font-serif font-semibold text-sm text-ivory tracking-tight">
              {resp?.agent_name || "Finova AI"}
            </span>
            {resp?.domain_detected && (
              <span className="font-mono text-[10px] uppercase tracking-wider px-2 py-0.5 rounded bg-surface border border-border-warm text-muted-warm">
                {resp.domain_detected}
              </span>
            )}
            {resp?.topic && (
              <span className="font-mono text-[10px] font-semibold uppercase tracking-wider px-2 py-0.5 rounded bg-marigold/15 border border-marigold/30 text-marigold">
                TOPIC: {resp.topic}
              </span>
            )}
          </div>

          {resp?.grounding_status && (
            <GroundingBadge status={resp.grounding_status} />
          )}
        </div>

        {/* Multi-Intent Subtasks Breakdown if Compound */}
        {resp?.sub_tasks && <SubtasksSummary subTasks={resp.sub_tasks} />}

        {/* Rich Card: Market Quotes */}
        {marketList.length > 0 && (
          <MarketQuoteCard list={marketList} />
        )}

        {/* Rich Card: Crypto Data */}
        {resp?.crypto_data && (
          <CryptoCard data={resp.crypto_data} />
        )}

        {/* Rich Card: Derivatives & Payoff Table */}
        {resp?.derivatives_data && (
          <PayoffTableCard data={resp.derivatives_data} />
        )}

        {/* Rich Card: Portfolio & What-If Stress Tests */}
        {resp?.portfolio_data && (
          <PortfolioCard data={resp.portfolio_data} />
        )}

        {/* Rich Card: News Articles */}
        {resp?.news_data && resp.news_data.length > 0 && (
          <NewsCard articles={resp.news_data} />
        )}

        {/* Rich Card: Interactive Quiz */}
        {resp?.quiz_data && (
          <QuizCard data={resp.quiz_data} userId={userId} />
        )}

        {/* Main Text / Answer */}
        <div className="text-xs sm:text-sm text-ivory/95 leading-relaxed bg-surface/80 p-4 sm:p-5 rounded-2xl border border-border-warm shadow-xs max-w-none font-sans prose prose-invert prose-headings:font-serif prose-headings:text-ivory prose-strong:text-marigold prose-p:leading-relaxed prose-pre:bg-espresso prose-pre:border prose-pre:border-border-warm">
          <ReactMarkdown remarkPlugins={[remarkGfm]}>
            {message.content}
          </ReactMarkdown>
        </div>

        {/* Citations & Verified Authorities */}
        {resp?.citations && resp.citations.length > 0 && (
          <CitationCard citations={resp.citations} />
        )}

        {/* Phase 11: Contextual Learning Controls & Related Concepts */}
        {(() => {
          const isSafetyRefusal = resp?.sub_tasks?.[0]?.intent === "advice_refusal" || resp?.model_used === "deterministic_guardrail";
          const hasPureQuoteOnly = (Boolean(resp?.market_data) || Boolean(resp?.crypto_data)) && !resp?.topic;
          const isEducationalTurn = Boolean(resp?.topic) && !isSafetyRefusal && !hasPureQuoteOnly && message.status === "complete" && !message.error;

          if (!isLatest || !isEducationalTurn || !onSelectPrompt) return null;

          return (
            <div className="space-y-2 pt-1">
              {resp?.related_concepts && resp.related_concepts.length > 0 && (
                <RelatedConcepts
                  concepts={resp.related_concepts}
                  activeTopic={resp.topic}
                  onSelectConcept={onSelectPrompt}
                />
              )}

              {resp?.topic && (
                <LearningActions
                  topic={resp.topic}
                  onSelectAction={onSelectPrompt}
                />
              )}
            </div>
          );
        })()}

        {/* Telemetry and Model Info */}
        <div className="flex flex-wrap items-center justify-between text-[11px] text-muted-warm pt-1 border-t border-border-warm/40">
          <div className="flex items-center gap-3">
            {resp?.model_used && (
              <span className="flex items-center gap-1.5 font-mono">
                <Cpu className="w-3.5 h-3.5 text-muted-warm/70" />
                <span>{resp.model_used}</span>
              </span>
            )}
            {resp?.latency_ms !== undefined && resp.latency_ms > 0 && (
              <span className="flex items-center gap-1.5 font-mono">
                <Clock className="w-3.5 h-3.5 text-muted-warm/70" />
                <span>{resp.latency_ms.toFixed(0)}ms</span>
              </span>
            )}
          </div>
        </div>

        {/* Regulatory Disclaimer */}
        {resp?.disclaimer && (
          <div className="flex items-start gap-1.5 text-[10px] text-muted-warm bg-surface/50 p-2.5 rounded-xl border border-border-warm/60">
            <AlertTriangle className="w-3.5 h-3.5 shrink-0 text-muted-warm/70 mt-0.5" />
            <p className="leading-relaxed font-sans">{resp.disclaimer}</p>
          </div>
        )}
      </div>
    </div>
  );
};
