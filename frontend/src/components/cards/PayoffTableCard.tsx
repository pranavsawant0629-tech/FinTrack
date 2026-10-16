import React, { useState } from "react";
import { Calculator, ChevronDown, ChevronUp, AlertCircle, CheckCircle2 } from "lucide-react";

interface Props {
  data?: Record<string, any> | null;
}

export const PayoffTableCard: React.FC<Props> = ({ data }) => {
  const [showTable, setShowTable] = useState(false);
  if (!data) return null;

  const optType = data.option_type ? String(data.option_type).toUpperCase() : "OPTION";
  const position = data.position ? String(data.position).toUpperCase() : "LONG";
  const strike = data.strike_price ?? null;
  const premium = data.premium ?? null;
  const breakeven = data.breakeven_price ?? null;
  const hasFeasibleBe = data.has_feasible_breakeven ?? true;
  const maxProfit = data.max_profit ?? "Unlimited";
  const maxLoss = data.max_loss ?? "Unlimited";
  const payoffTable: Array<{ underlying_price: number; profit_loss: number }> =
    data.payoff_table || [];

  return (
    <div className="mt-3 p-4 rounded-xl bg-surface border border-border-warm text-sm shadow-xs animate-in fade-in duration-150">
      <div className="flex items-center justify-between gap-2 border-b border-border-warm/60 pb-2.5 mb-3">
        <div className="flex items-center gap-2">
          <Calculator className="w-4 h-4 text-terracotta" />
          <span className="font-serif font-semibold text-ivory text-sm">
            {position} {optType} Payoff Analysis
          </span>
        </div>
        <span className="px-2 py-0.5 rounded text-[10px] font-mono font-medium bg-terracotta/15 text-terracotta border border-terracotta/30">
          DERIVATIVES
        </span>
      </div>

      {/* Primary Parameters Grid */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5 text-xs font-mono mb-3">
        {strike !== null && (
          <div className="p-2.5 rounded-lg bg-elevated border border-border-warm/60">
            <span className="text-muted-warm/70 block text-[10px] font-sans">STRIKE PRICE</span>
            <span className="text-ivory font-bold text-sm">₹{Number(strike).toFixed(2)}</span>
          </div>
        )}
        {premium !== null && (
          <div className="p-2.5 rounded-lg bg-elevated border border-border-warm/60">
            <span className="text-muted-warm/70 block text-[10px] font-sans">PREMIUM</span>
            <span className="text-ivory font-bold text-sm">₹{Number(premium).toFixed(2)}</span>
          </div>
        )}
        <div className="p-2.5 rounded-lg bg-elevated border border-border-warm/60">
          <span className="text-muted-warm/70 block text-[10px] font-sans">MAX PROFIT</span>
          <span className="text-ivory font-bold text-sm">
            {typeof maxProfit === "number" ? `₹${maxProfit.toFixed(2)}` : String(maxProfit)}
          </span>
        </div>
        <div className="p-2.5 rounded-lg bg-elevated border border-border-warm/60">
          <span className="text-muted-warm/70 block text-[10px] font-sans">MAX LOSS</span>
          <span className="text-terracotta font-bold text-sm">
            {typeof maxLoss === "number" ? `₹${maxLoss.toFixed(2)}` : String(maxLoss)}
          </span>
        </div>
      </div>

      {/* Breakeven Result Banner */}
      <div className="p-3 rounded-lg bg-elevated border border-border-warm flex items-center justify-between text-xs font-mono">
        <div className="flex items-center gap-2">
          {hasFeasibleBe ? (
            <CheckCircle2 className="w-4 h-4 text-teal shrink-0" />
          ) : (
            <AlertCircle className="w-4 h-4 text-terracotta shrink-0" />
          )}
          <span className="text-muted-warm font-sans">
            {hasFeasibleBe ? "Breakeven Price:" : "Feasible Breakeven:"}
          </span>
          <span className="font-bold text-ivory text-sm">
            {hasFeasibleBe
              ? `₹${Number(breakeven).toFixed(2)}`
              : "No non-negative price (Premium > Strike)"}
          </span>
        </div>

        {payoffTable.length > 0 && (
          <button
            type="button"
            onClick={() => setShowTable(!showTable)}
            className="inline-flex items-center gap-1 text-marigold hover:text-marigold-hover text-[11px] font-sans font-medium cursor-pointer transition-colors"
          >
            <span>{showTable ? "Hide Points" : `View Points (${payoffTable.length})`}</span>
            {showTable ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
          </button>
        )}
      </div>

      {/* Expandable Payoff Table */}
      {showTable && payoffTable.length > 0 && (
        <div className="mt-3 max-h-52 overflow-y-auto rounded-lg border border-border-warm font-mono text-[11px]">
          <table className="w-full text-left">
            <thead className="bg-elevated text-muted-warm sticky top-0 border-b border-border-warm font-sans text-[10px] uppercase">
              <tr>
                <th className="py-2 px-3">Underlying Price (₹)</th>
                <th className="py-2 px-3 text-right">Profit / Loss (₹)</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border-warm/40 bg-surface">
              {payoffTable.map((pt, i) => {
                const isProfitable = pt.profit_loss > 0;
                const isZero = pt.profit_loss === 0;
                return (
                  <tr key={i} className="hover:bg-elevated/50 transition-colors">
                    <td className="py-1.5 px-3 text-ivory/90">₹{pt.underlying_price.toFixed(2)}</td>
                    <td
                      className={`py-1.5 px-3 text-right font-semibold ${
                        isZero
                          ? "text-muted-warm"
                          : isProfitable
                          ? "text-teal"
                          : "text-terracotta"
                      }`}
                    >
                      {pt.profit_loss > 0 ? "+" : ""}
                      ₹{pt.profit_loss.toFixed(2)}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
};
