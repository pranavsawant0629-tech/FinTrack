import React, { useEffect, useState, useCallback } from "react";
import {
  X,
  User,
  Database,
  RefreshCw,
  CheckCircle2,
  Trash2,
  Sliders,
  Sun,
  Moon,
  Monitor,
  Info,
  AlertTriangle,
  Copy,
  BookOpen,
  Layers,
  Sparkles,
  MessageSquare,
} from "lucide-react";
import { apiClient } from "../../api/client";
import type { MemoryRecord } from "../../api/types";
import { useTheme } from "../../hooks/useTheme";

interface ProfileModalProps {
  isOpen: boolean;
  onClose: () => void;
  userId: string;
  displayName: string;
  setDisplayName: (name: string) => void;
  onClearAllConversations?: () => void;
}

type TabType = "profile" | "memory" | "data" | "appearance" | "about";

const AVAILABLE_GOALS = [
  "Investing Basics",
  "Understand Indian Markets",
  "Derivatives & Options",
  "Personal Finance & SIPs",
  "Finance Exam & Certification Prep",
  "Portfolio Risk Management",
];

const AVAILABLE_INTERESTS = [
  "Equities",
  "Derivatives",
  "Mutual Funds",
  "Personal Finance",
  "Crypto",
  "Macro Markets",
];

