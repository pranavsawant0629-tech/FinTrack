import React from "react";
import {
  Lightbulb,
  Microscope,
  BookOpen,
  Puzzle,
  Cog,
  HelpCircle,
  Compass,
} from "lucide-react";

interface LearningActionsProps {
  topic: string;
  onSelectAction: (prompt: string) => void;
  disabled?: boolean;
}

interface ActionItem {
  id: string;
  label: string;
  shortLabel: string;
  icon: React.ComponentType<{ className?: string }>;
  promptBuilder: (topic: string) => string;
  badge?: string;
  theme: "teal" | "marigold" | "terracotta" | "ivory";
}

const LEARNING_ACTIONS: ActionItem[] = [
  {
    id: "simpler",
    label: "Explain simpler",
    shortLabel: "Simpler",
    icon: Lightbulb,
    promptBuilder: (topic) => `Explain ${topic} in simpler terms like I'm a beginner`,
    theme: "marigold",
  },
  {
    id: "deeper",
    label: "Go deeper",
    shortLabel: "Deeper",
    icon: Microscope,
    promptBuilder: (topic) => `Go deeper into the mathematical mechanics, assumptions, and nuances of ${topic}`,
    theme: "teal",
  },
  {
    id: "example",
    label: "Give an example",
    shortLabel: "Example",
    icon: BookOpen,
    promptBuilder: (topic) => `Give me a practical, real-world Indian market example of ${topic}`,
    theme: "ivory",
  },
  {
    id: "analogy",
    label: "Analogy",
    shortLabel: "Analogy",
    icon: Puzzle,
    promptBuilder: (topic) => `Explain ${topic} with an intuitive everyday analogy`,
    theme: "marigold",
  },
  {
    id: "mechanics",
    label: "Show mechanics",
    shortLabel: "Mechanics",
    icon: Cog,
    promptBuilder: (topic) => `Show the step-by-step formula and mathematical mechanics for ${topic}`,
    theme: "teal",
  },
  {
    id: "quiz",
    label: "Quiz me on this",
    shortLabel: "Quiz me",
    icon: HelpCircle,
    promptBuilder: (topic) => `Quiz me on ${topic}`,
    badge: "TEST",
    theme: "terracotta",
  },
  {
    id: "next",
    label: "What should I learn next?",
    shortLabel: "What next?",
    icon: Compass,
    promptBuilder: (topic) => `What should I learn next after ${topic}?`,
    theme: "ivory",
  },
];

export const LearningActions: React.FC<LearningActionsProps> = ({
  topic,
  onSelectAction,
  disabled = false,
}) => {
  if (!topic) return null;

  return (
    <div className="pt-2 pb-1" aria-label={`Learning controls for ${topic}`}>
      <div className="flex items-center gap-2 mb-2">
        <div className="flex items-center gap-1.5 text-[11px] font-mono uppercase tracking-widest text-muted-warm/80">
          <Lightbulb className="w-3.5 h-3.5 text-marigold" />
          <span>Tutor Exploration Controls</span>
        </div>
        <div className="h-px flex-1 bg-border-warm/40" />
      </div>

      <div className="flex flex-wrap items-center gap-1.5 sm:gap-2">
        {LEARNING_ACTIONS.map((action) => {
          const Icon = action.icon;
          const isTeal = action.theme === "teal";
          const isTerracotta = action.theme === "terracotta";
          const isMarigold = action.theme === "marigold";

          return (
            <button
              key={action.id}
              type="button"
              disabled={disabled}
              onClick={() => onSelectAction(action.promptBuilder(topic))}
              title={`Ask: ${action.promptBuilder(topic)}`}
              className={`inline-flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-xs font-medium transition-all duration-150 border cursor-pointer select-none disabled:opacity-50 disabled:cursor-not-allowed ${
                isTeal
                  ? "bg-teal/10 hover:bg-teal/20 text-teal-light border-teal/30 hover:border-teal/50"
                  : isTerracotta
                  ? "bg-terracotta/10 hover:bg-terracotta/20 text-terracotta border-terracotta/30 hover:border-terracotta/50"
                  : isMarigold
                  ? "bg-marigold/10 hover:bg-marigold/20 text-marigold border-marigold/30 hover:border-marigold/50"
                  : "bg-surface hover:bg-elevated text-ivory/90 border-border-warm hover:border-border-warm/80"
              }`}
            >
              <Icon className="w-3.5 h-3.5 shrink-0 opacity-80" />
              <span>{action.label}</span>
              {action.badge && (
                <span className="text-[9px] font-mono px-1 py-0.2 rounded bg-terracotta/20 text-terracotta border border-terracotta/30">
                  {action.badge}
                </span>
              )}
            </button>
          );
        })}
      </div>
    </div>
  );
};
