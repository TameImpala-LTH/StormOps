import React, { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { useAuth } from '../context/AuthContext';

function getSalutation(date: Date): string {
  const hours = date.getHours();
  if (hours >= 5 && hours < 12) {
    return 'Good morning';
  } else if (hours >= 12 && hours < 17) {
    return 'Good afternoon';
  } else if (hours >= 17 && hours < 21) {
    return 'Good evening';
  } else {
    return 'Good night';
  }
}

export const PersonalizedGreeting: React.FC = () => {
  const { user, isAuthenticated } = useAuth();
  const [salutation, setSalutation] = useState<string>(() => getSalutation(new Date()));

  // Minute-level periodic check to gracefully update greeting across daypart boundaries
  useEffect(() => {
    const updateSalutation = () => {
      setSalutation(getSalutation(new Date()));
    };

    updateSalutation();
    const interval = setInterval(updateSalutation, 30000); // every 30 seconds
    return () => clearInterval(interval);
  }, []);

  if (!isAuthenticated || !user) {
    return null;
  }

  const rawName = user.display_name?.trim();
  const hasName = Boolean(rawName && rawName.length > 0);

  return (
    <motion.div
      initial={{ opacity: 0, y: -6 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
      className="inline-flex items-center gap-1.5 text-sm sm:text-base font-normal tracking-wide px-3.5 py-1 rounded-full border transition-all mb-1"
      style={{
        backgroundColor: 'var(--surface-elevated)',
        borderColor: 'var(--border-muted)',
        color: 'var(--text-secondary)',
      }}
    >
      <span>
        {salutation}
        {hasName ? (
          <>
            {', '}
            <span
              className="font-medium"
              style={{ color: 'var(--accent)' }}
            >
              {rawName}
            </span>
            {'!'}
          </>
        ) : (
          '!'
        )}
      </span>
    </motion.div>
  );
};
