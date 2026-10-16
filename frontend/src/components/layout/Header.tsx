import React, { useEffect, useState } from "react";
import { PlusCircle, Menu } from "lucide-react";
import { apiClient } from "../../api/client";
import type { TutorSectionId } from "../../api/types";

interface HeaderProps {
  displayName: string;
  userId: string;
  activeSection?: TutorSectionId;
  onOpenProfile: () => void;
  onNewChat: () => void;
  onToggleSidebar: () => void;
}

const SECTION_TITLES: Record<string, string> = {
  general: "GENERAL CHAT",
  equity: "EQUITY TUTOR",
  derivatives: "DERIVATIVES TUTOR",
  personal_finance: "PERSONAL FINANCE",
  crypto: "CRYPTO TUTOR",
  portfolio: "PORTFOLIO TUTOR",
  news: "MARKET NEWS",
  quiz: "QUIZ & CHALLENGE",
  onboarding: "SYSTEM GUIDE",
};

export const Header: React.FC<HeaderProps> = ({
  displayName,
  userId,
  activeSection = "general",
  onOpenProfile,
  onNewChat,
  onToggleSidebar,
}) => {
  const [backendHealthy, setBackendHealthy] = useState<boolean | null>(null);

  useEffect(() => {
    let mounted = true;
    const check = async () => {
      try {
        const health = await apiClient.checkHealth();
        if (mounted) setBackendHealthy(health.status === "healthy" || health.status === "ok");
      } catch {
        if (mounted) setBackendHealthy(false);
      }
    };
    check();
    const timer = setInterval(check, 30000);
    return () => {
      mounted = false;
      clearInterval(timer);
    };
  }, []);

  return (
    <header className="h-14 border-b border-border-warm bg-espresso/90 backdrop-blur-md px-4 flex items-center justify-between z-10 shrink-0">
      <div className="flex items-center gap-3">
        <button
          type="button"
          onClick={onToggleSidebar}
          className="p-1.5 rounded-lg text-muted-warm hover:text-ivory hover:bg-surface transition-colors cursor-pointer"
          title="Toggle Navigation"
        >
          <Menu className="w-5 h-5" />
        </button>

        {/* Active Tutor Section Badge */}
        <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-surface border border-border-warm text-xs">
          <span className="w-1.5 h-1.5 rounded-full bg-teal shrink-0 animate-pulse" />
          <span className="text-[11px] font-mono font-medium tracking-wide text-ivory/90">
            {SECTION_TITLES[activeSection] || "FINANCIAL LEARNING"}
          </span>
        </div>
      </div>

      <div className="flex items-center gap-2 sm:gap-3">
        {/* Backend Health Status Indicator */}
        <div
          className="hidden sm:flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[11px] font-sans border bg-surface border-border-warm"
          title={backendHealthy ? "Backend API online" : backendHealthy === false ? "Backend API offline" : "Checking connection..."}
        >
          {backendHealthy === true ? (
            <>
              <span className="w-1.5 h-1.5 rounded-full bg-teal" />
              <span className="text-muted-warm">System Online</span>
            </>
          ) : backendHealthy === false ? (
            <>
              <span className="w-1.5 h-1.5 rounded-full bg-terracotta" />
              <span className="text-terracotta">API Offline</span>
            </>
          ) : (
            <>
              <span className="w-1.5 h-1.5 rounded-full bg-marigold" />
              <span className="text-muted-warm">Checking...</span>
            </>
          )}
        </div>

        {/* New Chat Button */}
        <button
          type="button"
          onClick={onNewChat}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium text-ivory bg-surface border border-border-warm hover:border-marigold/50 hover:bg-elevated transition-all cursor-pointer"
          title="Start fresh conversation"
        >
          <PlusCircle className="w-3.5 h-3.5 text-marigold" />
          <span className="hidden sm:inline">New Conversation</span>
        </button>

        {/* Learner Profile / Identity Button */}
        <button
          type="button"
          onClick={onOpenProfile}
          className="flex items-center gap-2 p-1.5 sm:px-3 sm:py-1.5 rounded-lg text-xs font-medium text-ivory bg-surface border border-border-warm hover:bg-elevated hover:border-marigold/40 transition-colors cursor-pointer"
          title={`User: ${userId}`}
        >
          <div className="w-5 h-5 rounded-full bg-marigold flex items-center justify-center text-[10px] font-bold text-espresso">
            {displayName.slice(0, 2).toUpperCase()}
          </div>
          <span className="hidden sm:inline truncate max-w-[120px]">{displayName}</span>
        </button>
      </div>
    </header>
  );
};
