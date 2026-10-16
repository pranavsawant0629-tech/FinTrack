import React, { useState, useEffect } from "react";
import type { TutorSectionId, ConversationSummary } from "../../api/types";
import { apiClient } from "../../api/client";
import {
  TrendingUp,
  BarChart2,
  PieChart,
  Coins,
  Briefcase,
  Newspaper,
  HelpCircle,
  Compass,
  ArrowUpRight,
  ArrowRight,
  Sparkles,
} from "lucide-react";

interface TutorLandingProps {
  sectionId: TutorSectionId;
  userId?: string;
  onSelectPrompt: (prompt: string) => void;
  onContinueLearning?: (conversationId: string) => void;
  onNewChat?: () => void;
}

interface TutorConfig {
  id: TutorSectionId;
  title: string;
  italicTitle?: string;
  afterTitle?: string;
  badge: string;
  tagline: string;
  description: string;
  icon: React.ComponentType<{ className?: string }>;
  accentColor: "teal" | "marigold" | "terracotta" | "ivory";
  prompts: {
    tag: string;
    tagTheme: "teal" | "marigold" | "terracotta";
    title: string;
    subtext: string;
    prompt: string;
  }[];
}

const TUTOR_CONFIGS: Record<TutorSectionId, TutorConfig> = {
  general: {
    id: "general",
    title: "Understand money.",
    italicTitle: "Learn the market.",
    afterTitle: "Think for yourself.",
    badge: "FINANCIAL LEARNING • MARKETS • INDIA",
    tagline: "General Financial Intelligence & Multi-Subject Exploration",
    description:
      "Finova bridges disciplined financial education with live Indian equity market context — grounding complex instruments in clear, first-principle explanations.",
    icon: Sparkles,
    accentColor: "marigold",
    prompts: [
      {
        tag: "EQUITIES",
        tagTheme: "teal",
        title: "What is an IPO, and what is Reliance trading at today?",
        subtext: "NSE Snapshot • Draft RHP Explainer",
        prompt: "What is an IPO, and what is Reliance trading at today?",
      },
      {
        tag: "SIP LAB",
        tagTheme: "marigold",
        title: "Explain SIPs like I'm a beginner — calculate ₹5,000/mo over 10 years",
        subtext: "Interactive Step-up Simulator",
        prompt: "Explain SIPs like I'm a beginner — calculate ₹5,000/mo over 10 years at 12% return",
      },
      {
        tag: "DERIVATIVES",
        tagTheme: "terracotta",
        title: "Teach me Call Options: strike price, breakeven, and risk payoff",
        subtext: "NIFTY Payoff Visualizer",
        prompt: "Teach me Call Options: strike price, breakeven, and risk payoff for a Long Call at 22000 with premium 150",
      },
      {
        tag: "SELF-CHECK",
        tagTheme: "teal",
        title: "Quiz me on Mutual Funds & Expense Ratios",
        subtext: "3-Question Diagnostic • Level 1",
        prompt: "Quiz me on Mutual Funds & Expense Ratios",
      },
      {
        tag: "BUDGETING",
        tagTheme: "marigold",
        title: "What is the 50/30/20 budgeting rule and how do I apply it?",
        subtext: "Framework • Rupee Allocator",
        prompt: "What is the 50/30/20 budgeting rule and how do I apply it to a ₹60,000 monthly income?",
      },
      {
        tag: "MACRO / CRYPTO",
        tagTheme: "terracotta",
        title: "Explain Bitcoin volatility vs NIFTY 50",
        subtext: "Beta Comparison • Indian Context",
        prompt: "Explain Bitcoin volatility vs NIFTY 50 and what is Bitcoin's live price in INR?",
      },
    ],
  },
  equity: {
    id: "equity",
    title: "Master Indian Equities",
    italicTitle: "& Company Fundamentals.",
    afterTitle: "Build valuation discipline.",
    badge: "EQUITY TUTOR • NSE / BSE",
    tagline: "Stock Valuation, Balance Sheets & Price Action",
    description:
      "Study listed Indian businesses, dissect P/E multiples and corporate filings, and explore live NSE quotes through first-principle fundamental analysis.",
    icon: TrendingUp,
    accentColor: "teal",
    prompts: [
      {
        tag: "MARKET SNAPSHOT",
        tagTheme: "teal",
        title: "What is Reliance Industries trading at today, and what is its P/E?",
        subtext: "Live NSE Quote • Valuation Metric",
        prompt: "What is Reliance Industries trading at today, and explain its PE ratio?",
      },
      {
        tag: "CONCEPT",
        tagTheme: "teal",
        title: "How does the IPO book-building process work on NSE and BSE?",
        subtext: "Price Bands • Allotment Math",
        prompt: "What is an IPO and how does the allotment process work on NSE?",
      },
      {
        tag: "FUNDAMENTALS",
        tagTheme: "marigold",
        title: "Explain Book Value vs Market Cap for Tata Motors",
        subtext: "P/B Ratio • Balance Sheet Health",
        prompt: "Explain the difference between Book Value and Market Cap for Tata Motors",
      },
      {
        tag: "EARNINGS",
        tagTheme: "terracotta",
        title: "How do quarterly earnings announcements impact stock volatility?",
        subtext: "Guidance • Market Expectations",
        prompt: "How do quarterly earnings announcements impact stock volatility?",
      },
    ],
  },
  derivatives: {
    id: "derivatives",
    title: "Demystify Futures & Options",
    italicTitle: "Payoffs & Hedging.",
    afterTitle: "Manage risk before reward.",
    badge: "DERIVATIVES TUTOR • F&O LAB",
    tagline: "Options Chains, Greeks & Hedging Strategies",
    description:
      "Understand strikes, implied volatility, moneyness, and risk boundaries without speculative gambling. Grounded in mathematical payoff realities.",
    icon: BarChart2,
    accentColor: "terracotta",
    prompts: [
      {
        tag: "LONG CALL",
        tagTheme: "terracotta",
        title: "Teach me Call Options: strike price, breakeven, and risk payoff",
        subtext: "Long Call at 22000 • Premium 150",
        prompt: "Teach me Call Options: strike price, breakeven, and risk payoff for a Long Call at 22000 with premium 150",
      },
      {
        tag: "OPTION CHAIN",
        tagTheme: "teal",
        title: "What is an Option Chain and what do Open Interest (OI) build-ups mean?",
        subtext: "Support & Resistance • Put-Call Ratio",
        prompt: "What is an Option Chain and what do Open Interest (OI) build-ups signal?",
      },
      {
        tag: "SPREADS",
        tagTheme: "marigold",
        title: "What is the maximum loss and profit profile of a Bull Call Spread?",
        subtext: "Defined Risk Strategy • NIFTY Example",
        prompt: "What is the maximum loss and profit profile of a Bull Call Spread?",
      },
      {
        tag: "GREEKS",
        tagTheme: "terracotta",
        title: "Explain Delta and Theta decay: why do OTM options expire worthless?",
        subtext: "Time Value Erosion • Probability",
        prompt: "Explain Delta and Theta decay: why do out-of-the-money options lose value near expiry?",
      },
    ],
  },
  personal_finance: {
    id: "personal_finance",
    title: "Build Lasting Wealth",
    italicTitle: "& Financial Discipline.",
    afterTitle: "Compound your rupee.",
    badge: "PERSONAL FINANCE TUTOR • WEALTH LAB",
    tagline: "SIP Mathematics, Budgeting Frameworks & Tax Planning",
    description:
      "Learn systematic investing, emergency fund sizing, tax-saving strategies, and inflation-adjusted asset allocation tailored to Indian households.",
    icon: PieChart,
    accentColor: "marigold",
    prompts: [
      {
        tag: "SIP CALCULATOR",
        tagTheme: "marigold",
        title: "Calculate ₹5,000/mo SIP over 10 years at 12% return",
        subtext: "Power of Compounding • Rupee Growth",
        prompt: "Explain SIPs like I'm a beginner — calculate ₹5,000/mo over 10 years at 12% return",
      },
      {
        tag: "BUDGETING",
        tagTheme: "teal",
        title: "Apply the 50/30/20 rule to a ₹60,000 monthly take-home salary",
        subtext: "Needs • Wants • Savings Split",
        prompt: "What is the 50/30/20 budgeting rule and how do I apply it to a ₹60,000 monthly income?",
      },
      {
        tag: "STEP-UP SIP",
        tagTheme: "marigold",
        title: "How does a 10% annual step-up drastically accelerate compounding?",
        subtext: "Wealth Accelerator • Long-term Math",
        prompt: "How does an annual step-up SIP accelerate wealth creation compared to a flat SIP?",
      },
      {
        tag: "EMERGENCY FUND",
        tagTheme: "terracotta",
        title: "How should a 25-year-old size an emergency fund vs equity mutual funds?",
        subtext: "Liquid Funds • 6-Month Runway",
        prompt: "How should a 25-year-old allocate an emergency fund vs equity mutual funds?",
      },
    ],
  },
  crypto: {
    id: "crypto",
    title: "Explore Digital Assets",
    italicTitle: "& Blockchain Economics.",
    afterTitle: "Separate hype from fundamentals.",
    badge: "CRYPTO TUTOR • DIGITAL ASSETS",
    tagline: "Bitcoin, Ethereum & Crypto Volatility in INR",
    description:
      "Study crypto market cycles, tokenomics, consensus mechanisms, and live INR prices with sober, objective risk analysis.",
    icon: Coins,
    accentColor: "terracotta",
    prompts: [
      {
        tag: "MACRO BETA",
        tagTheme: "terracotta",
        title: "Explain Bitcoin volatility vs NIFTY 50 and live Bitcoin INR price",
        subtext: "Beta Comparison • Live Price Snapshot",
        prompt: "Explain Bitcoin volatility vs NIFTY 50 and what is Bitcoin's live price in INR?",
      },
      {
        tag: "PROOF OF STAKE",
        tagTheme: "teal",
        title: "How does Ethereum Proof-of-Stake differ from Bitcoin Proof-of-Work?",
        subtext: "Consensus Mechanism • Energy & Yield",
        prompt: "How does Ethereum's Proof-of-Stake consensus work compared to Bitcoin mining?",
      },
      {
        tag: "HALVING CYCLE",
        tagTheme: "marigold",
        title: "What is the 4-year Bitcoin halving cycle and its supply impact?",
        subtext: "Stock-to-Flow • Supply Dynamics",
        prompt: "What is a crypto market cycle and how does Bitcoin halving affect supply?",
      },
      {
        tag: "INDIAN TAXATION",
        tagTheme: "terracotta",
        title: "What are the tax implications of Virtual Digital Assets (VDA) in India?",
        subtext: "30% Flat Tax • 1% TDS Mandate",
        prompt: "What are the tax rules and TDS requirements for crypto trading in India?",
      },
    ],
  },
  portfolio: {
    id: "portfolio",
    title: "Architect Robust Portfolios",
    italicTitle: "& Master Risk Ratios.",
    afterTitle: "Balance return with drawdowns.",
    badge: "PORTFOLIO TUTOR • ASSET ALLOCATION",
    tagline: "Sharpe Ratios, Correlation & Risk Management",
    description:
      "Stress-test asset weights, evaluate portfolio drawdowns, compute risk-adjusted return metrics, and align holdings with your horizon.",
    icon: Briefcase,
    accentColor: "teal",
    prompts: [
      {
        tag: "RISK RATIOS",
        tagTheme: "teal",
        title: "How do I calculate the Sharpe Ratio of a 70/30 equity/debt portfolio?",
        subtext: "Risk-Adjusted Return • Formula & Meaning",
        prompt: "How do I calculate the Sharpe Ratio of a portfolio with 70% equities and 30% debt?",
      },
      {
        tag: "REBALANCING",
        tagTheme: "marigold",
        title: "Why does periodic rebalancing protect against major market crashes?",
        subtext: "Systematic Discipline • Trim High, Buy Low",
        prompt: "Explain portfolio rebalancing and why asset allocation determines 90% of returns",
      },
      {
        tag: "DRAWDOWN",
        tagTheme: "terracotta",
        title: "What does a maximum drawdown of 25% mean for a retirement portfolio?",
        subtext: "Recovery Mathematics • Stress Testing",
        prompt: "What does a maximum drawdown of 25% mean for a retirement portfolio?",
      },
      {
        tag: "DIVERSIFICATION",
        tagTheme: "teal",
        title: "How does adding gold or liquid debt lower overall portfolio volatility?",
        subtext: "Uncorrelated Assets • Efficient Frontier",
        prompt: "How does adding gold or debt to an all-equity portfolio reduce portfolio volatility?",
      },
    ],
  },
  news: {
    id: "news",
    title: "Market Intelligence",
    italicTitle: "& Macro Context.",
    afterTitle: "Understand what moves the indices.",
    badge: "MARKET NEWS AGENT • MACRO BRIEF",
    tagline: "Indian Macroeconomic Signals, Earnings & Policy Updates",
    description:
      "Stay grounded with concise, objective market commentary, corporate announcements, RBI monetary developments, and global macroeconomic cues.",
    icon: Newspaper,
    accentColor: "ivory",
    prompts: [
      {
        tag: "HEADLINES",
        tagTheme: "teal",
        title: "What are the key financial headlines driving Indian markets today?",
        subtext: "Market Roundup • Sector Movers",
        prompt: "What are the key financial headlines driving Indian markets today?",
      },
      {
        tag: "CENTRAL BANK",
        tagTheme: "marigold",
        title: "Summarize recent RBI monetary policy updates and repo rate stance",
        subtext: "MPC Committee • Inflation Targeting",
        prompt: "Summarize recent RBI monetary policy updates and inflation expectations",
      },
      {
        tag: "GLOBAL CUES",
        tagTheme: "terracotta",
        title: "How do US Federal Reserve rate decisions affect foreign institutional flows?",
        subtext: "FII / DII Dynamics • Rupee Exchange Rate",
        prompt: "Explain how US Federal Reserve rate commentary impacts FII flows into India",
      },
      {
        tag: "CORPORATE ACTIONS",
        tagTheme: "teal",
        title: "What major corporate actions or earnings results were announced recently?",
        subtext: "Dividends • Bonus Issues • Results",
        prompt: "What corporate actions or earnings results were announced this week?",
      },
    ],
  },
  quiz: {
    id: "quiz",
    title: "Diagnostic Self-Checks",
    italicTitle: "& Financial Challenges.",
    afterTitle: "Test your understanding.",
    badge: "QUIZ & CHALLENGE • DIAGNOSTIC LAB",
    tagline: "Interactive Knowledge Checks with Step-by-Step Explanations",
    description:
      "Reinforce concepts through targeted questions spanning equities, options, debt, and personal finance with deterministic scoring and explanations.",
    icon: HelpCircle,
    accentColor: "teal",
    prompts: [
      {
        tag: "MUTUAL FUNDS",
        tagTheme: "teal",
        title: "Quiz me on Mutual Funds & Expense Ratios with 3 questions",
        subtext: "Diagnostic Check • Level 1",
        prompt: "Quiz me on Mutual Funds & Expense Ratios",
      },
      {
        tag: "MARKET BASICS",
        tagTheme: "marigold",
        title: "Give me a beginner quiz on Stock Market Basics and P/E ratios",
        subtext: "Equity Fundamentals • 3 Questions",
        prompt: "Give me a beginner quiz on Stock Market Basics and P/E ratios",
      },
      {
        tag: "DERIVATIVES",
        tagTheme: "terracotta",
        title: "Challenge me with an intermediate options & derivatives quiz",
        subtext: "Strike, Moneyness, and Greeks",
        prompt: "Challenge me with an intermediate options & derivatives quiz",
      },
      {
        tag: "PERSONAL FINANCE",
        tagTheme: "teal",
        title: "Test my knowledge on emergency funds, SIPs, and personal taxation",
        subtext: "Rupee Allocation Diagnostic",
        prompt: "Test my knowledge on emergency funds, SIPs, and personal taxation",
      },
    ],
  },
  onboarding: {
    id: "onboarding",
    title: "Explore Finova AI",
    italicTitle: "& Architecture Guide.",
    afterTitle: "Your financial co-pilot.",
    badge: "SYSTEM GUIDE • CAPABILITIES & FAQ",
    tagline: "Architecture Overview, Specialized Agents & Learner Memory",
    description:
      "Learn how Finova coordinates 8 domain specialists, personalizes explanations to your experience level, and verifies citations against official sources.",
    icon: Compass,
    accentColor: "ivory",
    prompts: [
      {
        tag: "CAPABILITIES",
        tagTheme: "teal",
        title: "What financial subjects and tools does Finova AI support?",
        subtext: "Agent Capabilities • Tools Catalog",
        prompt: "What financial subjects and tools does Finova AI support?",
      },
      {
        tag: "MEMORY",
        tagTheme: "marigold",
        title: "How does Finova remember my learning level and financial preferences?",
        subtext: "Zero-Cloud • Local Memory DB",
        prompt: "How does Finova remember my learning level and financial preferences?",
      },
      {
        tag: "GROUNDING",
        tagTheme: "teal",
        title: "What makes Finova's market citations and grounded answers trustworthy?",
        subtext: "SEBI Circulars • NSE Live Data",
        prompt: "What makes Finova's market citations and grounded answers trustworthy?",
      },
      {
        tag: "FAQS",
        tagTheme: "marigold",
        title: "Show me frequently asked questions about using Finova AI",
        subtext: "Usage Guide • Disclaimer & Policies",
        prompt: "Show me frequently asked questions about using Finova AI",
      },
    ],
  },
};

