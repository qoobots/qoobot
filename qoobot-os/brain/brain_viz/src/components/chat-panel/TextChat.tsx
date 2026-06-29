/**
 * src/components/chat-panel/TextChat.tsx — Text chat message list component
 */
'use client';

import React, { useEffect, useRef } from 'react';
import { useChatStore, type ChatMessage } from '@/stores/chatStore';
import { formatTimestamp } from '@/utils/formatTime';
import { LoadingSpinner } from '@/components/common/LoadingSpinner';
import { Badge } from '@/components/common/Badge';
import type { TaskStatus } from '@/types/domain';

interface TextChatProps {
  maxMessages?: number;
}

function MessageBubble({ message }: { message: ChatMessage }) {
  const isUser = message.role === 'user';
  const isSystem = message.role === 'system';

  if (isSystem) {
    return (
      <div className="flex justify-center my-3">
        <span className="text-xs text-brain-muted bg-brain-surface px-3 py-1 rounded-full">
          {message.content}
        </span>
      </div>
    );
  }

  return (
    <div className={`flex ${isUser ? 'justify-end' : 'justify-start'} mb-3`}>
      <div
        className={`
          max-w-[85%] rounded-lg px-3 py-2
          ${isUser
            ? 'bg-indigo-600/80 text-white rounded-br-sm'
            : 'bg-brain-surface text-brain-text rounded-bl-sm'
          }
        `.trim()}
      >
        <p className="text-sm whitespace-pre-wrap break-words">{message.content}</p>
        <div className="flex items-center gap-2 mt-1">
          <span className={`text-[10px] ${isUser ? 'text-indigo-200' : 'text-brain-muted'}`}>
            {formatTimestamp(message.timestamp)}
          </span>
          {message.intent && (
            <Badge size="sm" variant="outline">
              {message.intent.action}
            </Badge>
          )}
          {message.taskStatus && (
            <Badge size="sm" taskStatus={message.taskStatus as TaskStatus} />
          )}
        </div>
      </div>
    </div>
  );
}

export function TextChat({ maxMessages = 100 }: TextChatProps) {
  const activeSession = useChatStore((s) => s.activeSession());
  const messages = activeSession?.messages ?? [];
  const isStreaming = useChatStore((s) => s.isStreaming);
  const bottomRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom on new messages
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages.length]);

  const displayMessages = messages.slice(-maxMessages);

  return (
    <div className="flex-1 overflow-y-auto px-3 py-2 space-y-1">
      {displayMessages.length === 0 && !isStreaming && (
        <div className="flex items-center justify-center h-full text-brain-muted text-sm">
          开始对话以控制机器人
        </div>
      )}
      {displayMessages.map((msg) => (
        <MessageBubble key={msg.id} message={msg} />
      ))}
      {isStreaming && (
        <div className="flex justify-start mb-3">
          <div className="bg-brain-surface rounded-lg rounded-bl-sm px-4 py-3">
            <LoadingSpinner size="sm" />
          </div>
        </div>
      )}
      <div ref={bottomRef} />
    </div>
  );
}
