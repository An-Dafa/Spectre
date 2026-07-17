import { ChevronDown, ChevronRight } from "lucide-react";
import { ReactNode, useState } from "react";

export function Collapsible({ title, children }: { title: string; children: ReactNode }) {
  const [isOpen, setIsOpen] = useState(false);
  return (
    <div className="collapsible">
      <div className="collapsible-header" onClick={() => setIsOpen(!isOpen)}>
        <span>{title}</span>
        {isOpen ? <ChevronDown size={16} /> : <ChevronRight size={16} />}
      </div>
      {isOpen && <div className="collapsible-content">{children}</div>}
    </div>
  );
}
