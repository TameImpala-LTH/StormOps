import React from 'react';
import { ExtractedQueryInfo } from '../types/weather';
import { Sparkles, Compass } from 'lucide-react';

interface QuerySummaryCardProps {
  queryInfo: ExtractedQueryInfo;
  summary: string;
}

export const QuerySummaryCard: React.FC<QuerySummaryCardProps> = ({ queryInfo, summary }) => {
  const formatIntentLabel = (intent: string) => {
    switch (intent) {
      case 'umbrella_recommendation':
        return 'Umbrella Recommendation';
      case 'rain_query':
        return 'Rain Risk Evaluation';
      case 'temperature_query':
        return 'Temperature Query';
      default:
        return 'Weather Intelligence';
    }
  };

  return (
    <div className="w-full bg-zinc-900/80 border border-emerald-500/30 rounded-3xl p-6 backdrop-blur shadow-xl space-y-3">
      <div className="flex flex-wrap items-center justify-between gap-2 border-b border-zinc-800/80 pb-3">
        <div className="flex items-center space-x-2">
          <span className="p-1.5 bg-emerald-500/10 rounded-lg text-emerald-400">
            <Sparkles className="w-4 h-4" />
          </span>
          <span className="text-xs font-mono font-medium text-emerald-400 uppercase tracking-wider">
            {formatIntentLabel(queryInfo.intent)}
          </span>
        </div>

        <div className="flex items-center space-x-2 text-xs font-mono text-zinc-400">
          <Compass className="w-3.5 h-3.5 text-zinc-500" />
          <span>Context: {queryInfo.date_context} ({queryInfo.time_period})</span>
        </div>
      </div>

      <p className="text-base font-normal text-zinc-200 leading-relaxed pt-1">
        {summary}
      </p>
    </div>
  );
};
