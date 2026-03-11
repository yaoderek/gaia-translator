import { ChevronDown } from "lucide-react";
import type { Discipline, DisciplineInfo } from "../types";

const DISCIPLINES: DisciplineInfo[] = [
  { value: "hydrology", label: "Hydrology", description: "", key_concepts: [] },
  { value: "seismology", label: "Seismology", description: "", key_concepts: [] },
  { value: "atmospheric_science", label: "Atmospheric Science", description: "", key_concepts: [] },
  { value: "climatology", label: "Climatology", description: "", key_concepts: [] },
  { value: "geology", label: "Geology", description: "", key_concepts: [] },
  { value: "computer_science", label: "Computer Science", description: "", key_concepts: [] },
  { value: "applied_mathematics", label: "Applied Mathematics", description: "", key_concepts: [] },
];

interface Props {
  value: Discipline;
  onChange: (d: Discipline) => void;
  exclude?: Discipline;
}

export default function DisciplineSelector({ value, onChange, exclude }: Props) {
  return (
    <div className="relative inline-block">
      <select
        value={value}
        onChange={(e) => onChange(e.target.value as Discipline)}
        className="appearance-none bg-transparent text-sm font-semibold text-slate-800 pr-7 pl-2 py-2 
                   border-b-2 border-blue-500 cursor-pointer focus:outline-none focus:border-blue-600
                   hover:border-blue-400 transition-colors"
      >
        {DISCIPLINES.filter((d) => d.value !== exclude).map((d) => (
          <option key={d.value} value={d.value}>
            {d.label}
          </option>
        ))}
      </select>
      <ChevronDown className="absolute right-0 top-1/2 -translate-y-1/2 w-4 h-4 text-blue-500 pointer-events-none" />
    </div>
  );
}
