import React from "react";
import { ShieldCheck, ShieldAlert, Info } from "lucide-react";
import type { GroundingStatus } from "../../api/types";

interface Props {
  status: GroundingStatus;
  sources?: string[];
  citationCount?: number;
}

export const GroundingBadge: React.FC<Props> = ({ status, sources = [], citationCount = 0 }) => {
  if (status === "fully_grounded") {
    return (
      <div className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-[11px] font-sans font-medium bg-teal/20 text-ivory border border-teal/40">
        <ShieldCheck className="w-3.5 h-3.5 text-teal stroke-[2.2]" />
        <span>Fully Grounded</span>
        {citationCount > 0 && (
          <span className="ml-0.5 px-1.5 py-0.2 rounded-full bg-teal/30 text-[10px] text-ivory font-mono">
            {citationCount} {citationCount === 1 ? "source" : "sources"}
          </span>
        )}
      </div>
    );
  }

  if (status === "partially_grounded") {
    return (
      <div className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-[11px] font-sans font-medium bg-marigold/15 text-marigold border border-marigold/30">
        <ShieldAlert className="w-3.5 h-3.5 text-marigold stroke-[2.2]" />
        <span>Partially Grounded</span>
        {sources.length > 0 && (
          <span className="text-[10px] text-muted-warm">({sources.join(", ")})</span>
        )}
      </div>
    );
  }

  return (
    <div className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-[11px] font-sans font-medium bg-surface border border-border-warm text-muted-warm">
      <Info className="w-3.5 h-3.5 text-muted-warm/70" />
      <span>General Educational</span>
    </div>
  );
};
