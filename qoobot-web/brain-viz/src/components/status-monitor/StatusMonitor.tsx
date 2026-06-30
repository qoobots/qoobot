/**
 * src/components/status-monitor/StatusMonitor.tsx — System status monitor panel
 */
'use client';

import { useRobotStore } from '@/stores/robotStore';
import { SAFETY_COLORS, SAFETY_LABELS } from '@/types/enums';

export function StatusMonitor() {
  const state = useRobotStore((s) => s.state);
  const connected = useRobotStore((s) => s.connected);
  const emergencyStop = state?.emergency_stop ?? false;
  const safetyLevel = state?.safety_level ?? 'NORMAL';

  return (
    <div className="p-4 space-y-4">
      <h2 className="text-sm font-mono font-bold text-brain-text">系统状态</h2>

      {/* Connection */}
      <div className="panel-card space-y-2">
        <div className="flex justify-between text-xs">
          <span className="text-brain-muted">连接状态</span>
          <span className={connected ? 'text-brain-safe' : 'text-brain-danger'}>
            {connected ? '在线' : '离线'}
          </span>
        </div>
      </div>

      {/* Safety */}
      <div className="panel-card space-y-2">
        <div className="flex justify-between text-xs">
          <span className="text-brain-muted">安全等级</span>
          <span style={{ color: SAFETY_COLORS[safetyLevel] }}>
            {SAFETY_LABELS[safetyLevel]}
          </span>
        </div>
        <div className="flex justify-between text-xs">
          <span className="text-brain-muted">紧急制动</span>
          <span className={emergencyStop ? 'text-brain-danger' : 'text-brain-safe'}>
            {emergencyStop ? '已触发' : '正常'}
          </span>
        </div>
      </div>

      {/* Joint States */}
      {state?.joints && (
        <div className="panel-card space-y-2">
          <h3 className="text-xs font-mono text-brain-muted">关节状态</h3>
          {state.joints.names.map((name, i) => (
            <div key={name} className="flex justify-between text-xs">
              <span className="text-brain-muted">{name}</span>
              <span className="text-brain-text font-mono">
                {state.joints.positions[i]?.toFixed(3) ?? '-'} rad
              </span>
            </div>
          ))}
        </div>
      )}

      {/* Emergency Stop Button */}
      <button
        className={`w-full py-3 rounded-lg text-sm font-bold transition-colors duration-200
          ${emergencyStop
            ? 'bg-brain-safe text-black'
            : 'bg-brain-danger text-white hover:bg-red-600'
          }`}
      >
        {emergencyStop ? '解除紧急制动' : '紧急制动'}
      </button>
    </div>
  );
}
