import React from 'react';
import { motion } from 'framer-motion';

interface LoadingStateProps {
  locationName: string;
}

export const LoadingState: React.FC<LoadingStateProps> = ({ locationName }) => {
  const isLongQuery = locationName.length > 25 || locationName.includes(' ');

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0 }}
      className="w-full max-w-lg mx-auto rounded-3xl p-8 text-center space-y-4"
      style={{
        backgroundColor: 'var(--surface)',
        border: '1px solid var(--border)',
      }}
    >
      <div className="flex justify-center">
        <div
          className="w-10 h-10 border-2 rounded-full animate-spin"
          style={{
            borderColor: 'var(--spinner-track)',
            borderTopColor: 'var(--spinner-head)',
          }}
        />
      </div>
      <div className="text-lg font-light" style={{ color: 'var(--text-primary)' }}>
        {isLongQuery ? (
          <span>Checking weather conditions...</span>
        ) : (
          <span>
            Retrieving meteorological data for{' '}
            <span className="font-medium" style={{ color: 'var(--accent)' }}>
              {locationName}
            </span>
          </span>
        )}
      </div>
      <div className="text-xs font-mono" style={{ color: 'var(--text-muted)' }}>
        Connecting to Open-Meteo weather intelligence service
      </div>
    </motion.div>
  );
};
