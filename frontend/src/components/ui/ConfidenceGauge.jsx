import { cn } from "../../lib/cn.js";

// SVG arc showing 0..1 confidence. 180° semicircle.
export function ConfidenceGauge({ value = 0, size = 96, label = true, className }) {
  const clamped = Math.max(0, Math.min(1, value ?? 0));
  const stroke = 8;
  const radius = (size - stroke) / 2;
  const cx = size / 2;
  const cy = size / 2;
  const circumference = Math.PI * radius;
  const dash = circumference * clamped;

  const color =
    clamped >= 0.8
      ? "var(--accent)"
      : clamped >= 0.6
      ? "var(--accent-alt)"
      : clamped >= 0.4
      ? "var(--warn)"
      : "var(--danger)";

  return (
    <div className={cn("inline-flex flex-col items-center", className)}>
      <svg
        width={size}
        height={size / 2 + stroke}
        viewBox={`0 0 ${size} ${size / 2 + stroke}`}
        role="img"
        aria-label={`confidence ${(clamped * 100).toFixed(0)}%`}
      >
        <path
          d={`M ${stroke / 2} ${cy} A ${radius} ${radius} 0 0 1 ${size - stroke / 2} ${cy}`}
          fill="none"
          stroke="var(--border)"
          strokeWidth={stroke}
          strokeLinecap="round"
        />
        <path
          d={`M ${stroke / 2} ${cy} A ${radius} ${radius} 0 0 1 ${size - stroke / 2} ${cy}`}
          fill="none"
          stroke={color}
          strokeWidth={stroke}
          strokeLinecap="round"
          strokeDasharray={`${dash} ${circumference}`}
          style={{ transition: "stroke-dasharray 400ms ease" }}
        />
      </svg>
      {label && (
        <div className="-mt-3 text-center">
          <div className="text-base font-medium text-text tabular-nums">
            {(clamped * 100).toFixed(0)}%
          </div>
          <div className="text-[10px] text-text-muted uppercase tracking-wider">
            confidence
          </div>
        </div>
      )}
    </div>
  );
}
