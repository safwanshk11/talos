import React from 'react';
import { motion, useReducedMotion } from 'framer-motion';

/** Wraps routed page content so navigation feels continuous rather than an
 * abrupt swap. Keep this cheap — transform/opacity only. */
export const PageTransition: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const reduceMotion = useReducedMotion();
  return (
    <motion.div
      initial={reduceMotion ? false : { opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      exit={reduceMotion ? undefined : { opacity: 0, y: -4 }}
      transition={{ duration: reduceMotion ? 0 : 0.22, ease: [0.16, 1, 0.3, 1] }}
    >
      {children}
    </motion.div>
  );
};
