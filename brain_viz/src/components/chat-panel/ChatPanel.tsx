/**
 * src/components/chat-panel/ChatPanel.tsx — Chat / instruction input panel
 *
 * Integrates TextChat, IntentView, SubtaskTimeline, and VoiceIO.
 * Uses chatStore for persistent conversation state.
 */
'use client';

import { useState, useCallback, useEffect, useRef } from 'react';
import { Send } from 'lucide-react';
import { cognitionClient } from '@/services/cognitionClient';
import { grpcClient } from '@/services/grpcClient';
import { useChatStore, type ChatMessage } from '@/stores/chatStore';
import { TextChat } from './TextChat';
import { IntentView } from './IntentView';
import { SubtaskTimeline } from './SubtaskTimeline';
import { VoiceIO } from './VoiceIO';
import type { Intent, Task } from '@/types/domain';

export function ChatPanel() {
  const [instruction, setInstruction] = useState('');
  const [lastIntent, setLastIntent] = useState<Intent | null>(null);
  const [lastTask, setLastTask] = useState<Task | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const activeSession = useChatStore((s) => s.activeSession());
  const isStreaming = useChatStore((s) => s.isStreaming);
  const addMessage = useChatStore((s) => s.addMessage);
  const setStreaming = useChatStore((s) => s.setStreaming);
  const newSession = useChatStore((s) => s.newSession);
  const setActiveTask = useChatStore((s) => s.setActiveTask);

  // Create initial session if none exists
  useEffect(() => {
    if (!activeSession) {
      newSession();
    }
    inputRef.current?.focus();
  }, [activeSession, newSession]);

  const handleSend = useCallback(async () => {
    if (!instruction.trim() || isStreaming) return;

    const text = instruction.trim();
    setInstruction('');
    setStreaming(true);

    // Add user message
    addMessage({
      id: `msg_${Date.now()}`,
      role: 'user',
      content: text,
      timestamp: new Date().toISOString(),
    });

    try {
      // Step 1: Parse intent
      const { intent } = await cognitionClient.parseIntent(text);
      setLastIntent(intent);

      addMessage({
        id: `msg_${Date.now()}`,
        role: 'assistant',
        content: `意图识别: ${intent.action} → ${intent.target} (置信度 ${(intent.confidence * 100).toFixed(0)}%)`,
        timestamp: new Date().toISOString(),
        intent,
      });

      // Step 2: Decompose task
      try {
        const task = await cognitionClient.decomposeTask(intent);
        setLastTask(task);

        addMessage({
          id: `msg_${Date.now()}`,
          role: 'assistant',
          content: `任务已分解为 ${task.subtasks?.length || 1} 个子任务`,
          timestamp: new Date().toISOString(),
          taskStatus: task.status,
        });

        setActiveTask(task.id);

        // Step 3: Request trajectory generation
        const trajs = await grpcClient.generateTrajectories(
          task.id,
          { x: 0.3, y: 0.1, z: 0.2 }
        );

        addMessage({
          id: `msg_${Date.now()}`,
          role: 'assistant',
          content: `已生成 ${trajs.length} 条轨迹候选，请在 HITL 面板中选择`,
          timestamp: new Date().toISOString(),
        });
      } catch {
        addMessage({
          id: `msg_${Date.now()}`,
          role: 'assistant',
          content: '任务分解中，请稍候...',
          timestamp: new Date().toISOString(),
        });
      }
    } catch {
      // Fallback: stub parsing
      const fallbackIntent: Intent = {
        action: 'pick',
        target: instruction.includes('红色') ? 'red_cup' : 'object',
        constraints: [],
        confidence: 0.85,
      };
      setLastIntent(fallbackIntent);

      addMessage({
        id: `msg_${Date.now()}`,
        role: 'assistant',
        content: `[离线模式] 意图: ${fallbackIntent.action} → ${fallbackIntent.target}`,
        timestamp: new Date().toISOString(),
        intent: fallbackIntent,
      });
    } finally {
      setStreaming(false);
    }
  }, [instruction, isStreaming, addMessage, setStreaming, setActiveTask]);

  const handleVoiceTranscript = useCallback((text: string) => {
    setInstruction(text);
  }, []);

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="px-4 py-3 border-b border-brain-border">
        <h2 className="text-sm font-semibold text-brain-text">指令对话</h2>
      </div>

      {/* Intent visualization */}
      {lastIntent && (
        <IntentView intent={lastIntent} />
      )}

      {/* Subtask timeline */}
      {lastTask && (
        <SubtaskTimeline task={lastTask} />
      )}

      {/* Chat history */}
      <TextChat />

      {/* Input area */}
      <div className="border-t border-brain-border">
        <div className="flex items-center gap-2 px-3 py-2">
          <input
            ref={inputRef}
            type="text"
            value={instruction}
            onChange={(e) => setInstruction(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleSend()}
            placeholder="输入指令，如：拿起红色杯子..."
            disabled={isStreaming}
            className="flex-1 bg-brain-bg border border-brain-border rounded-md px-3 py-1.5
                       text-xs text-brain-text placeholder-brain-muted
                       focus:outline-none focus:border-indigo-500
                       disabled:opacity-50"
          />
          <button
            onClick={handleSend}
            disabled={!instruction.trim() || isStreaming}
            className="bg-indigo-600 hover:bg-indigo-500 text-white p-2 rounded-md
                       transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <Send size={14} />
          </button>
        </div>
        <VoiceIO onTranscript={handleVoiceTranscript} disabled={isStreaming} />
      </div>
    </div>
  );
}
