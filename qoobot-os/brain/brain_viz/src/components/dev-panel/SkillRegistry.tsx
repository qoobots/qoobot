/**
 * src/components/dev-panel/SkillRegistry.tsx — Skill registry viewer
 */
'use client';

import React, { useEffect, useState } from 'react';
import { knowledgeClient, type Skill } from '@/services/knowledgeClient';
import { Button } from '@/components/common/Button';
import { LoadingSpinner } from '@/components/common/LoadingSpinner';

export function SkillRegistry() {
  const [skills, setSkills] = useState<Skill[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedSkill, setSelectedSkill] = useState<Skill | null>(null);

  useEffect(() => {
    knowledgeClient.listSkills().then((s) => {
      setSkills(s);
      setLoading(false);
    });
  }, []);

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <h3 className="text-xs text-brain-muted uppercase tracking-wide">
          技能注册表 ({skills.length})
        </h3>
        <Button size="sm" variant="ghost" onClick={() => {
          setLoading(true);
          knowledgeClient.listSkills().then((s) => {
            setSkills(s);
            setLoading(false);
          });
        }}>
          刷新
        </Button>
      </div>

      {loading ? (
        <LoadingSpinner size="sm" label="加载技能..." />
      ) : (
        <div className="flex flex-col gap-1">
          {skills.map((skill) => (
            <button
              key={skill.name}
              onClick={() => setSelectedSkill(skill)}
              className={`
                text-left px-2 py-1.5 rounded text-xs transition-colors
                ${selectedSkill?.name === skill.name
                  ? 'bg-indigo-500/10 border border-indigo-500/20'
                  : 'bg-brain-surface hover:bg-brain-border/30 border border-transparent'
                }
              `.trim()}
            >
              <span className="text-brain-text font-mono font-medium">{skill.name}</span>
              <span className="text-brain-muted ml-2">{skill.description}</span>
            </button>
          ))}
        </div>
      )}

      {selectedSkill && (
        <div className="panel-card mt-3">
          <h4 className="text-sm font-semibold text-brain-text mb-2">{selectedSkill.name}</h4>
          <p className="text-xs text-brain-muted">{selectedSkill.description}</p>
          {selectedSkill.parameters && selectedSkill.parameters.length > 0 && (
            <div className="mt-2">
              <span className="text-[10px] text-brain-muted uppercase">参数</span>
              <div className="flex flex-wrap gap-1 mt-1">
                {selectedSkill.parameters.map((p) => (
                  <span key={p} className="text-[10px] bg-brain-border px-1.5 py-0.5 rounded font-mono text-brain-text">
                    {p}
                  </span>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
