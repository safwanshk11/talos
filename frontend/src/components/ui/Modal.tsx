import React from 'react';
import { AnimatePresence, motion } from 'framer-motion';

interface ModalProps {
  isOpen: boolean;
  onClose?: () => void;
  maxWidth?: string;
  children: React.ReactNode;
}

/** Shared modal shell: animated backdrop + panel, consistent across every
 * dialog in TALOS (connect, scan progress, remove confirm, job detail). */
export const Modal: React.FC<ModalProps> = ({ isOpen, onClose, maxWidth = 'max-w-2xl', children }) => {
  return (
    <AnimatePresence>
      {isOpen && (
        <motion.div
          className="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm flex items-center justify-center p-4 select-none"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          transition={{ duration: 0.15 }}
          onClick={(e) => { if (e.target === e.currentTarget) onClose?.(); }}
        >
          <motion.div
            className={`bg-card border border-subtle w-full ${maxWidth} rounded-xl shadow-lift overflow-hidden flex flex-col max-h-[90vh]`}
            initial={{ opacity: 0, scale: 0.97, y: 8 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.97, y: 8 }}
            transition={{ duration: 0.22, ease: [0.16, 1, 0.3, 1] }}
          >
            {children}
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
};