export const TutorLanding: React.FC<TutorLandingProps> = ({
  sectionId,
  userId,
  onSelectPrompt,
  onContinueLearning,
}) => {
  const config = TUTOR_CONFIGS[sectionId] || TUTOR_CONFIGS.general;
  const IconComponent = config.icon;
  const [recentConv, setRecentConv] = useState<ConversationSummary | null>(null);

  useEffect(() => {
    let isMounted = true;
    if (!userId) return;

    const domainFilter = sectionId === "general" ? null : sectionId;
    apiClient
      .listConversations(userId, domainFilter)
      .then((list) => {
        if (isMounted) {
          if (list && list.length > 0) {
            setRecentConv(list[0]);
          } else {
            setRecentConv(null);
          }
        }
      })
      .catch(() => {
        if (isMounted) setRecentConv(null);
      });

    return () => {
      isMounted = false;
    };
  }, [sectionId, userId]);

  return (
    <div className="max-w-4xl mx-auto my-6 sm:my-10 text-center space-y-7 animate-in fade-in duration-300">
      {/* Top Pill / Badge */}
      <div className="inline-flex items-center gap-2 px-3.5 py-1 rounded-full bg-surface border border-border-warm text-[11px] tracking-wider uppercase font-mono text-muted-warm shadow-xs">
        <IconComponent className="w-3.5 h-3.5 text-marigold" />
        <span>{config.badge}</span>
      </div>

      {/* Editorial Headline */}
      <div className="space-y-3">
        <h1 className="text-3xl sm:text-5xl lg:text-6xl font-serif text-ivory tracking-tight leading-[1.14]">
          {config.title}
          {config.italicTitle && (
            <>
              <br />
              <span className="italic text-marigold font-normal">{config.italicTitle}</span>
            </>
          )}
          {config.afterTitle && (
            <>
              <br />
              <span>{config.afterTitle}</span>
            </>
          )}
        </h1>
        <p className="text-xs sm:text-sm text-muted-warm max-w-2xl mx-auto leading-relaxed font-sans font-light">
          {config.description}
        </p>
      </div>

      {/* Curriculum Banner */}
      <div className="max-w-3xl mx-auto py-2.5 px-4 rounded-xl bg-surface/60 border border-border-warm/60 text-[11px] sm:text-xs text-muted-warm font-sans flex items-center justify-center gap-2">
        <span className="w-2 h-2 rounded-full bg-teal" />
        <span className="font-mono text-ivory/80 uppercase tracking-wider">{config.tagline}</span>
      </div>

      {/* Continue Learning / Pick up where you left off */}
      {recentConv && onContinueLearning && (
        <div className="max-w-3xl mx-auto p-4 rounded-xl bg-surface border border-marigold/40 hover:border-marigold/70 transition-all duration-150 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 shadow-xs text-left">
          <div className="space-y-1">
            <div className="flex items-center gap-2">
              <span className="text-[10px] font-mono font-bold tracking-wider px-2 py-0.5 rounded bg-marigold/15 text-marigold border border-marigold/30">
                RECENT LEARNING
              </span>
              <span className="text-[11px] font-mono text-muted-warm">
                {recentConv.message_count} {recentConv.message_count === 1 ? "inquiry" : "inquiries"} recorded
              </span>
            </div>
            <h4 className="text-xs sm:text-sm font-serif font-medium text-ivory line-clamp-1">
              {recentConv.title}
            </h4>
          </div>

          <button
            type="button"
            onClick={() => onContinueLearning(recentConv.conversation_id)}
            className="inline-flex items-center gap-1.5 px-3.5 py-1.5 rounded-lg text-xs font-medium bg-marigold text-espresso hover:bg-marigold/90 transition-all font-sans cursor-pointer shrink-0 select-none shadow-xs"
          >
            <span>Pick up where you left off</span>
            <ArrowRight className="w-3.5 h-3.5" />
          </button>
        </div>
      )}

      {/* Section Divider: Prompts */}
      <div className="pt-3">
        <div className="flex items-center justify-between max-w-4xl mx-auto pb-3 text-[11px] uppercase tracking-widest text-muted-warm font-mono border-b border-border-warm/50">
          <span className="font-semibold text-ivory/70">Curated Learning Inquiries</span>
          <span className="text-muted-warm/70 lowercase font-sans text-[11px]">Click to start conversation</span>
        </div>

        {/* Prompts Grid */}
        <div className={`grid grid-cols-1 md:grid-cols-2 ${config.prompts.length > 4 ? "lg:grid-cols-3" : "lg:grid-cols-2"} gap-3.5 mt-4 text-left`}>
          {config.prompts.map((item, idx) => {
            const isTeal = item.tagTheme === "teal";
            const isTerracotta = item.tagTheme === "terracotta";

            return (
              <button
                key={idx}
                type="button"
                onClick={() => onSelectPrompt(item.prompt)}
                className="p-4 rounded-xl bg-surface border border-border-warm hover:border-marigold/40 hover:bg-elevated transition-all duration-150 text-left group cursor-pointer flex flex-col justify-between min-h-[120px] shadow-xs relative"
              >
                <div>
                  <div className="flex items-center justify-between mb-2">
                    <span
                      className={`text-[10px] font-mono font-bold tracking-wider px-2 py-0.5 rounded ${
                        isTeal
                          ? "bg-teal/20 text-teal border border-teal/40"
                          : isTerracotta
                          ? "bg-terracotta/20 text-terracotta border border-terracotta/40"
                          : "bg-marigold/15 text-marigold border border-marigold/30"
                      }`}
                    >
                      {item.tag}
                    </span>
                    <ArrowUpRight className="w-3.5 h-3.5 text-muted-warm group-hover:text-marigold group-hover:translate-x-0.5 group-hover:-translate-y-0.5 transition-all" />
                  </div>

                  <h3 className="text-xs sm:text-[13px] font-serif font-medium text-ivory group-hover:text-white leading-snug">
                    {item.title}
                  </h3>
                </div>

                <p className="text-[10px] sm:text-[11px] font-mono text-muted-warm/80 mt-3 pt-2 border-t border-border-warm/40">
                  {item.subtext}
                </p>
              </button>
            );
          })}
        </div>
      </div>
    </div>
  );
};
