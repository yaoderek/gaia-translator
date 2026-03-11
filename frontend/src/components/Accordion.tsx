import { ChevronDown } from "lucide-react";
import { useState } from "react";

interface AccordionSectionProps {
  title: string;
  defaultOpen?: boolean;
  children: React.ReactNode;
}

export function AccordionSection({
  title,
  defaultOpen = true,
  children,
}: AccordionSectionProps) {
  const [open, setOpen] = useState(defaultOpen);

  return (
    <div className="border border-slate-200 rounded-lg overflow-hidden">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="w-full flex items-center justify-between px-4 py-2.5
                   bg-slate-50 hover:bg-slate-100 transition-colors text-left"
      >
        <span className="text-sm font-semibold text-slate-700">{title}</span>
        <ChevronDown
          className={`w-4 h-4 text-slate-400 transition-transform duration-200 ${
            open ? "rotate-180" : ""
          }`}
        />
      </button>
      <div
        className={`transition-all duration-200 ease-in-out ${
          open ? "max-h-[2000px] opacity-100" : "max-h-0 opacity-0 overflow-hidden"
        }`}
      >
        <div className="px-4 py-3">{children}</div>
      </div>
    </div>
  );
}
