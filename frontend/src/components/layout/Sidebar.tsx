import React, { useEffect, useState } from "react";
import {
  X,
  Plus,
  Compass,
  ChevronRight,
  TrendingUp,
  Coins,
  Layers,
  Newspaper,
  Settings,
  MessageSquare,
  Trash2,
  Edit2,
  Check,
  Sparkles,
  Briefcase,
  HelpCircle,
  Calculator,
} from "lucide-react";
import { apiClient } from "../../api/client";
import type { ConversationSummary, SystemCapability, TutorSectionId } from "../../api/types";

interface SidebarProps {
  isOpen: boolean;
  onClose: () => void;
  onSelectPrompt: (prompt: string) => void;
  onOpenProfile: () => void;
  userId: string;
  displayName?: string;
  activeConversationId?: string | null;
  activeSection?: TutorSectionId;
  onSelectSection?: (sectionId: TutorSectionId) => void;
  onSelectConversation?: (conversationId: string) => void;
  onNewChat?: (domain?: TutorSectionId) => void;
  refreshTrigger?: number;
}

interface TutorNavItem {
  id: TutorSectionId;
  label: string;
  shortLabel: string;
  icon: React.ComponentType<{ className?: string }>;
  tag: string;
  tagColor: string;
}

const TUTOR_NAV_ITEMS: TutorNavItem[] = [
  { id: "general", label: "General Chat", shortLabel: "General", icon: Sparkles, tag: "ALL", tagColor: "text-marigold" },
  { id: "equity", label: "Equity Tutor", shortLabel: "Equity", icon: TrendingUp, tag: "NSE/BSE", tagColor: "text-teal" },
  { id: "derivatives", label: "Derivatives Tutor", shortLabel: "F&O", icon: Layers, tag: "F&O", tagColor: "text-terracotta" },
  { id: "personal_finance", label: "Personal Finance", shortLabel: "Wealth", icon: Calculator, tag: "SIP", tagColor: "text-marigold" },
  { id: "crypto", label: "Crypto Tutor", shortLabel: "Crypto", icon: Coins, tag: "INR", tagColor: "text-terracotta" },
  { id: "portfolio", label: "Portfolio Tutor", shortLabel: "Portfolio", icon: Briefcase, tag: "RISK", tagColor: "text-teal" },
  { id: "news", label: "Market News", shortLabel: "News", icon: Newspaper, tag: "MACRO", tagColor: "text-ivory" },
  { id: "quiz", label: "Quiz & Challenge", shortLabel: "Quiz", icon: HelpCircle, tag: "TEST", tagColor: "text-teal" },
  { id: "onboarding", label: "System Guide", shortLabel: "Guide", icon: Compass, tag: "DOCS", tagColor: "text-muted-warm" },
];

const DOMAIN_TAGS: Record<string, { label: string; className: string }> = {
  equity: { label: "EQUITY", className: "bg-teal/15 text-teal border border-teal/30" },
  derivatives: { label: "F&O", className: "bg-terracotta/15 text-terracotta border border-terracotta/30" },
  personal_finance: { label: "WEALTH", className: "bg-marigold/15 text-marigold border border-marigold/30" },
  crypto: { label: "CRYPTO", className: "bg-terracotta/15 text-terracotta border border-terracotta/30" },
  portfolio: { label: "PORTFOLIO", className: "bg-teal/15 text-teal border border-teal/30" },
  news: { label: "NEWS", className: "bg-ivory/10 text-ivory/90 border border-ivory/20" },
  quiz: { label: "QUIZ", className: "bg-marigold/15 text-marigold border border-marigold/30" },
  onboarding: { label: "GUIDE", className: "bg-surface text-muted-warm border border-border-warm" },
  general: { label: "GENERAL", className: "bg-surface text-muted-warm border border-border-warm" },
};

