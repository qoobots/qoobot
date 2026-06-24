/**
 * src/components/dev-panel/CodeEditor.tsx — Simple JSON/XML code editor
 */
'use client';

import React, { useState } from 'react';
import { Button } from '@/components/common/Button';

interface CodeEditorProps {
  value: string;
  onChange: (value: string) => void;
  language?: 'json' | 'xml' | 'text';
  readOnly?: boolean;
  height?: string;
  label?: string;
}

export function CodeEditor({
  value,
  onChange,
  language = 'text',
  readOnly = false,
  height = '200px',
  label,
}: CodeEditorProps) {
  const [valid, setValid] = useState(true);

  const handleChange = (text: string) => {
    onChange(text);
    if (language === 'json') {
      try {
        JSON.parse(text);
        setValid(true);
      } catch {
        setValid(false);
      }
    }
  };

  const handleFormat = () => {
    if (language === 'json') {
      try {
        const parsed = JSON.parse(value);
        onChange(JSON.stringify(parsed, null, 2));
      } catch { /* ignore */ }
    }
  };

  return (
    <div className="space-y-1">
      {label && (
        <div className="flex items-center justify-between">
          <span className="text-xs text-brain-muted">{label}</span>
          <div className="flex gap-1">
            {!valid && (
              <span className="text-[10px] text-red-400">JSON 格式无效</span>
            )}
            {language === 'json' && (
              <button
                onClick={handleFormat}
                className="text-[10px] text-indigo-400 hover:text-indigo-300"
              >
                格式化
              </button>
            )}
          </div>
        </div>
      )}
      <textarea
        value={value}
        onChange={(e) => handleChange(e.target.value)}
        readOnly={readOnly}
        style={{ height }}
        className={`
          w-full bg-brain-bg text-brain-text font-mono text-xs p-2 rounded border
          resize-none focus:outline-none focus:border-indigo-500
          ${!valid ? 'border-red-500' : 'border-brain-border'}
        `.trim()}
        spellCheck={false}
      />
    </div>
  );
}