export const ProfileModal: React.FC<ProfileModalProps> = ({
  isOpen,
  onClose,
  userId,
  displayName,
  setDisplayName,
  onClearAllConversations,
}) => {
  const { theme, setTheme } = useTheme();

  // Active Tab
  const [activeTab, setActiveTab] = useState<TabType>("profile");

  // Display Name State (derived during render if prop changes)
  const [localName, setLocalName] = useState(displayName);
  const [prevDisplayName, setPrevDisplayName] = useState(displayName);
  if (displayName !== prevDisplayName) {
    setPrevDisplayName(displayName);
    setLocalName(displayName);
  }
  const [nameSaved, setNameSaved] = useState(false);

  // Profile & Personalization State
  const [learningLevel, setLearningLevel] = useState<"beginner" | "intermediate" | "advanced">("beginner");
  const [selectedGoals, setSelectedGoals] = useState<string[]>([]);
  const [selectedInterests, setSelectedInterests] = useState<string[]>([]);
  const [explanationStyle, setExplanationStyle] = useState<"concise" | "detailed">("concise");
  const [isLoadingProfile, setIsLoadingProfile] = useState(false);
  const [isSavingProfile, setIsSavingProfile] = useState(false);
  const [profileSaveMessage, setProfileSaveMessage] = useState<{ text: string; type: "success" | "error" } | null>(null);

  // Long-Term Memory State
  const [memories, setMemories] = useState<MemoryRecord[]>([]);
  const [isLoadingMemories, setIsLoadingMemories] = useState(false);
  const [memoryMessage, setMemoryMessage] = useState<{ text: string; type: "success" | "error" } | null>(null);
  const [isClearingMemory, setIsClearingMemory] = useState(false);
  const [confirmClearMemory, setConfirmClearMemory] = useState(false);

  // Data / Conversations State
  const [isClearingConversations, setIsClearingConversations] = useState(false);
  const [confirmClearConversations, setConfirmClearConversations] = useState(false);
  const [dataMessage, setDataMessage] = useState<{ text: string; type: "success" | "error" } | null>(null);
  const [copiedUserId, setCopiedUserId] = useState(false);

  // Load Profile from backend
  const loadProfile = useCallback(async () => {
    setIsLoadingProfile(true);
    try {
      const res = await apiClient.getPersonalizationProfile(userId);
      if (res.learning_level) {
        setLearningLevel(res.learning_level);
      }
      setSelectedGoals(res.learning_goals || []);
      setSelectedInterests(res.interests || []);
      if (res.preferences?.explanation_style === "detailed") {
        setExplanationStyle("detailed");
      } else {
        setExplanationStyle("concise");
      }
    } catch {
      // Gracefully degrade if profile fetch fails
    } finally {
      setIsLoadingProfile(false);
    }
  }, [userId]);

  // Load raw memories from backend
  const loadMemories = useCallback(async () => {
    setIsLoadingMemories(true);
    try {
      const res = await apiClient.getMemories(userId);
      setMemories(res.memories || []);
    } catch {
      setMemories([]);
    } finally {
      setIsLoadingMemories(false);
    }
  }, [userId]);

  // Load data asynchronously when modal opens
  useEffect(() => {
    if (!isOpen) return;

    const timer = setTimeout(() => {
      void loadProfile();
      void loadMemories();
      setConfirmClearMemory(false);
      setConfirmClearConversations(false);
      setProfileSaveMessage(null);
      setMemoryMessage(null);
      setDataMessage(null);
    }, 0);

    return () => clearTimeout(timer);
  }, [isOpen, loadProfile, loadMemories]);

  // Keyboard accessibility: Escape to close
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape" && isOpen) {
        onClose();
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [isOpen, onClose]);

  // Save Display Name
  const handleSaveName = (e: React.FormEvent) => {
    e.preventDefault();
    const clean = localName.trim() || "Learner";
    setDisplayName(clean);
    setNameSaved(true);
    setTimeout(() => setNameSaved(false), 2000);
  };

  // Toggle Goal Selection
  const toggleGoal = (goal: string) => {
    setSelectedGoals((prev) =>
      prev.includes(goal) ? prev.filter((g) => g !== goal) : [...prev, goal]
    );
  };

  // Toggle Interest Selection
  const toggleInterest = (interest: string) => {
    setSelectedInterests((prev) =>
      prev.includes(interest) ? prev.filter((i) => i !== interest) : [...prev, interest]
    );
  };

  // Save Learning Preferences
  const handleSavePreferences = async () => {
    setIsSavingProfile(true);
    setProfileSaveMessage(null);
    try {
      const updated = await apiClient.updatePersonalizationProfile({
        user_id: userId,
        learning_level: learningLevel,
        learning_goals: selectedGoals,
        interests: selectedInterests,
        preferences: { explanation_style: explanationStyle },
      });
      if (updated.learning_level) setLearningLevel(updated.learning_level);
      setSelectedGoals(updated.learning_goals || []);
      setSelectedInterests(updated.interests || []);
      setProfileSaveMessage({ text: "Learning preferences saved to persistent memory.", type: "success" });
      void loadMemories();
    } catch (err: any) {
      setProfileSaveMessage({
        text: err?.message || "Failed to save learning preferences. Please try again.",
        type: "error",
      });
    } finally {
      setIsSavingProfile(false);
    }
  };

  // Delete Individual Memory
  const handleDeleteMemory = async (memoryId: string) => {
    try {
      await apiClient.deleteMemory(userId, memoryId);
      setMemories((prev) => prev.filter((m) => m.memory_id !== memoryId));
      void loadProfile();
    } catch (err: any) {
      setMemoryMessage({ text: `Failed to delete memory item: ${err.message}`, type: "error" });
    }
  };

  // Clear All Learner Memories
  const handleClearAllMemories = async () => {
    setIsClearingMemory(true);
    setMemoryMessage(null);
    try {
      const res = await apiClient.clearMemories(userId);
      setMemories([]);
      setConfirmClearMemory(false);
      setMemoryMessage({
        text: `Successfully cleared ${res.deleted_count ?? 0} educational memories. Conversation history remains intact.`,
        type: "success",
      });
      void loadProfile();
    } catch (err: any) {
      setMemoryMessage({
        text: `Failed to clear memory: ${err?.message || "Unknown error"}`,
        type: "error",
      });
    } finally {
      setIsClearingMemory(false);
    }
  };

  // Clear All Conversations
  const handleClearAllConversations = async () => {
    setIsClearingConversations(true);
    setDataMessage(null);
    try {
      const res = await apiClient.clearAllConversations(userId);
      setConfirmClearConversations(false);
      setDataMessage({
        text: `Cleared ${res.deleted_count ?? 0} conversations from history. Learner memory was not touched.`,
        type: "success",
      });
      if (onClearAllConversations) {
        onClearAllConversations();
      }
    } catch (err: any) {
      setDataMessage({
        text: `Failed to clear conversations: ${err?.message || "Unknown error"}`,
        type: "error",
      });
    } finally {
      setIsClearingConversations(false);
    }
  };

  // Copy User ID
  const handleCopyUserId = () => {
    void navigator.clipboard.writeText(userId);
    setCopiedUserId(true);
    setTimeout(() => setCopiedUserId(false), 2000);
  };

  if (!isOpen) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-3 sm:p-5 bg-espresso/80 backdrop-blur-xs animate-in fade-in duration-200"
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
      role="dialog"
      aria-modal="true"
      aria-label="Profile and Settings"
    >
      <div className="bg-surface border border-border-warm rounded-2xl w-full max-w-2xl max-h-[90vh] flex flex-col overflow-hidden shadow-2xl animate-in zoom-in-95 duration-200">
        {/* Header */}
        <div className="px-5 py-4 border-b border-border-warm flex items-center justify-between bg-elevated shrink-0">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-lg bg-marigold/15 border border-marigold/30 flex items-center justify-center text-marigold">
              <Sliders className="w-4 h-4" />
            </div>
            <div>
              <h2 className="font-serif font-semibold text-ivory text-base">
                Profile & Settings
              </h2>
              <p className="text-[11px] text-muted-warm font-sans">
                Identity, learning personalization, and local memory controls
              </p>
            </div>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="p-1.5 rounded-lg text-muted-warm hover:text-ivory hover:bg-surface transition-colors cursor-pointer"
            aria-label="Close settings"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Tab Navigation */}
        <div className="flex border-b border-border-warm bg-elevated/50 px-3 overflow-x-auto shrink-0 scrollbar-none">
          <button
            type="button"
            onClick={() => setActiveTab("profile")}
            className={`flex items-center gap-1.5 px-3.5 py-2.5 text-xs font-medium border-b-2 transition-colors whitespace-nowrap cursor-pointer ${
              activeTab === "profile"
                ? "border-marigold text-marigold font-semibold"
                : "border-transparent text-muted-warm hover:text-ivory"
            }`}
          >
            <User className="w-3.5 h-3.5" />
            <span>Profile & Learning</span>
          </button>

          <button
            type="button"
            onClick={() => setActiveTab("memory")}
            className={`flex items-center gap-1.5 px-3.5 py-2.5 text-xs font-medium border-b-2 transition-colors whitespace-nowrap cursor-pointer ${
              activeTab === "memory"
                ? "border-marigold text-marigold font-semibold"
                : "border-transparent text-muted-warm hover:text-ivory"
            }`}
          >
            <Database className="w-3.5 h-3.5" />
            <span>Learner Memory</span>
            {memories.length > 0 && (
              <span className="text-[10px] px-1.5 py-0.2 rounded-full bg-marigold/20 text-marigold font-mono">
                {memories.length}
              </span>
            )}
          </button>

          <button
            type="button"
            onClick={() => setActiveTab("data")}
            className={`flex items-center gap-1.5 px-3.5 py-2.5 text-xs font-medium border-b-2 transition-colors whitespace-nowrap cursor-pointer ${
              activeTab === "data"
                ? "border-marigold text-marigold font-semibold"
                : "border-transparent text-muted-warm hover:text-ivory"
            }`}
          >
            <MessageSquare className="w-3.5 h-3.5" />
            <span>History & Data</span>
          </button>

          <button
            type="button"
            onClick={() => setActiveTab("appearance")}
            className={`flex items-center gap-1.5 px-3.5 py-2.5 text-xs font-medium border-b-2 transition-colors whitespace-nowrap cursor-pointer ${
              activeTab === "appearance"
                ? "border-marigold text-marigold font-semibold"
                : "border-transparent text-muted-warm hover:text-ivory"
            }`}
          >
            <Sun className="w-3.5 h-3.5" />
            <span>Appearance</span>
          </button>

          <button
            type="button"
            onClick={() => setActiveTab("about")}
            className={`flex items-center gap-1.5 px-3.5 py-2.5 text-xs font-medium border-b-2 transition-colors whitespace-nowrap cursor-pointer ${
              activeTab === "about"
                ? "border-marigold text-marigold font-semibold"
                : "border-transparent text-muted-warm hover:text-ivory"
            }`}
          >
            <Info className="w-3.5 h-3.5" />
            <span>About</span>
          </button>
        </div>

        {/* Tab Body */}
        <div className="flex-1 overflow-y-auto p-5 space-y-6">
          {/* ========================================================
              TAB 1: PROFILE & LEARNING (9A & 9B)
             ======================================================== */}
          {activeTab === "profile" && (
            <div className="space-y-6">
              {isLoadingProfile && (
                <div className="flex items-center gap-2 p-2.5 rounded-lg bg-elevated/60 border border-border-warm text-xs text-muted-warm font-sans animate-in fade-in">
                  <RefreshCw className="w-3.5 h-3.5 animate-spin text-marigold" />
                  <span>Loading personalized preferences from memory...</span>
                </div>
              )}

              {/* Display Name Section */}
              <div className="bg-elevated p-4 rounded-xl border border-border-warm space-y-3">
                <div className="flex items-center justify-between">
                  <div>
                    <h3 className="text-xs font-semibold text-ivory flex items-center gap-1.5 font-sans">
                      <User className="w-3.5 h-3.5 text-marigold" />
                      Display Name & Alias
                    </h3>
                    <p className="text-[11px] text-muted-warm font-sans mt-0.5">
                      How Finova greets you across sessions and learning prompts.
                    </p>
                  </div>
                </div>

                <form onSubmit={handleSaveName} className="flex gap-2">
                  <input
                    type="text"
                    value={localName}
                    onChange={(e) => setLocalName(e.target.value)}
                    placeholder="Enter your name"
                    maxLength={50}
                    className="flex-1 bg-surface border border-border-warm rounded-lg px-3 py-2 text-xs text-ivory placeholder-muted-warm/50 focus:outline-none focus:border-marigold font-sans"
                  />
                  <button
                    type="submit"
                    className="px-4 py-2 rounded-lg bg-marigold hover:bg-marigold-hover text-espresso text-xs font-semibold transition-colors cursor-pointer shadow-xs active:scale-95 shrink-0"
                  >
                    Save Name
                  </button>
                </form>

                {nameSaved && (
                  <p className="text-[11px] text-teal flex items-center gap-1 font-sans animate-in fade-in">
                    <CheckCircle2 className="w-3.5 h-3.5" /> Display name saved!
                  </p>
                )}
              </div>

              {/* Learning Level Selection */}
              <div className="space-y-3">
                <div>
                  <h3 className="text-xs font-semibold text-ivory flex items-center gap-1.5 font-sans">
                    <BookOpen className="w-3.5 h-3.5 text-marigold" />
                    Instructional Learning Level
                  </h3>
                  <p className="text-[11px] text-muted-warm font-sans mt-0.5">
                    Calibrates the pedagogical tone of explanations. Does not change numerical facts or calculations.
                  </p>
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-3 gap-2.5">
                  <button
                    type="button"
                    onClick={() => setLearningLevel("beginner")}
                    className={`p-3 rounded-xl border text-left transition-all cursor-pointer ${
                      learningLevel === "beginner"
                        ? "bg-elevated border-marigold shadow-xs ring-1 ring-marigold/30"
                        : "bg-surface border-border-warm hover:border-border-warm/80 hover:bg-elevated/40"
                    }`}
                  >
                    <div className="flex items-center justify-between mb-1">
                      <span className="text-xs font-serif font-bold text-ivory">Beginner</span>
                      {learningLevel === "beginner" && <CheckCircle2 className="w-3.5 h-3.5 text-marigold" />}
                    </div>
                    <p className="text-[10px] text-muted-warm leading-relaxed">
                      Intuitive analogies, core vocabulary, and plain-language definitions without heavy jargon.
                    </p>
                  </button>

                  <button
                    type="button"
                    onClick={() => setLearningLevel("intermediate")}
                    className={`p-3 rounded-xl border text-left transition-all cursor-pointer ${
                      learningLevel === "intermediate"
                        ? "bg-elevated border-marigold shadow-xs ring-1 ring-marigold/30"
                        : "bg-surface border-border-warm hover:border-border-warm/80 hover:bg-elevated/40"
                    }`}
                  >
                    <div className="flex items-center justify-between mb-1">
                      <span className="text-xs font-serif font-bold text-ivory">Intermediate</span>
                      {learningLevel === "intermediate" && <CheckCircle2 className="w-3.5 h-3.5 text-marigold" />}
                    </div>
                    <p className="text-[10px] text-muted-warm leading-relaxed">
                      Structured market mechanics, standard terminology, and practical trading examples.
                    </p>
                  </button>

                  <button
                    type="button"
                    onClick={() => setLearningLevel("advanced")}
                    className={`p-3 rounded-xl border text-left transition-all cursor-pointer ${
                      learningLevel === "advanced"
                        ? "bg-elevated border-marigold shadow-xs ring-1 ring-marigold/30"
                        : "bg-surface border-border-warm hover:border-border-warm/80 hover:bg-elevated/40"
                    }`}
                  >
                    <div className="flex items-center justify-between mb-1">
                      <span className="text-xs font-serif font-bold text-ivory">Advanced</span>
                      {learningLevel === "advanced" && <CheckCircle2 className="w-3.5 h-3.5 text-marigold" />}
                    </div>
                    <p className="text-[10px] text-muted-warm leading-relaxed">
                      Technically rigorous explanations with quantitative formulas and institutional edge cases.
                    </p>
                  </button>
                </div>
              </div>

              {/* Learning Goals Selection */}
              <div className="space-y-3">
                <div>
                  <h3 className="text-xs font-semibold text-ivory flex items-center gap-1.5 font-sans">
                    <Sparkles className="w-3.5 h-3.5 text-marigold" />
                    Learning Objectives
                  </h3>
                  <p className="text-[11px] text-muted-warm font-sans mt-0.5">
                    Select topics you wish to master. Finova tailors example domains and follow-up suggestions accordingly.
                  </p>
                </div>

                <div className="flex flex-wrap gap-2">
                  {AVAILABLE_GOALS.map((goal) => {
                    const isSelected = selectedGoals.includes(goal);
                    return (
                      <button
                        key={goal}
                        type="button"
                        onClick={() => toggleGoal(goal)}
                        className={`px-3 py-1.5 rounded-full text-xs font-sans transition-all cursor-pointer border ${
                          isSelected
                            ? "bg-marigold/15 border-marigold text-marigold font-medium shadow-xs"
                            : "bg-elevated border-border-warm text-muted-warm hover:text-ivory hover:border-border-warm/90"
                        }`}
                      >
                        {isSelected && <span className="mr-1">✓</span>}
                        {goal}
                      </button>
                    );
                  })}
                </div>
              </div>

              {/* Primary Interests Selection */}
              <div className="space-y-3">
                <div>
                  <h3 className="text-xs font-semibold text-ivory flex items-center gap-1.5 font-sans">
                    <Layers className="w-3.5 h-3.5 text-marigold" />
                    Asset & Topic Interests
                  </h3>
                  <p className="text-[11px] text-muted-warm font-sans mt-0.5">
                    Preferred financial areas for real-time market data cards and curriculum questions.
                  </p>
                </div>

                <div className="flex flex-wrap gap-2">
                  {AVAILABLE_INTERESTS.map((interest) => {
                    const isSelected = selectedInterests.includes(interest);
                    return (
                      <button
                        key={interest}
                        type="button"
                        onClick={() => toggleInterest(interest)}
                        className={`px-3 py-1.5 rounded-full text-xs font-sans transition-all cursor-pointer border ${
                          isSelected
                            ? "bg-teal/20 border-teal text-teal font-medium shadow-xs"
                            : "bg-elevated border-border-warm text-muted-warm hover:text-ivory hover:border-border-warm/90"
                        }`}
                      >
                        {isSelected && <span className="mr-1">✓</span>}
                        {interest}
                      </button>
                    );
                  })}
                </div>
              </div>

              {/* Explanation Style Preference */}
              <div className="space-y-3">
                <div>
                  <h3 className="text-xs font-semibold text-ivory flex items-center gap-1.5 font-sans">
                    <Sliders className="w-3.5 h-3.5 text-marigold" />
                    Response Detail Preference
                  </h3>
                  <p className="text-[11px] text-muted-warm font-sans mt-0.5">
                    Choose how in-depth you prefer standard concept explanations to be.
                  </p>
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
                  <button
                    type="button"
                    onClick={() => setExplanationStyle("concise")}
                    className={`p-3 rounded-xl border text-left transition-all cursor-pointer ${
                      explanationStyle === "concise"
                        ? "bg-elevated border-marigold shadow-xs ring-1 ring-marigold/30"
                        : "bg-surface border-border-warm hover:bg-elevated/40"
                    }`}
                  >
                    <div className="flex items-center justify-between mb-1">
                      <span className="text-xs font-serif font-bold text-ivory">Concise & Direct</span>
                      {explanationStyle === "concise" && <CheckCircle2 className="w-3.5 h-3.5 text-marigold" />}
                    </div>
                    <p className="text-[10px] text-muted-warm leading-relaxed">
                      High-signal, focused summaries prioritizing direct clarity and key takeaways.
                    </p>
                  </button>

                  <button
                    type="button"
                    onClick={() => setExplanationStyle("detailed")}
                    className={`p-3 rounded-xl border text-left transition-all cursor-pointer ${
                      explanationStyle === "detailed"
                        ? "bg-elevated border-marigold shadow-xs ring-1 ring-marigold/30"
                        : "bg-surface border-border-warm hover:bg-elevated/40"
                    }`}
                  >
                    <div className="flex items-center justify-between mb-1">
                      <span className="text-xs font-serif font-bold text-ivory">Comprehensive & Detailed</span>
                      {explanationStyle === "detailed" && <CheckCircle2 className="w-3.5 h-3.5 text-marigold" />}
                    </div>
                    <p className="text-[10px] text-muted-warm leading-relaxed">
                      Step-by-step breakdowns exploring historical context, mechanics, and edge cases.
                    </p>
                  </button>
                </div>
              </div>

              {/* Save Preferences Action Bar */}
              <div className="pt-2 border-t border-border-warm flex items-center justify-between gap-3">
                <div>
                  {profileSaveMessage && (
                    <p
                      className={`text-xs font-sans flex items-center gap-1.5 ${
                        profileSaveMessage.type === "success" ? "text-teal" : "text-terracotta"
                      }`}
                    >
                      {profileSaveMessage.type === "success" ? (
                        <CheckCircle2 className="w-3.5 h-3.5 shrink-0" />
                      ) : (
                        <AlertTriangle className="w-3.5 h-3.5 shrink-0" />
                      )}
                      {profileSaveMessage.text}
                    </p>
                  )}
                </div>

                <button
                  type="button"
                  onClick={handleSavePreferences}
                  disabled={isSavingProfile}
                  className="px-5 py-2 rounded-lg bg-marigold hover:bg-marigold-hover text-espresso text-xs font-bold transition-all cursor-pointer shadow-sm active:scale-95 disabled:opacity-50 disabled:cursor-not-allowed shrink-0"
                >
                  {isSavingProfile ? "Saving preferences..." : "Save Learning Preferences"}
                </button>
              </div>
            </div>
          )}

          {/* ========================================================
              TAB 2: LEARNER MEMORY MANAGEMENT (9C)
             ======================================================== */}
          {activeTab === "memory" && (
            <div className="space-y-5">
              {/* Educational Memory Explanation Banner */}
              <div className="bg-elevated/80 border border-border-warm rounded-xl p-4 space-y-1.5">
                <div className="flex items-center gap-2 text-xs font-serif font-semibold text-ivory">
                  <Database className="w-4 h-4 text-marigold" />
                  <span>Long-Term Learner Memory</span>
                </div>
                <p className="text-[11px] text-muted-warm font-sans leading-relaxed">
                  Finova records verified learning levels, goals, and instructional preferences here to tailor future explanations.
                  This memory is completely distinct from your conversation history and is never mixed with chat logs.
                </p>
              </div>

              {/* Memory List Header */}
              <div className="flex items-center justify-between">
                <h4 className="text-xs font-sans font-semibold text-ivory flex items-center gap-1.5">
                  <span>Active Memory Records</span>
                  <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-elevated border border-border-warm text-muted-warm">
                    {memories.length} item{memories.length === 1 ? "" : "s"}
                  </span>
                </h4>
                <button
                  type="button"
                  onClick={loadMemories}
                  className="text-xs text-muted-warm hover:text-ivory flex items-center gap-1 font-sans cursor-pointer transition-colors"
                >
                  <RefreshCw className={`w-3 h-3 ${isLoadingMemories ? "animate-spin text-marigold" : ""}`} />
                  <span>Refresh</span>
                </button>
              </div>

              {/* Status Banner */}
              {memoryMessage && (
                <div
                  className={`p-3 rounded-xl border text-xs font-sans flex items-start gap-2 ${
                    memoryMessage.type === "success"
                      ? "bg-teal/15 border-teal/30 text-ivory"
                      : "bg-terracotta/15 border-terracotta/30 text-terracotta"
                  }`}
                >
                  {memoryMessage.type === "success" ? (
                    <CheckCircle2 className="w-4 h-4 text-teal shrink-0 mt-0.5" />
                  ) : (
                    <AlertTriangle className="w-4 h-4 text-terracotta shrink-0 mt-0.5" />
                  )}
                  <span>{memoryMessage.text}</span>
                </div>
              )}

              {/* Memory List */}
              {isLoadingMemories ? (
                <div className="py-8 text-center text-xs text-muted-warm italic font-sans">
                  Loading persistent memories from backend...
                </div>
              ) : memories.length === 0 ? (
                <div className="bg-elevated/40 rounded-xl p-6 text-center border border-border-warm/60 space-y-1.5">
                  <Database className="w-6 h-6 text-muted-warm mx-auto mb-2 opacity-50" />
                  <p className="text-xs text-ivory/90 font-serif font-medium">No long-term memories stored yet</p>
                  <p className="text-[11px] text-muted-warm font-sans max-w-md mx-auto">
                    Configure your learning goals and preferences in the "Profile & Learning" tab, or share them in chat.
                  </p>
                </div>
              ) : (
                <div className="space-y-2 max-h-64 overflow-y-auto pr-1">
                  {memories.map((mem) => (
                    <div
                      key={mem.memory_id}
                      className="p-3 rounded-xl bg-elevated border border-border-warm/70 text-xs flex items-start justify-between gap-3 group hover:border-marigold/40 transition-colors"
                    >
                      <div className="min-w-0 flex-1 space-y-1">
                        <div className="flex items-center gap-2 flex-wrap">
                          <span className="font-mono font-semibold text-marigold text-[11px]">
                            {mem.key}
                          </span>
                          <span className="text-[10px] font-sans px-1.5 py-0.2 rounded bg-surface border border-border-warm text-muted-warm uppercase tracking-wider">
                            {mem.memory_type.replace(/_/g, " ")}
                          </span>
                        </div>
                        <p className="text-ivory/95 font-sans leading-relaxed break-words">
                          {typeof mem.value === "string" ? mem.value : JSON.stringify(mem.value)}
                        </p>
                        <div className="text-[10px] text-muted-warm font-mono flex items-center gap-2">
                          <span>Confidence: {(mem.confidence * 100).toFixed(0)}%</span>
                          <span>·</span>
                          <span>Source: {mem.source.replace(/_/g, " ")}</span>
                        </div>
                      </div>

                      <button
                        type="button"
                        onClick={() => handleDeleteMemory(mem.memory_id)}
                        className="p-1.5 rounded-lg text-muted-warm hover:text-terracotta hover:bg-surface transition-colors cursor-pointer shrink-0"
                        title="Delete this memory"
                        aria-label={`Delete memory ${mem.key}`}
                      >
                        <Trash2 className="w-3.5 h-3.5" />
                      </button>
                    </div>
                  ))}
                </div>
              )}

              {/* Clear All Memories Section */}
              <div className="pt-4 border-t border-border-warm space-y-2">
                <div className="flex items-center justify-between gap-3">
                  <div>
                    <h5 className="text-xs font-sans font-semibold text-terracotta">
                      Clear Learner Memory (Right to be Forgotten)
                    </h5>
                    <p className="text-[11px] text-muted-warm leading-relaxed">
                      Permanently wipes all personalized learning guidelines from local memory. Chat history remains untouched.
                    </p>
                  </div>

                  {!confirmClearMemory ? (
                    <button
                      type="button"
                      onClick={() => setConfirmClearMemory(true)}
                      disabled={isClearingMemory || memories.length === 0}
                      className="px-3.5 py-1.5 rounded-lg bg-terracotta/15 hover:bg-terracotta/25 text-terracotta border border-terracotta/30 text-xs font-semibold transition-colors disabled:opacity-40 disabled:cursor-not-allowed shrink-0 cursor-pointer"
                    >
                      Clear Memory
                    </button>
                  ) : (
                    <div className="flex items-center gap-2 shrink-0">
                      <button
                        type="button"
                        onClick={() => setConfirmClearMemory(false)}
                        className="px-2.5 py-1 rounded-lg bg-surface hover:bg-elevated text-muted-warm text-xs font-medium border border-border-warm cursor-pointer"
                      >
                        Cancel
                      </button>
                      <button
                        type="button"
                        onClick={handleClearAllMemories}
                        disabled={isClearingMemory}
                        className="px-3.5 py-1 rounded-lg bg-terracotta hover:bg-terracotta/90 text-white text-xs font-semibold cursor-pointer shadow-xs"
                      >
                        {isClearingMemory ? "Clearing..." : "Yes, Clear"}
                      </button>
                    </div>
                  )}
                </div>
              </div>
            </div>
          )}

          {/* ========================================================
              TAB 3: HISTORY & DATA CONTROLS (9D & 9I)
             ======================================================== */}
          {activeTab === "data" && (
            <div className="space-y-6">
              {/* Local Browser Identity Info (NO Generate New Identity button) */}
              <div className="bg-elevated p-4 rounded-xl border border-border-warm space-y-2">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-semibold text-ivory font-sans flex items-center gap-1.5">
                    <User className="w-3.5 h-3.5 text-marigold" />
                    Local Browser Identity
                  </span>
                  <span className="text-[10px] font-mono text-teal bg-teal/15 px-2 py-0.5 rounded border border-teal/30">
                    Local Device Partition
                  </span>
                </div>

                <div className="flex items-center gap-2 bg-surface p-2.5 rounded-lg border border-border-warm font-mono text-xs text-marigold">
                  <span className="flex-1 select-all truncate">{userId}</span>
                  <button
                    type="button"
                    onClick={handleCopyUserId}
                    className="p-1 rounded text-muted-warm hover:text-ivory hover:bg-elevated transition-colors cursor-pointer shrink-0"
                    title="Copy user ID"
                    aria-label="Copy User ID"
                  >
                    <Copy className="w-3.5 h-3.5" />
                  </button>
                </div>

                <p className="text-[11px] text-muted-warm font-sans leading-relaxed">
                  Finova uses this local key to partition conversations and long-term memory on your machine.
                  No central accounts, passwords, or external cloud identifiers are required.
                </p>

                {copiedUserId && (
                  <p className="text-[11px] text-teal flex items-center gap-1 font-sans">
                    <CheckCircle2 className="w-3.5 h-3.5" /> User ID copied to clipboard!
                  </p>
                )}
              </div>

              {/* Conversation History Clearing */}
              <div className="bg-elevated p-4 rounded-xl border border-border-warm space-y-3">
                <div className="space-y-1">
                  <div className="flex items-center justify-between">
                    <h4 className="text-xs font-semibold text-ivory flex items-center gap-1.5 font-sans">
                      <MessageSquare className="w-3.5 h-3.5 text-marigold" />
                      Conversation History
                    </h4>
                  </div>
                  <p className="text-[11px] text-muted-warm font-sans leading-relaxed">
                    Stores your previous inquiries, multi-turn assistant responses, citations, and market cards.
                    Clearing this affects past conversation history only. Your learner memory and personalization preferences will remain completely intact.
                  </p>
                </div>

                {dataMessage && (
                  <div
                    className={`p-3 rounded-lg border text-xs font-sans flex items-start gap-2 ${
                      dataMessage.type === "success"
                        ? "bg-teal/15 border-teal/30 text-ivory"
                        : "bg-terracotta/15 border-terracotta/30 text-terracotta"
                    }`}
                  >
                    {dataMessage.type === "success" ? (
                      <CheckCircle2 className="w-4 h-4 text-teal shrink-0 mt-0.5" />
                    ) : (
                      <AlertTriangle className="w-4 h-4 text-terracotta shrink-0 mt-0.5" />
                    )}
                    <span>{dataMessage.text}</span>
                  </div>
                )}

                <div className="pt-2 border-t border-border-warm flex items-center justify-between gap-3">
                  <div>
                    <span className="text-xs font-medium text-ivory/90">Clear all chat turns & sessions</span>
                    <p className="text-[10px] text-muted-warm">Removes all persistent conversation turns on this device</p>
                  </div>

                  {!confirmClearConversations ? (
                    <button
                      type="button"
                      onClick={() => setConfirmClearConversations(true)}
                      disabled={isClearingConversations}
                      className="px-3.5 py-1.5 rounded-lg bg-terracotta/15 hover:bg-terracotta/25 text-terracotta border border-terracotta/30 text-xs font-semibold transition-colors cursor-pointer shrink-0 disabled:opacity-50"
                    >
                      Clear Conversations
                    </button>
                  ) : (
                    <div className="flex items-center gap-2 shrink-0">
                      <button
                        type="button"
                        onClick={() => setConfirmClearConversations(false)}
                        className="px-2.5 py-1 rounded-lg bg-surface hover:bg-elevated text-muted-warm text-xs font-medium border border-border-warm cursor-pointer"
                      >
                        Cancel
                      </button>
                      <button
                        type="button"
                        onClick={handleClearAllConversations}
                        disabled={isClearingConversations}
                        className="px-3.5 py-1 rounded-lg bg-terracotta hover:bg-terracotta/90 text-white text-xs font-semibold cursor-pointer shadow-xs"
                      >
                        {isClearingConversations ? "Clearing..." : "Confirm Clear"}
                      </button>
                    </div>
                  )}
                </div>
              </div>
            </div>
          )}

          {/* ========================================================
              TAB 4: APPEARANCE & SETTINGS (9E & 9F)
             ======================================================== */}
          {activeTab === "appearance" && (
            <div className="space-y-5">
              <div>
                <h3 className="text-xs font-semibold text-ivory flex items-center gap-1.5 font-sans">
                  <Sun className="w-3.5 h-3.5 text-marigold" />
                  Display Theme & Visual Tone
                </h3>
                <p className="text-[11px] text-muted-warm font-sans mt-0.5">
                  Finova's editorial maroon, marigold, and teal palette adapts to your preferred lighting environment.
                </p>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                {/* Dark Theme Card */}
                <button
                  type="button"
                  onClick={() => setTheme("dark")}
                  className={`p-4 rounded-xl border text-left transition-all cursor-pointer ${
                    theme === "dark"
                      ? "bg-elevated border-marigold ring-1 ring-marigold/40 shadow-xs"
                      : "bg-surface border-border-warm hover:border-border-warm/90 hover:bg-elevated/40"
                  }`}
                >
                  <div className="flex items-center justify-between mb-2">
                    <div className="w-7 h-7 rounded-lg bg-[#1A0E0D] border border-border-warm flex items-center justify-center text-marigold">
                      <Moon className="w-3.5 h-3.5" />
                    </div>
                    {theme === "dark" && <CheckCircle2 className="w-4 h-4 text-marigold" />}
                  </div>
                  <h4 className="text-xs font-serif font-bold text-ivory">Espresso & Marigold</h4>
                  <p className="text-[10px] text-muted-warm font-sans mt-1 leading-relaxed">
                    Signature dark editorial canvas with rich maroon-black background and warm amber accents.
                  </p>
                </button>

                {/* Light Theme Card */}
                <button
                  type="button"
                  onClick={() => setTheme("light")}
                  className={`p-4 rounded-xl border text-left transition-all cursor-pointer ${
                    theme === "light"
                      ? "bg-elevated border-marigold ring-1 ring-marigold/40 shadow-xs"
                      : "bg-surface border-border-warm hover:border-border-warm/90 hover:bg-elevated/40"
                  }`}
                >
                  <div className="flex items-center justify-between mb-2">
                    <div className="w-7 h-7 rounded-lg bg-[#F7F3EC] border border-[#D4C5B3] flex items-center justify-center text-[#C97D1A]">
                      <Sun className="w-3.5 h-3.5" />
                    </div>
                    {theme === "light" && <CheckCircle2 className="w-4 h-4 text-marigold" />}
                  </div>
                  <h4 className="text-xs font-serif font-bold text-ivory">Warm Parchment</h4>
                  <p className="text-[10px] text-muted-warm font-sans mt-1 leading-relaxed">
                    Warm newsprint-inspired light aesthetic maintaining deep espresso text and marigold details.
                  </p>
                </button>

                {/* System Mode Card */}
                <button
                  type="button"
                  onClick={() => setTheme("system")}
                  className={`p-4 rounded-xl border text-left transition-all cursor-pointer ${
                    theme === "system"
                      ? "bg-elevated border-marigold ring-1 ring-marigold/40 shadow-xs"
                      : "bg-surface border-border-warm hover:border-border-warm/90 hover:bg-elevated/40"
                  }`}
                >
                  <div className="flex items-center justify-between mb-2">
                    <div className="w-7 h-7 rounded-lg bg-surface border border-border-warm flex items-center justify-center text-muted-warm">
                      <Monitor className="w-3.5 h-3.5" />
                    </div>
                    {theme === "system" && <CheckCircle2 className="w-4 h-4 text-marigold" />}
                  </div>
                  <h4 className="text-xs font-serif font-bold text-ivory">System Default</h4>
                  <p className="text-[10px] text-muted-warm font-sans mt-1 leading-relaxed">
                    Automatically syncs with your operating system's light or dark mode preference.
                  </p>
                </button>
              </div>
            </div>
          )}

          {/* ========================================================
              TAB 5: ABOUT FINOVA AI (9G)
             ======================================================== */}
          {activeTab === "about" && (
            <div className="space-y-4">
              <div className="bg-elevated p-4 rounded-xl border border-border-warm space-y-2">
                <div className="flex items-center justify-between">
                  <h3 className="text-xs font-serif font-bold text-ivory text-sm">
                    Finova AI
                  </h3>
                  <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-marigold/20 text-marigold border border-marigold/30">
                    Finova AI · Local Edition
                  </span>
                </div>
                <p className="text-xs text-ivory/90 font-serif leading-relaxed">
                  Autonomous Local Financial Learning & Concept Pedagogical Companion.
                </p>
                <p className="text-[11px] text-muted-warm font-sans leading-relaxed">
                  Designed for Indian investors, students, and practitioners to learn equities, derivatives, mutual funds, personal finance, and crypto through grounded RAG citations, real-time market data, and interactive calculators.
                </p>
              </div>

              {/* Data & Model Provenance */}
              <div className="bg-elevated p-4 rounded-xl border border-border-warm space-y-2">
                <h4 className="text-xs font-sans font-semibold text-ivory">
                  System & Provenance Architecture
                </h4>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-[11px] font-sans text-muted-warm">
                  <div className="p-2.5 rounded-lg bg-surface border border-border-warm/70">
                    <span className="block text-ivory font-medium mb-0.5">Zero-Cost / Local-First</span>
                    <span>All RAG embeddings and Qwen LLM inferences run 100% locally on your machine.</span>
                  </div>
                  <div className="p-2.5 rounded-lg bg-surface border border-border-warm/70">
                    <span className="block text-ivory font-medium mb-0.5">Isolated Local Storage</span>
                    <span>Learner memory and chat persistence operate independently on your local device.</span>
                  </div>
                </div>
              </div>

              {/* Truthful Educational Disclaimer */}
              <div className="p-4 rounded-xl bg-elevated/40 border border-border-warm text-[11px] text-muted-warm font-sans space-y-2 leading-relaxed">
                <div className="flex items-center gap-1.5 text-xs font-semibold text-ivory">
                  <Info className="w-3.5 h-3.5 text-marigold" />
                  <span>Educational-Only Notice</span>
                </div>
                <p>
                  Finova AI is strictly an educational learning companion. Information provided is for conceptual understanding, financial literacy, and curriculum learning purposes only.
                </p>
                <p>
                  Finova AI is <strong>not</strong> a SEBI-registered Investment Adviser, Research Analyst, or broker. Market quotes, portfolio records, and derivative calculations are simulated or paper figures and must not be construed as investment advice, recommendations, or endorsements of any security or asset class.
                </p>
                <p className="text-[10px] text-muted-warm/80">
                  Always consult a licensed financial advisor registered with SEBI before executing real investment decisions.
                </p>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
