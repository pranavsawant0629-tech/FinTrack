import React from "react";
import { PieChart, TrendingUp, TrendingDown, Layers } from "lucide-react";

interface PortfolioCardProps {
  data: Record<string, any>;
}

export const PortfolioCard: React.FC<PortfolioCardProps> = ({ data }) => {
  // Scenario 1: What-If Stress Test result
  if (data.scenario_description || data.simulated_portfolio_value !== undefined) {
    const isGain = (data.portfolio_delta_value ?? 0) >= 0;
    const sign = isGain ? "+" : "";

    return (
      <div className="bg-surface border border-border-warm rounded-xl p-4 sm:p-5 shadow-xs my-3 animate-in fade-in duration-150">
        <div className="flex items-center justify-between border-b border-border-warm/60 pb-2.5 mb-3.5">
          <div className="flex items-center gap-2">
            <Layers className="w-4 h-4 text-marigold" />
            <h4 className="font-serif font-semibold text-ivory text-sm tracking-tight">
              Portfolio Stress Simulation
            </h4>
          </div>
          <span className="text-[10px] font-mono bg-marigold/15 text-marigold px-2 py-0.5 rounded border border-marigold/30 font-medium">
            WHAT-IF SCENARIO
          </span>
        </div>

        <p className="text-xs text-ivory/90 mb-3.5 bg-elevated p-3 rounded-lg border border-border-warm/60 font-sans">
          <span className="text-muted-warm font-medium">Scenario: </span>
          {data.scenario_description}
        </p>

        <div className="grid grid-cols-1 sm:grid-cols-3 gap-2.5 text-center mb-4">
          <div className="bg-elevated p-3 rounded-lg border border-border-warm/60">
            <span className="text-[10px] text-muted-warm block mb-0.5 font-sans uppercase">Original Value</span>
            <span className="text-sm font-bold text-ivory/80 font-mono">
              ₹{(data.original_portfolio_value ?? 0).toLocaleString("en-IN", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
            </span>
          </div>

          <div className="bg-elevated p-3 rounded-lg border border-border-warm/60">
            <span className="text-[10px] text-muted-warm block mb-0.5 font-sans uppercase">Simulated Value</span>
            <span className="text-base font-bold text-ivory font-mono">
              ₹{(data.simulated_portfolio_value ?? 0).toLocaleString("en-IN", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
            </span>
          </div>

          <div className={`p-3 rounded-lg border ${isGain ? "bg-teal/20 border-teal/40 text-ivory" : "bg-terracotta/20 border-terracotta/40 text-terracotta"}`}>
            <span className="text-[10px] block mb-0.5 font-sans uppercase opacity-80">Projected Impact</span>
            <span className="text-sm font-bold font-mono flex items-center justify-center gap-1">
              {isGain ? <TrendingUp className="w-3.5 h-3.5 stroke-[2.5]" /> : <TrendingDown className="w-3.5 h-3.5 stroke-[2.5]" />}
              {sign}₹{Math.abs(data.portfolio_delta_value ?? 0).toLocaleString("en-IN", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
              <span className="text-[11px] ml-0.5">({sign}{(data.portfolio_delta_pct ?? 0).toFixed(2)}%)</span>
            </span>
          </div>
        </div>

        {Array.isArray(data.impacted_holdings) && data.impacted_holdings.length > 0 && (
          <div className="overflow-x-auto text-xs rounded-lg border border-border-warm">
            <table className="w-full text-left text-ivory">
              <thead>
                <tr className="bg-elevated text-muted-warm text-[10px] font-sans uppercase border-b border-border-warm">
                  <th className="py-2 px-3 font-medium">Holding</th>
                  <th className="py-2 px-3 font-medium text-right">Original Price</th>
                  <th className="py-2 px-3 font-medium text-right">Simulated Price</th>
                  <th className="py-2 px-3 font-medium text-right">Impact</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border-warm/40 font-mono bg-surface">
                {data.impacted_holdings.map((h: any, idx: number) => {
                  const hGain = (h.value_delta ?? 0) >= 0;
                  return (
                    <tr key={idx} className="hover:bg-elevated/40 transition-colors">
                      <td className="py-1.5 px-3 font-sans font-medium text-ivory">{h.symbol}</td>
                      <td className="py-1.5 px-3 text-right">₹{(h.original_price ?? 0).toLocaleString("en-IN", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</td>
                      <td className="py-1.5 px-3 text-right">₹{(h.simulated_price ?? 0).toLocaleString("en-IN", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</td>
                      <td className={`py-1.5 px-3 text-right font-semibold ${hGain ? "text-teal" : "text-terracotta"}`}>
                        {hGain ? "+" : ""}₹{(h.value_delta ?? 0).toLocaleString("en-IN", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
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
  }

  // Scenario 2: Standard Portfolio Overview & Metrics
  const metrics = data.metrics || {};
  const portfolio = data.portfolio || {};
  const totalValue = metrics.total_current_value ?? 0;
  const invested = metrics.total_invested ?? 0;
  const pnl = metrics.unrealized_pnl ?? 0;
  const pnlPct = metrics.unrealized_pnl_pct ?? 0;
  const isPnlPositive = pnl >= 0;

  return (
    <div className="bg-surface border border-border-warm rounded-xl p-4 sm:p-5 shadow-xs my-3 animate-in fade-in duration-150">
      <div className="flex items-center justify-between border-b border-border-warm/60 pb-2.5 mb-3.5">
        <div className="flex items-center gap-2">
          <PieChart className="w-4 h-4 text-teal" />
          <h4 className="font-serif font-semibold text-ivory text-sm tracking-tight">
            Portfolio Overview
          </h4>
        </div>
        <span className="text-xs text-muted-warm font-sans">
          Holdings: <span className="font-mono text-ivory font-bold">{metrics.holdings_count ?? (portfolio.holdings?.length || 0)}</span>
        </span>
      </div>

      {/* ONE Dominant Number: Total Portfolio Value */}
      <div className="mb-4 p-3.5 rounded-lg bg-elevated border border-border-warm/60 flex flex-wrap items-baseline justify-between gap-2">
        <div>
          <span className="text-[10px] font-sans text-muted-warm uppercase tracking-wider block">Total Portfolio Value</span>
          <span className="text-2xl sm:text-3xl font-bold font-mono text-ivory tracking-tight">
            ₹{totalValue.toLocaleString("en-IN", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
          </span>
        </div>
        <div className="flex items-center gap-3">
          <div>
            <span className="text-[10px] font-sans text-muted-warm uppercase tracking-wider block">Invested</span>
            <span className="text-sm font-mono text-ivory/80">
              ₹{invested.toLocaleString("en-IN", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
            </span>
          </div>
          <div className={`px-2.5 py-1 rounded-md border font-mono text-xs font-semibold flex items-center gap-1 ${
            isPnlPositive ? "bg-teal/20 border-teal/40 text-ivory" : "bg-terracotta/20 border-terracotta/40 text-terracotta"
          }`}>
            {isPnlPositive ? <TrendingUp className="w-3.5 h-3.5 stroke-[2.5]" /> : <TrendingDown className="w-3.5 h-3.5 stroke-[2.5]" />}
            <span>
              {isPnlPositive ? "+" : ""}₹{pnl.toLocaleString("en-IN", { minimumFractionDigits: 2, maximumFractionDigits: 2 })} ({isPnlPositive ? "+" : ""}{pnlPct.toFixed(2)}%)
            </span>
          </div>
        </div>
      </div>

      {Array.isArray(portfolio.holdings) && portfolio.holdings.length > 0 && (
        <div className="overflow-x-auto text-xs rounded-lg border border-border-warm mt-3">
          <table className="w-full text-left text-ivory">
            <thead>
              <tr className="bg-elevated text-muted-warm text-[10px] font-sans uppercase border-b border-border-warm">
                <th className="py-2 px-3 font-medium">Asset</th>
                <th className="py-2 px-3 font-medium text-right">Qty</th>
                <th className="py-2 px-3 font-medium text-right">Avg Cost</th>
                <th className="py-2 px-3 font-medium text-right">Cur Price</th>
                <th className="py-2 px-3 font-medium text-right">Current Value</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border-warm/40 font-mono bg-surface">
              {portfolio.holdings.map((h: any, idx: number) => (
                <tr key={idx} className="hover:bg-elevated/40 transition-colors">
                  <td className="py-1.5 px-3 font-sans font-medium text-ivory">{h.symbol}</td>
                  <td className="py-1.5 px-3 text-right">{h.quantity}</td>
                  <td className="py-1.5 px-3 text-right">₹{(h.average_buy_price ?? 0).toLocaleString("en-IN", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</td>
                  <td className="py-1.5 px-3 text-right">₹{(h.current_price ?? 0).toLocaleString("en-IN", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</td>
                  <td className="py-1.5 px-3 text-right font-semibold text-ivory">
                    ₹{((h.quantity || 0) * (h.current_price || 0)).toLocaleString("en-IN", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
};
