import React from "react";
import { TrendingUp, TrendingDown, Clock, Building2 } from "lucide-react";
import type { MarketDataProvenance } from "../../api/types";

interface Props {
  data?: MarketDataProvenance | null;
  list?: MarketDataProvenance[];
}

export const MarketQuoteCard: React.FC<Props> = ({ data, list = [] }) => {
  const quotes = list.length > 0 ? list : data ? [data] : [];
  if (quotes.length === 0) return null;

  return (
    <div className="mt-3 space-y-2.5">
      {quotes.map((q) => {
        const isPositive = q.change >= 0;
        const changeSign = isPositive ? "+" : "";
        const currencySymbol = q.currency === "INR" ? "₹" : q.currency;

        const sessionLabel = q.market_status
          ? q.market_status.replace(/_/g, " ").toUpperCase()
          : "REGULAR";

        return (
          <div
            key={q.symbol}
            className="p-4 rounded-xl bg-surface border border-border-warm text-sm shadow-xs animate-in fade-in duration-150"
          >
            {/* Header: Symbol, Company, and Session Badge */}
            <div className="flex items-center justify-between gap-2 border-b border-border-warm/60 pb-2.5 mb-3">
              <div className="flex items-center gap-2">
                <Building2 className="w-4 h-4 text-muted-warm" />
                <div className="flex items-baseline gap-2">
                  <span className="font-bold text-ivory font-mono text-base tracking-tight">{q.symbol}</span>
                  {q.company_name && (
                    <span className="text-xs text-muted-warm font-sans">{q.company_name}</span>
                  )}
                </div>
              </div>
              <div className="flex items-center gap-1.5">
                <span className="px-2 py-0.5 rounded text-[10px] font-mono font-medium bg-elevated border border-border-warm text-muted-warm">
                  {q.exchange}
                </span>
                <span
                  className={`px-2 py-0.5 rounded text-[10px] font-mono font-medium ${
                    q.market_status === "regular_trading"
                      ? "bg-teal/20 text-teal border border-teal/40"
                      : "bg-elevated text-muted-warm border border-border-warm"
                  }`}
                >
                  {sessionLabel}
                </span>
              </div>
            </div>

            {/* Price & Change Row — ONE Dominant Price */}
            <div className="flex items-baseline justify-between">
              <div className="flex items-baseline gap-3">
                <span className="text-3xl font-bold font-mono text-ivory tracking-tight">
                  {currencySymbol}{q.price.toLocaleString("en-IN", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                </span>
                <div
                  className={`inline-flex items-center gap-1 text-xs font-mono font-semibold px-2.5 py-0.5 rounded-md ${
                    isPositive
                      ? "bg-teal/20 text-ivory border border-teal/50"
                      : "bg-terracotta/20 text-terracotta border border-terracotta/40"
                  }`}
                >
                  {isPositive ? (
                    <TrendingUp className="w-3.5 h-3.5 stroke-[2.5]" />
                  ) : (
                    <TrendingDown className="w-3.5 h-3.5 stroke-[2.5]" />
                  )}
                  <span>
                    {changeSign}{q.change.toFixed(2)} ({changeSign}{q.change_percent.toFixed(2)}%)
                  </span>
                </div>
              </div>

              {/* Data Freshness Indicator */}
              {q.freshness_status && (
                <span className="text-[11px] text-muted-warm font-mono flex items-center gap-1">
                  <Clock className="w-3 h-3 text-muted-warm/70" />
                  {q.freshness_status}
                </span>
              )}
            </div>

            {/* Market Range details if present */}
            {(q.high !== undefined || q.low !== undefined || q.previous_close !== undefined) && (
              <div className="mt-3 pt-2.5 grid grid-cols-3 gap-2 text-xs border-t border-border-warm/50 text-muted-warm font-mono">
                {q.open !== undefined && (
                  <div>
                    <span className="text-muted-warm/60 block text-[10px] font-sans">OPEN</span>
                    <span className="text-ivory">{currencySymbol}{q.open.toFixed(2)}</span>
                  </div>
                )}
                {q.high !== undefined && q.low !== undefined && (
                  <div>
                    <span className="text-muted-warm/60 block text-[10px] font-sans">DAY RANGE</span>
                    <span className="text-ivory">{q.low.toFixed(1)} - {q.high.toFixed(1)}</span>
                  </div>
                )}
                {q.previous_close !== undefined && (
                  <div>
                    <span className="text-muted-warm/60 block text-[10px] font-sans">PREV CLOSE</span>
                    <span className="text-ivory">{currencySymbol}{q.previous_close.toFixed(2)}</span>
                  </div>
                )}
              </div>
            )}

            {/* Provider attribution footer */}
            <div className="mt-2.5 pt-2 flex items-center justify-between text-[10px] text-muted-warm/70 border-t border-border-warm/40 font-mono">
              <span>Source: {q.provider}</span>
              {q.retrieved_at && (
                <span>Timestamp: {new Date(q.retrieved_at).toLocaleTimeString()}</span>
              )}
            </div>
          </div>
        );
      })}
    </div>
  );
};
