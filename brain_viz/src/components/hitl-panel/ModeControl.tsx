/**
 * src/components/hitl-panel/ModeControl.tsx — Autonomy mode selector
 */
'use client';

import { useHITLStore } from '@/stores/hitlStore';

const modes = [
  { id: 'autonomous', label: '自主' },
  { id: 'suggested', label: '建议' },
  { id: 'manual',    label: '手动' },
] as const;

export function ModeControl() {
  const mode = useHITLStore((s) => s.mode);
  const setMode = useHITLStore((s) => s.setMode);

  return (
    <div className="flex bg-brain-border/30 rounded-md p-0.5">
      {modes.map((m) => (
        <button
          key={m.id}
          onClick={() => setMode(m.id)}
          className={`px-2 py-1 text-xs rounded transition-colors duration-200
            ${mode === m.id
              ? 'bg-brain-accent text-white'
              : 'text-brain-muted hover:text-brain-text'
            }`}
        >
          {m.label}
        </button>
      ))}
    </div>
  );
}
