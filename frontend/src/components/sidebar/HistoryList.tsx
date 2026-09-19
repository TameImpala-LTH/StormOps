import React, { useMemo } from 'react';
import { MessageSquare, Trash2, Clock, MapPin } from 'lucide-react';
import { ConversationSummary } from '../../types/auth';
import { useTheme } from '../../context/ThemeContext';

interface HistoryListProps {
  conversations: ConversationSummary[];
  activeConversationId?: string;
  onSelectConversation: (conversationId: string) => void;
  onDeleteConversation: (conversationId: string, e: React.MouseEvent) => void;
}

type TimeBucket = 'Today' | 'Yesterday' | 'Earlier this week' | 'Older';

function getTimeBucket(dateStr: string): TimeBucket {
  try {
    const d = new Date(dateStr);
    const now = new Date();

    const isToday =
      d.getDate() === now.getDate() &&
      d.getMonth() === now.getMonth() &&
      d.getFullYear() === now.getFullYear();
    if (isToday) return 'Today';

    const yesterday = new Date(now);
    yesterday.setDate(now.getDate() - 1);
    const isYesterday =
      d.getDate() === yesterday.getDate() &&
      d.getMonth() === yesterday.getMonth() &&
      d.getFullYear() === yesterday.getFullYear();
    if (isYesterday) return 'Yesterday';

    const diffMs = now.getTime() - d.getTime();
    const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));
    if (diffDays < 7) return 'Earlier this week';

    return 'Older';
  } catch {
    return 'Older';
  }
}

function formatWallClockTime(dateStr: string): string {
  try {
    const d = new Date(dateStr);
    return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  } catch {
    return '';
  }
}

function formatRelativeTime(dateStr: string): string {
  try {
    const d = new Date(dateStr);
    const now = new Date();
    const diffMs = now.getTime() - d.getTime();
    const diffMins = Math.floor(diffMs / (1000 * 60));
    const diffHours = Math.floor(diffMins / 60);

    if (diffMins < 1) return 'Just now';
    if (diffMins < 60) return `${diffMins}m ago`;
    if (diffHours < 24) return `${diffHours}h ago`;
    return d.toLocaleDateString(undefined, { month: 'short', day: 'numeric' });
  } catch {
    return '';
  }
}

export const HistoryList: React.FC<HistoryListProps> = ({
  conversations,
  activeConversationId,
  onSelectConversation,
  onDeleteConversation,
}) => {
  const { accentColor } = useTheme();
  const grouped = useMemo(() => {
    const buckets: { label: TimeBucket; items: ConversationSummary[] }[] = [
      { label: 'Today', items: [] },
      { label: 'Yesterday', items: [] },
      { label: 'Earlier this week', items: [] },
      { label: 'Older', items: [] },
    ];

    for (const c of conversations) {
      const bucket = getTimeBucket(c.updated_at || c.created_at);
      const target = buckets.find((b) => b.label === bucket);
      if (target) {
        target.items.push(c);
      }
    }

    return buckets.filter((b) => b.items.length > 0);
  }, [conversations]);

  if (conversations.length === 0) {
    return (
      <div className="py-8 px-3 text-center">
        <Clock className="w-5 h-5 mx-auto mb-2 opacity-30 text-zinc-400" />
        <p className="text-xs font-medium" style={{ color: 'var(--text-secondary)' }}>
          No weather searches yet.
        </p>
        <p className="text-[11px] mt-1" style={{ color: 'var(--text-muted)' }}>
          Ask WeatherGPT about any location to build your personal timeline.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {grouped.map((group) => (
        <div key={group.label} className="space-y-2">
          <div
            className="px-1 text-[10px] font-semibold tracking-wider uppercase opacity-60"
            style={{ color: 'var(--text-muted)' }}
          >
            {group.label}
          </div>

          <div className="space-y-2">
            {group.items.map((c) => {
              const isActive = c.id === activeConversationId;
              const dateRef = c.updated_at || c.created_at;
              const wallClock = formatWallClockTime(dateRef);
              const relative = formatRelativeTime(dateRef);

              return (
                <div
                  key={c.id}
                  onClick={() => onSelectConversation(c.id)}
                  className={`group relative flex flex-col p-2.5 rounded-xl text-xs cursor-pointer transition-all border ${
                    isActive
                      ? 'shadow-xs'
                      : 'hover:border-zinc-700/60'
                  }`}
                  style={{
                    backgroundColor: isActive
                      ? 'var(--surface-elevated)'
                      : 'rgba(255, 255, 255, 0.02)',
                    borderColor: isActive ? 'var(--accent)' : 'var(--border-muted)',
                    color: 'var(--text-primary)',
                    boxShadow: isActive ? `0 0 0 1px ${accentColor}40` : undefined,
                  }}
                >
                  {/* Header row: Time & location meta */}
                  <div className="flex items-center justify-between gap-1 w-full mb-1">
                    <div className="flex items-center gap-1.5 text-[10px] font-mono" style={{ color: 'var(--text-muted)' }}>
                      {wallClock && <span>{wallClock}</span>}
                      {c.location_name && (
                        <>
                          <span>·</span>
                          <span className="flex items-center gap-0.5 text-zinc-300 font-medium">
                            <MapPin className="w-2.5 h-2.5 text-emerald-400 shrink-0" />
                            <span className="truncate max-w-[100px]">{c.location_name}</span>
                          </span>
                        </>
                      )}
                    </div>

                    <div className="flex items-center gap-1">
                      <span className="text-[9px] opacity-60" style={{ color: 'var(--text-muted)' }}>
                        {relative}
                      </span>
                      {/* Delete action button */}
                      <button
                        type="button"
                        onClick={(e) => onDeleteConversation(c.id, e)}
                        title="Delete from timeline"
                        className="opacity-0 group-hover:opacity-100 p-1 rounded hover:text-rose-400 transition-all text-zinc-400 -mr-1 cursor-pointer"
                      >
                        <Trash2 className="w-3 h-3" />
                      </button>
                    </div>
                  </div>

                  {/* Question */}
                  <div className="font-medium text-[12px] leading-tight flex items-start gap-1.5">
                    <MessageSquare className="w-3.5 h-3.5 shrink-0 opacity-70 mt-0.5" style={{ color: 'var(--accent)' }} />
                    <span className="line-clamp-2">{c.last_query || c.title}</span>
                  </div>

                  {/* Answer snippet if stored */}
                  {c.last_answer && (
                    <div
                      className="mt-2 text-[11px] line-clamp-2 pl-4 pt-1.5 border-t"
                      style={{
                        borderColor: 'var(--border-muted)',
                        color: 'var(--text-secondary)',
                      }}
                    >
                      <span className="italic opacity-90">"{c.last_answer}"</span>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      ))}
    </div>
  );
};
