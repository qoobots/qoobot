/**
 * src/components/chat-panel/VoiceIO.tsx — Voice input/output component
 *
 * Stub implementation for voice control interface.
 * Full ASR/TTS integration deferred to Phase 2.
 */
'use client';

import React, { useState, useCallback } from 'react';
import { Button } from '@/components/common/Button';

interface VoiceIOProps {
  onTranscript?: (text: string) => void;
  onAudioData?: (audioData: ArrayBuffer) => void;
  disabled?: boolean;
}

export function VoiceIO({ onTranscript, onAudioData, disabled = false }: VoiceIOProps) {
  const [isListening, setIsListening] = useState(false);
  const [isSpeaking, setIsSpeaking] = useState(false);

  const toggleListening = useCallback(() => {
    if (isListening) {
      setIsListening(false);
      // Mock transcript for demo
      onTranscript?.('拿起红色杯子');
    } else {
      setIsListening(true);
    }
  }, [isListening, onTranscript]);

  return (
    <div className="flex items-center gap-2 px-3 py-1.5 border-t border-brain-border">
      {/* Listen button */}
      <button
        onClick={toggleListening}
        disabled={disabled}
        className={`
          p-2 rounded-full transition-all duration-200
          ${isListening
            ? 'bg-red-500/20 text-red-400 animate-pulse'
            : 'text-brain-muted hover:text-brain-text hover:bg-brain-border/50'
          }
          disabled:opacity-40 disabled:cursor-not-allowed
        `.trim()}
        title={isListening ? '停止录音' : '语音输入'}
      >
        <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
            d="M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m0 0H8m4 0h4m-4-8a3 3 0 01-3-3V5a3 3 0 116 0v6a3 3 0 01-3 3z" />
        </svg>
      </button>
      {/* Speak indicator */}
      <button
        disabled={disabled}
        className={`
          p-2 rounded-full transition-all duration-200
          ${isSpeaking
            ? 'bg-indigo-500/20 text-indigo-400'
            : 'text-brain-muted hover:text-brain-text hover:bg-brain-border/50'
          }
          disabled:opacity-40 disabled:cursor-not-allowed
        `.trim()}
        title="语音输出"
      >
        <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
            d="M15.536 8.464a5 5 0 010 7.072m2.828-9.9a9 9 0 010 12.728M5.586 15H4a1 1 0 01-1-1v-4a1 1 0 011-1h1.586l4.707-4.707C10.923 3.663 12 4.109 12 5v14c0 .891-1.077 1.337-1.707.707L5.586 15z" />
        </svg>
      </button>
      {isListening && (
        <span className="text-xs text-red-400 animate-pulse ml-1">录音中...</span>
      )}
    </div>
  );
}
