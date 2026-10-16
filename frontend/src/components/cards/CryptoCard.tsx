import React from "react";
import { Coins, TrendingUp, TrendingDown } from "lucide-react";

interface Props {
  data?: Record<string, any> | null;
}

export const CryptoCard: React.FC<Props> = ({ data }) => {
  if (!data) return null;

  const symbol = data.symbol || data.coin_id?.toUpperCase() || "CRYPTO";
  const name = data.name || data.coin_name || symbol;
  const priceInr = data.price_inr ?? data.inr_price ?? null;
  const priceUsd = data.price_usd ?? data.usd_price ?? null;
  const change24h = data.change_24h_percent ?? data.usd_24h_change ?? 0;
  const isPositive = change24h >= 0;
  const provider = data.provider || "CoinGecko API";

  return (
    <div className="mt-3 p-4 rounded-xl bg-surface border border-border-warm text-sm shadow-xs animate-in fade-in duration-150">
      <div className="flex items-center justify-between gap-2 border-b border-border-warm/60 pb-2.5 mb-3">
        <div className="flex items-center gap-2">
          <Coins className="w-4 h-4 text-marigold" />
          <span className="font-bold font-mono text-ivory text-base">{symbol}</span>
          <span className="text-xs text-muted-warm font-sans">{name}</span>
        </div>
        <span className="px-2 py-0.5 rounded text-[10px] font-mono font-medium bg-marigold/15 text-marigold border border-marigold/30">
          CRYPTO
        </span>
      </div>

      <div className="flex items-baseline justify-between">
        <div className="space-y-1">
          {priceInr !== null && (
            <div className="text-3xl font-bold font-mono text-ivory tracking-tight">
              ₹{Number(priceInr).toLocaleString("en-IN", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
            </div>
          )}
          {priceUsd !== null && (
            <div className="text-xs text-muted-warm font-mono">
              ${Number(priceUsd).toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })} USD
            </div>
          )}
        </div>

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
            {isPositive ? "+" : ""}{Number(change24h).toFixed(2)}%
          </span>
        </div>
      </div>

      <div className="mt-3 pt-2 flex items-center justify-between text-[10px] text-muted-warm/70 border-t border-border-warm/40 font-mono">
        <span>Source: {provider}</span>
        <span>Simulated educational context</span>
      </div>
    </div>
  );
};
