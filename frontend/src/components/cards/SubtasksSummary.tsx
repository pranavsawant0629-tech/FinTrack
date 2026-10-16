import React from "react";
import { GitFork, Check, AlertCircle, Clock } from "lucide-react";
import type { SubTaskExecutionMetadata } from "../../api/types";

interface SubtasksSummaryProps {
  subTasks: SubTaskExecutionMetadata[];
}

export const SubtasksSummary: React.FC<SubtasksSummaryProps> = ({ subTasks }) => {
  if (!subTasks || subTasks.length <= 1) return null;

  return (
    <div className="bg-surface/90 border border-border-warm rounded-xl p-3 my-2 text-xs animate-in fade-in duration-150">
      <div className="flex items-center gap-2 text-muted-warm mb-2 font-sans font-medium">
        <GitFork className="w-3.5 h-3.5 text-marigold" />
        <span>Multi-intent query decomposed into {subTasks.length} sub-tasks:</span>
      </div>

      <div className="flex flex-wrap gap-2">
        {subTasks.map((task) => {
          const isSuccess = task.status === "success";
          const isError = task.status === "error" || task.status === "failed";

          return (
            <div
              key={task.task_id}
              className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md text-[11px] font-mono border ${
                isSuccess
                  ? "bg-elevated border-border-warm text-ivory"
                  : isError
                  ? "bg-terracotta/20 border-terracotta/40 text-terracotta"
                  : "bg-marigold/15 border-marigold/30 text-marigold"
              }`}
            >
              {isSuccess ? (
                <Check className="w-3 h-3 text-teal stroke-[2.5]" />
              ) : isError ? (
                <AlertCircle className="w-3 h-3 text-terracotta stroke-[2.5]" />
              ) : (
                <Clock className="w-3 h-3 text-marigold" />
              )}
              <span className="font-semibold text-marigold">{task.domain}</span>
              {task.target && <span className="text-muted-warm">({task.target})</span>}
              <span className="text-muted-warm/60 text-[10px] ml-1">{task.latency_ms.toFixed(0)}ms</span>
            </div>
          );
        })}
      </div>
    </div>
  );
};
