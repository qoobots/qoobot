/**
 * src/stores/chatStore.ts — Chat & conversation history store (Zustand)
 *
 * Manages natural language conversation state, intent parsing results,
 * and conversation history between user and Brain OS.
 */
import { create } from 'zustand';
import type { Intent, Task } from '@/types/domain';

export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  timestamp: string;
  intent?: Intent;
  taskStatus?: Task['status'];
}

export interface ChatSession {
  id: string;
  messages: ChatMessage[];
  createdAt: string;
  activeTaskId: string | null;
}

interface ChatStore {
  // State
  sessions: ChatSession[];
  activeSessionId: string | null;
  isStreaming: boolean;
  inputDraft: string;

  // Computed helpers
  activeSession: () => ChatSession | undefined;

  // Actions
  newSession: () => string;
  switchSession: (sessionId: string) => void;
  addMessage: (message: ChatMessage) => void;
  setStreaming: (streaming: boolean) => void;
  setInputDraft: (text: string) => void;
  deleteMessage: (messageId: string) => void;
  clearSession: (sessionId: string) => void;
  setActiveTask: (taskId: string | null) => void;
}

let msgCounter = 0;
function nextMsgId(): string {
  return `msg_${Date.now()}_${++msgCounter}`;
}

function nextSessionId(): string {
  return `session_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`;
}

export const useChatStore = create<ChatStore>((set, get) => ({
  sessions: [],
  activeSessionId: null,
  isStreaming: false,
  inputDraft: '',

  activeSession: () => {
    const { sessions, activeSessionId } = get();
    return sessions.find((s) => s.id === activeSessionId);
  },

  newSession: () => {
    const id = nextSessionId();
    const session: ChatSession = {
      id,
      messages: [
        {
          id: nextMsgId(),
          role: 'system',
          content: 'Brain OS 已就绪。请用自然语言描述您的机器人任务。',
          timestamp: new Date().toISOString(),
        },
      ],
      createdAt: new Date().toISOString(),
      activeTaskId: null,
    };
    set((s) => ({
      sessions: [session, ...s.sessions],
      activeSessionId: id,
    }));
    return id;
  },

  switchSession: (sessionId) => set({ activeSessionId: sessionId }),

  addMessage: (message) =>
    set((s) => ({
      sessions: s.sessions.map((session) =>
        session.id === s.activeSessionId
          ? { ...session, messages: [...session.messages, message] }
          : session
      ),
    })),

  setStreaming: (streaming) => set({ isStreaming: streaming }),

  setInputDraft: (text) => set({ inputDraft: text }),

  deleteMessage: (messageId) =>
    set((s) => ({
      sessions: s.sessions.map((session) =>
        session.id === s.activeSessionId
          ? { ...session, messages: session.messages.filter((m) => m.id !== messageId) }
          : session
      ),
    })),

  clearSession: (sessionId) =>
    set((s) => ({
      sessions: s.sessions.filter((session) => session.id !== sessionId),
      activeSessionId:
        s.activeSessionId === sessionId ? null : s.activeSessionId,
    })),

  setActiveTask: (taskId) =>
    set((s) => ({
      sessions: s.sessions.map((session) =>
        session.id === s.activeSessionId
          ? { ...session, activeTaskId: taskId }
          : session
      ),
    })),
}));
