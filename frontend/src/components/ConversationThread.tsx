import React from 'react';
import { motion } from 'framer-motion';
import { User, Sparkles, MapPin, Clock } from 'lucide-react';
import { MessageItem } from '../types/auth';
import { FormattedMarkdown } from './FormattedMarkdown';

interface ConversationThreadProps {
  messages: MessageItem[];
  locationName?: string | null;
  title?: string;
}

function formatMessageTime(dateStr: string): string {
  try {
    const d = new Date(dateStr);
    return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  } catch {
    return '';
  }
}

export const ConversationThread: React.FC<ConversationThreadProps> = ({
  messages,
  locationName,
  title,
}) => {
  if (!messages || messages.length === 0) return null;

  return (
    <div className="w-full space-y-4 mb-6">
      {/* Thread Header Banner */}
      <div
        className="flex items-center justify-between px-3 py-2 rounded-xl border text-xs"
        style={{
          backgroundColor: 'var(--surface-elevated)',
          borderColor: 'var(--border-muted)',
          color: 'var(--text-secondary)',
        }}
      >
        <div className="flex items-center gap-2 min-w-0">
          <Clock className="w-3.5 h-3.5 text-sky-400 shrink-0" />
          <span className="font-medium truncate" style={{ color: 'var(--text-primary)' }}>
            {title || 'Previous WeatherGPT Conversation'}
          </span>
          {locationName && (
            <span className="flex items-center gap-1 font-mono text-[11px] text-zinc-400">
              · <MapPin className="w-3 h-3 text-emerald-400 shrink-0" />
              {locationName}
            </span>
          )}
        </div>
        <span className="text-[10px] font-mono shrink-0 opacity-70">
          {messages.length} {messages.length === 1 ? 'Message' : 'Messages'}
        </span>
      </div>

      {/* Messages List */}
      <div className="space-y-3">
        {messages.map((m, idx) => {
          const isUser = m.role === 'user';
          const timeStr = formatMessageTime(m.created_at);

          return (
            <motion.div
              key={m.id || idx}
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.2 }}
              className={`flex gap-2.5 max-w-3xl ${isUser ? 'ml-auto flex-row-reverse' : 'mr-auto'}`}
            >
              {/* Avatar Icon */}
              <div
                className={`w-7 h-7 rounded-full flex items-center justify-center shrink-0 text-xs border ${
                  isUser
                    ? 'bg-sky-500/10 text-sky-400 border-sky-500/20'
                    : 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20'
                }`}
              >
                {isUser ? <User className="w-3.5 h-3.5" /> : <Sparkles className="w-3.5 h-3.5" />}
              </div>

              {/* Message Bubble */}
              <div
                className={`p-3 rounded-2xl text-xs space-y-1 border ${
                  isUser
                    ? 'rounded-tr-xs bg-sky-950/30 border-sky-800/40 text-sky-100'
                    : 'rounded-tl-xs border-zinc-800/60'
                }`}
                style={{
                  backgroundColor: !isUser ? 'var(--surface-elevated)' : undefined,
                  borderColor: !isUser ? 'var(--border-muted)' : undefined,
                  color: !isUser ? 'var(--text-primary)' : undefined,
                }}
              >
                <div className="flex items-center justify-between gap-3 text-[10px]">
                  <span className="font-semibold uppercase tracking-wider font-mono opacity-60">
                    {isUser ? 'You' : 'WeatherGPT'}
                  </span>
                  {timeStr && <span className="opacity-50 font-mono">{timeStr}</span>}
                </div>
                <div className="leading-relaxed">
                  {isUser ? (
                    <div className="whitespace-pre-wrap">{m.content}</div>
                  ) : (
                    <FormattedMarkdown content={m.content} />
                  )}
                </div>
              </div>
            </motion.div>
          );
        })}
      </div>
    </div>
  );
};
