import React from 'react';
import { DecisionResponse } from '../types/weather';
import { Umbrella, Activity, Car, Shirt, AlertCircle, CheckCircle2, ShieldAlert, Info } from 'lucide-react';

interface DecisionCardProps {
  decision: DecisionResponse;
}

export const DecisionCard: React.FC<DecisionCardProps> = ({ decision }) => {
  const getDecisionIcon = (type: string) => {
    switch (type) {
      case 'umbrella':
        return <Umbrella className="w-5 h-5" />;
      case 'outdoor_activity':
        return <Activity className="w-5 h-5" />;
      case 'travel':
        return <Car className="w-5 h-5" />;
      case 'clothing':
        return <Shirt className="w-5 h-5" />;
      default:
        return <Info className="w-5 h-5" />;
    }
  };

  const getStatusBadge = (recommendation: string) => {
    switch (recommendation) {
      case 'recommended':
        return (
          <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/30">
            <CheckCircle2 className="w-3.5 h-3.5" /> Recommended
          </span>
        );
      case 'caution':
        return (
          <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-amber-500/10 text-amber-400 border border-amber-500/30">
            <AlertCircle className="w-3.5 h-3.5" /> Caution
          </span>
        );
      case 'not_recommended':
        return (
          <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-rose-500/10 text-rose-400 border border-rose-500/30">
            <ShieldAlert className="w-3.5 h-3.5" /> Not Recommended
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-sky-500/10 text-sky-400 border border-sky-500/30">
            <Info className="w-3.5 h-3.5" /> Neutral
          </span>
        );
    }
  };

  return (
    <div className="w-full bg-zinc-900/80 border border-zinc-800 rounded-3xl p-6 backdrop-blur shadow-xl space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-zinc-800/80 pb-3">
        <div className="flex items-center space-x-3">
          <div className="p-2 bg-zinc-800 rounded-xl text-zinc-300">
            {getDecisionIcon(decision.type)}
          </div>
          <div>
            <h4 className="text-sm font-medium text-zinc-200 capitalize">
              {decision.type.replace('_', ' ')} Decision
            </h4>
            <span className="text-[11px] text-zinc-500 font-mono uppercase tracking-wider">
              Confidence: {decision.confidence}
            </span>
          </div>
        </div>
        {getStatusBadge(decision.recommendation)}
      </div>

      {/* Decision Summary */}
      <p className="text-base text-zinc-100 font-normal leading-relaxed">
        {decision.summary}
      </p>

      {/* Factor Breakdown */}
      {decision.factors && decision.factors.length > 0 && (
        <div className="pt-2">
          <div className="text-xs text-zinc-500 font-mono uppercase tracking-wider mb-2">
            Decision Factors:
          </div>
          <div className="flex flex-wrap gap-2">
            {decision.factors.map((factor, idx) => (
              <div
                key={idx}
                className="px-3 py-1.5 bg-zinc-950/60 border border-zinc-800/80 rounded-xl text-xs flex items-center space-x-2"
              >
                <span className="text-zinc-400 capitalize">
                  {factor.metric.replace('_', ' ')}:
                </span>
                <span className="font-semibold text-zinc-200">{String(factor.value)}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};
