import { Brain } from "lucide-react";
import { EmptyState } from "../ui/EmptyState.jsx";

export function ReasoningTrace({ steps }) {
  if (!steps || steps.length === 0) {
    return (
      <EmptyState
        icon={Brain}
        title="No reasoning trace"
        description="The agent did not record reasoning for this ticket."
      />
    );
  }
  return (
    <ol className="px-5 py-4 space-y-2.5">
      {steps.map((s, i) => (
        <li key={i} className="flex gap-3">
          <div className="w-5 h-5 rounded-full bg-surface-2 border border-border text-[10px] font-mono flex items-center justify-center shrink-0 text-text-dim tabular-nums">
            {i + 1}
          </div>
          <p className="text-sm text-text-dim leading-relaxed">{s}</p>
        </li>
      ))}
    </ol>
  );
}