function groupConversationsByDate(conversations: ConversationSummary[]) {
  const groups: Record<string, ConversationSummary[]> = {
    TODAY: [],
    YESTERDAY: [],
    "PREVIOUS 7 DAYS": [],
    OLDER: [],
  };

  const now = new Date();
  const startOfToday = new Date(now.getFullYear(), now.getMonth(), now.getDate()).getTime();
  const startOfYesterday = startOfToday - 24 * 60 * 60 * 1000;
  const startOf7DaysAgo = startOfToday - 7 * 24 * 60 * 60 * 1000;

  for (const conv of conversations) {
    const timeMs = new Date(conv.updated_at || conv.created_at).getTime();
    if (timeMs >= startOfToday) {
      groups.TODAY.push(conv);
    } else if (timeMs >= startOfYesterday) {
      groups.YESTERDAY.push(conv);
    } else if (timeMs >= startOf7DaysAgo) {
      groups["PREVIOUS 7 DAYS"].push(conv);
    } else {
      groups.OLDER.push(conv);
    }
  }

  return Object.entries(groups).filter(([, items]) => items.length > 0);
}

export const Sidebar: React.FC<SidebarProps> = ({
  isOpen,
  onClose,
  onSelectPrompt,
  onOpenProfile,
  userId,
  displayName = "Learner",
  activeConversationId,
  activeSection = "general",
  onSelectSection,
  onSelectConversation,
  onNewChat,
  refreshTrigger,
}) => {
  const [conversations, setConversations] = useState<ConversationSummary[]>([]);
  const [capabilities, setCapabilities] = useState<SystemCapability[]>([]);
  const [viewMode, setViewMode] = useState<"tutors" | "history" | "capabilities">("tutors");
  const [filterByActiveTutor, setFilterByActiveTutor] = useState<boolean>(false);
  const [editingConvId, setEditingConvId] = useState<string | null>(null);
  const [editTitle, setEditTitle] = useState<string>("");

  useEffect(() => {
    let mounted = true;
    const load = async () => {
      try {
        const list = await apiClient.listConversations(userId);
        if (mounted) {
          setConversations(list || []);
        }
      } catch {
        if (mounted) {
          setConversations([]);
        }
      }
    };
    load();
    return () => {
      mounted = false;
    };
  }, [userId, refreshTrigger, activeConversationId]);

  useEffect(() => {
    let mounted = true;
    const fetchCaps = async () => {
      try {
        const caps = await apiClient.getCapabilities();
        if (mounted && Array.isArray(caps) && caps.length > 0) {
          setCapabilities(caps);
        }
      } catch {
        if (mounted) {
          setCapabilities([
            {
              name: "Equity & Stock Analysis",
              domain: "EQUITY",
              description: "Live Indian stock prices (NSE/BSE) with provenance and freshness tracking.",
              example_queries: ["What is Reliance trading at?", "What is an IPO?"],
            },
            {
              name: "Cryptocurrency Analytics",
              domain: "CRYPTO",
              description: "Live crypto prices in INR and USD with 24h market volume via CoinGecko.",
              example_queries: ["What is Bitcoin?", "Show Ethereum price in INR."],
            },
            {
              name: "Personal Finance & SIP",
              domain: "PERSONAL_FINANCE",
              description: "Deterministic SIP, compounding growth, and budgeting formulations.",
              example_queries: ["Explain 50/30/20 budgeting.", "Calculate SIP for ₹5,000/mo over 10 years."],
            },
            {
              name: "Options & Derivatives",
              domain: "DERIVATIVES",
              description: "Payoff simulation, breakeven formulas, and options spread education.",
              example_queries: ["What is a call option?", "Explain Bull Call Spread payoff."],
            },
            {
              name: "Portfolio Stress Testing",
              domain: "PORTFOLIO",
              description: "Simulated portfolio metrics and 'what-if' market stress tests.",
              example_queries: ["Show me my portfolio.", "Simulate a 10% drop in NIFTY."],
            },
            {
              name: "Financial Knowledge Challenge",
              domain: "QUIZ",
              description: "Interactive financial education challenges with grading and explanations.",
              example_queries: ["Give me a quiz on mutual funds.", "Test my knowledge on equities."],
            },
          ]);
        }
      }
    };
    fetchCaps();
    return () => {
      mounted = false;
    };
  }, []);

  const handleDeleteConversation = async (e: React.MouseEvent, convId: string) => {
    e.stopPropagation();
    if (!window.confirm("Delete this conversation and its history?")) return;
    try {
      await apiClient.deleteConversation(convId, userId);
      setConversations((prev) => prev.filter((c) => c.conversation_id !== convId));
      if (activeConversationId === convId && onNewChat) {
        onNewChat(activeSection);
      }
    } catch {
      // Failed to delete
    }
  };

  const handleStartRename = (e: React.MouseEvent, conv: ConversationSummary) => {
    e.stopPropagation();
    setEditingConvId(conv.conversation_id);
    setEditTitle(conv.title);
  };

  const handleSaveRename = async (e: React.MouseEvent | React.FormEvent, convId: string) => {
    e.stopPropagation();
    if (e.type === "submit") (e as React.FormEvent).preventDefault();
    const clean = editTitle.trim();
    if (!clean) {
      setEditingConvId(null);
      return;
    }
    try {
      await apiClient.renameConversation(convId, userId, clean);
      setConversations((prev) =>
        prev.map((c) => (c.conversation_id === convId ? { ...c, title: clean } : c))
      );
    } catch {
      // Ignored
    } finally {
      setEditingConvId(null);
    }
  };

  // Filter conversations for history tab if filterByActiveTutor is on
  const displayedConversations = filterByActiveTutor
    ? conversations.filter(
        (c) => (c.domain || "general").toLowerCase() === activeSection.toLowerCase()
      )
    : conversations;

  const conversationGroups = groupConversationsByDate(displayedConversations);

  const activeTutorNav = TUTOR_NAV_ITEMS.find((t) => t.id === activeSection) || TUTOR_NAV_ITEMS[0];

  return (
    <>
      {/* Mobile Backdrop */}
      {isOpen && (
        <div
          className="fixed inset-0 bg-black/70 z-40 lg:hidden backdrop-blur-xs"
          onClick={onClose}
        />
      )}

      {/* Sidebar Container */}
      <aside
        className={`fixed lg:static top-0 bottom-0 left-0 z-50 bg-espresso border-r border-border-warm flex flex-col transition-all duration-300 ease-in-out ${
          isOpen
            ? "w-[270px] translate-x-0"
            : "-translate-x-full lg:translate-x-0 lg:w-0 lg:overflow-hidden lg:border-r-0"
        }`}
      >
        {/* Sidebar Header */}
        <div className="h-14 border-b border-border-warm px-4 flex items-center justify-between shrink-0">
          <div className="flex items-center gap-2">
            <span className="font-serif font-bold text-base tracking-wider text-ivory">
              FINOVA <span className="font-sans text-[11px] text-marigold font-semibold tracking-normal">AI</span>
            </span>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="p-1 rounded-md text-muted-warm hover:text-ivory hover:bg-surface lg:hidden cursor-pointer"
            title="Close sidebar"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* New Conversation Button */}
        <div className="p-3">
          <button
            type="button"
            onClick={() => {
              if (onNewChat) onNewChat(activeSection);
              if (window.innerWidth < 1024) onClose();
            }}
            className="w-full flex items-center justify-center gap-2 py-2 px-3 rounded-lg bg-surface hover:bg-elevated border border-border-warm hover:border-marigold/50 text-xs font-medium text-ivory transition-all shadow-xs group cursor-pointer"
            title={`Start fresh ${activeTutorNav.shortLabel} conversation`}
          >
            <Plus className="w-4 h-4 text-marigold group-hover:scale-110 transition-transform" />
            <span>New {activeTutorNav.shortLabel} Chat</span>
          </button>
        </div>

        {/* Navigation Tabs: Tutors / History / Capabilities */}
        <div className="flex px-3 border-b border-border-warm/60 pb-2 gap-1 text-[11px]">
          <button
            type="button"
            onClick={() => setViewMode("tutors")}
            className={`flex-1 py-1 px-1.5 rounded-md font-medium transition-colors text-center cursor-pointer ${
              viewMode === "tutors"
                ? "bg-surface text-marigold border border-border-warm"
                : "text-muted-warm hover:text-ivory"
            }`}
          >
            Tutors
          </button>
          <button
            type="button"
            onClick={() => setViewMode("history")}
            className={`flex-1 py-1 px-1.5 rounded-md font-medium transition-colors text-center cursor-pointer ${
              viewMode === "history"
                ? "bg-surface text-marigold border border-border-warm"
                : "text-muted-warm hover:text-ivory"
            }`}
          >
            Chats ({conversations.length})
          </button>
          <button
            type="button"
            onClick={() => setViewMode("capabilities")}
            className={`flex-1 py-1 px-1.5 rounded-md font-medium transition-colors text-center cursor-pointer ${
              viewMode === "capabilities"
                ? "bg-surface text-marigold border border-border-warm"
                : "text-muted-warm hover:text-ivory"
            }`}
          >
            Catalog
          </button>
        </div>

        {/* Navigation Content */}
        <div className="flex-1 overflow-y-auto p-3 space-y-4">
          {/* 1. TUTOR SECTIONS VIEW */}
          {viewMode === "tutors" && (
            <div className="space-y-1.5">
              <span className="text-[10px] font-semibold text-muted-warm/70 tracking-wider px-2 block uppercase">
                Subject Tutors & Labs
              </span>
              <div className="space-y-1 pt-1">
                {TUTOR_NAV_ITEMS.map((tutor) => {
                  const Icon = tutor.icon;
                  const isSelected = activeSection === tutor.id;
                  const countForTutor = conversations.filter(
                    (c) => (c.domain || "general").toLowerCase() === tutor.id
                  ).length;

                  return (
                    <button
                      key={tutor.id}
                      type="button"
                      onClick={() => {
                        if (onSelectSection) onSelectSection(tutor.id);
                        if (window.innerWidth < 1024) onClose();
                      }}
                      className={`w-full text-left py-2 px-2.5 rounded-lg text-xs transition-all flex items-center justify-between cursor-pointer group ${
                        isSelected
                          ? "bg-marigold/10 text-marigold font-medium border border-marigold/30 shadow-xs"
                          : "text-ivory/85 hover:bg-surface hover:text-ivory border border-transparent"
                      }`}
                    >
                      <div className="flex items-center gap-2.5 min-w-0">
                        <Icon
                          className={`w-4 h-4 shrink-0 transition-colors ${
                            isSelected ? "text-marigold" : "text-muted-warm group-hover:text-ivory"
                          }`}
                        />
                        <span className="truncate">{tutor.label}</span>
                      </div>

                      <div className="flex items-center gap-1.5 shrink-0">
                        {countForTutor > 0 && (
                          <span className="text-[10px] font-mono text-muted-warm/70 px-1 rounded">
                            {countForTutor}
                          </span>
                        )}
                        <span className={`text-[9px] font-mono px-1.5 py-0.2 rounded border border-border-warm ${tutor.tagColor}`}>
                          {tutor.tag}
                        </span>
                      </div>
                    </button>
                  );
                })}
              </div>
            </div>
          )}

          {/* 2. CONVERSATION HISTORY VIEW */}
          {viewMode === "history" && (
            <div className="space-y-3">
              {/* Filter toggle */}
              <div className="flex items-center justify-between px-1 pb-1">
                <span className="text-[10px] font-semibold text-muted-warm/70 tracking-wider block uppercase">
                  {filterByActiveTutor ? `${activeTutorNav.shortLabel} Chats` : "All Chats"}
                </span>

                <button
                  type="button"
                  onClick={() => setFilterByActiveTutor((prev) => !prev)}
                  className={`text-[10px] font-mono px-2 py-0.5 rounded cursor-pointer transition-colors border ${
                    filterByActiveTutor
                      ? "bg-marigold/20 text-marigold border-marigold/40"
                      : "bg-surface text-muted-warm border-border-warm hover:text-ivory"
                  }`}
                  title="Filter conversations by active tutor"
                >
                  {filterByActiveTutor ? "Filter: Active" : "Filter: All"}
                </button>
              </div>

              {conversationGroups.length === 0 ? (
                <div className="py-8 text-center space-y-2">
                  <MessageSquare className="w-6 h-6 text-muted-warm/40 mx-auto" />
                  <p className="text-xs text-muted-warm">
                    {filterByActiveTutor
                      ? `No ${activeTutorNav.label} chats yet.`
                      : "No conversation history yet."}
                  </p>
                  <p className="text-[11px] text-muted-warm/60 font-light">
                    Send an inquiry to start a dialogue!
                  </p>
                </div>
              ) : (
                conversationGroups.map(([label, items]) => (
                  <div key={label} className="space-y-1">
                    <span className="text-[10px] font-semibold text-muted-warm/70 tracking-wider px-2 block uppercase">
                      {label}
                    </span>
                    <div className="space-y-0.5">
                      {items.map((conv) => {
                        const isActive = activeConversationId === conv.conversation_id;
                        const isEditing = editingConvId === conv.conversation_id;
                        const domainSlug = (conv.domain || "general").toLowerCase();
                        const tagInfo = DOMAIN_TAGS[domainSlug] || DOMAIN_TAGS.general;

                        if (isEditing) {
                          return (
                            <form
                              key={conv.conversation_id}
                              onSubmit={(e) => handleSaveRename(e, conv.conversation_id)}
                              className="flex items-center gap-1 p-1 bg-surface rounded-lg border border-marigold/50"
                            >
                              <input
                                type="text"
                                value={editTitle}
                                onChange={(e) => setEditTitle(e.target.value)}
                                onKeyDown={(e) => {
                                  if (e.key === "Escape") setEditingConvId(null);
                                }}
                                className="flex-1 bg-transparent text-xs text-ivory px-1.5 py-0.5 focus:outline-none"
                                autoFocus
                              />
                              <button
                                type="button"
                                onClick={(e) => handleSaveRename(e, conv.conversation_id)}
                                className="p-1 text-marigold hover:text-ivory cursor-pointer"
                                title="Save"
                              >
                                <Check className="w-3.5 h-3.5" />
                              </button>
                              <button
                                type="button"
                                onClick={() => setEditingConvId(null)}
                                className="p-1 text-muted-warm hover:text-ivory cursor-pointer"
                                title="Cancel"
                              >
                                <X className="w-3.5 h-3.5" />
                              </button>
                            </form>
                          );
                        }

                        return (
                          <div
                            key={conv.conversation_id}
                            onClick={() => {
                              if (onSelectConversation) {
                                onSelectConversation(conv.conversation_id);
                              }
                              if (window.innerWidth < 1024) onClose();
                            }}
                            className={`group relative w-full text-left py-2 px-2.5 rounded-lg text-xs transition-all flex items-center justify-between cursor-pointer ${
                              isActive
                                ? "bg-marigold/10 text-marigold font-medium border border-marigold/25"
                                : "text-ivory/85 hover:bg-surface hover:text-ivory border border-transparent"
                            }`}
                          >
                            <div className="flex items-center gap-2 min-w-0 flex-1 pr-1.5">
                              <span
                                className={`text-[8px] font-mono font-semibold px-1 py-0.2 rounded shrink-0 ${tagInfo.className}`}
                              >
                                {tagInfo.label}
                              </span>
                              <span className="truncate">{conv.title}</span>
                            </div>

                            {/* Actions on hover */}
                            <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                              <button
                                type="button"
                                onClick={(e) => handleStartRename(e, conv)}
                                className="p-1 text-muted-warm hover:text-marigold rounded transition-colors cursor-pointer"
                                title="Rename conversation"
                              >
                                <Edit2 className="w-3 h-3" />
                              </button>
                              <button
                                type="button"
                                onClick={(e) => handleDeleteConversation(e, conv.conversation_id)}
                                className="p-1 text-muted-warm hover:text-terracotta rounded transition-colors cursor-pointer"
                                title="Delete conversation"
                              >
                                <Trash2 className="w-3 h-3" />
                              </button>
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  </div>
                ))
              )}
            </div>
          )}

          {/* 3. CAPABILITIES VIEW */}
          {viewMode === "capabilities" && (
            <div className="space-y-2.5">
              <span className="text-[10px] font-semibold text-muted-warm/70 tracking-wider px-1 block uppercase">
                Agent Disciplines
              </span>
              {capabilities.map((cap, idx) => (
                <div
                  key={idx}
                  className="p-2.5 rounded-lg bg-surface border border-border-warm hover:border-border-warm/90 transition-colors"
                >
                  <div className="flex items-center gap-2 mb-1">
                    <Compass className="w-3.5 h-3.5 text-marigold shrink-0" />
                    <h4 className="text-xs font-semibold text-ivory">
                      {cap.name}
                    </h4>
                  </div>
                  <p className="text-[11px] text-muted-warm leading-relaxed mb-2">
                    {cap.description}
                  </p>
                  {cap.example_queries && cap.example_queries.length > 0 && (
                    <div className="space-y-1">
                      {cap.example_queries.map((eq, qIdx) => (
                        <button
                          key={qIdx}
                          type="button"
                          onClick={() => {
                            onSelectPrompt(eq);
                            if (window.innerWidth < 1024) onClose();
                          }}
                          className="w-full text-left p-1.5 rounded bg-espresso hover:bg-elevated text-[10px] text-ivory/80 hover:text-marigold border border-border-warm/80 transition-colors flex items-center justify-between group cursor-pointer"
                        >
                          <span className="truncate">{eq}</span>
                          <ChevronRight className="w-3 h-3 text-muted-warm group-hover:text-marigold shrink-0" />
                        </button>
                      ))}
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Profile / Bottom Bar */}
        <div className="p-3 border-t border-border-warm bg-espresso flex items-center justify-between shrink-0">
          <button
            type="button"
            onClick={onOpenProfile}
            title={`${displayName} (${userId})`}
            className="flex items-center gap-2.5 text-left flex-1 min-w-0 p-1 rounded-lg hover:bg-surface transition-colors cursor-pointer group"
          >
            <div className="w-8 h-8 rounded-full bg-marigold text-espresso font-bold text-xs flex items-center justify-center shrink-0 shadow-xs">
              {displayName.slice(0, 2).toUpperCase()}
            </div>
            <div className="min-w-0 flex-1">
              <span className="text-xs font-medium text-ivory block truncate group-hover:text-marigold transition-colors">
                {displayName}
              </span>
              <span className="text-[10px] text-muted-warm flex items-center gap-1 leading-none mt-0.5">
                <span className="w-1.5 h-1.5 rounded-full bg-teal" />
                <span>Learner Profile</span>
              </span>
            </div>
          </button>

          <button
            type="button"
            onClick={onOpenProfile}
            className="p-1.5 rounded-lg text-muted-warm hover:text-marigold hover:bg-surface transition-colors shrink-0 ml-1 cursor-pointer"
            title="Learner Identity & Memory Settings"
          >
            <Settings className="w-4 h-4" />
          </button>
        </div>
      </aside>
    </>
  );
};
