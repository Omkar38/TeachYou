import { CheckCircle2 } from "lucide-react";

type Step = {
  key: string;
  label: string;
};

export function Stepper({ steps, activeKey }: { steps: Step[]; activeKey: string }) {
  const activeIdx = Math.max(0, steps.findIndex((s) => s.key === activeKey));
  return (
    <div className="w-full border-b border-neutral-200 bg-white">
      <div className="mx-auto flex w-full max-w-6xl items-center gap-6 px-4 py-3 text-sm">
        {steps.map((s, idx) => {
          const done = idx < activeIdx;
          const active = idx === activeIdx;
          return (
            <div key={s.key} className="flex items-center gap-2">
              {done ? (
                <CheckCircle2 className="h-5 w-5 text-emerald-600" />
              ) : (
                <div
                  className={
                    "flex h-5 w-5 items-center justify-center rounded-full border text-xs font-semibold " +
                    (active ? "border-neutral-900 bg-neutral-900 text-white" : "border-neutral-300 bg-white text-neutral-600")
                  }
                >
                  {idx + 1}
                </div>
              )}
              <div className={active ? "font-semibold text-neutral-900" : "text-neutral-600"}>{s.label}</div>
              {idx !== steps.length - 1 ? <div className="mx-2 h-px w-10 bg-neutral-200" /> : null}
            </div>
          );
        })}
        <div className="ml-auto text-xs text-neutral-500">Click on media or text to edit</div>
      </div>
    </div>
  );
}
