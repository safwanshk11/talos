import React, { useId } from 'react';

/**
 * The TALOS brand mark — a stylized "T" (swept wings + a tapered blade).
 * Single source of truth: used in the first-boot intro, the app sidebar,
 * the landing page nav/footer, the login page, and mirrored in
 * public/favicon.svg for the browser tab icon.
 */
export const TalosMark: React.FC<{ size?: number; className?: string }> = ({ size = 20, className }) => {
  // Unique per instance — multiple TalosMarks can render on the same page
  // (e.g. Sidebar + a modal), and SVG gradient ids must not collide.
  const gradientId = `talos-mark-gradient-${useId()}`;
  return (
    <svg width={size} height={size} viewBox="0 0 100 100" className={className}>
      <defs>
        <linearGradient id={gradientId} x1="0%" y1="0%" x2="0%" y2="100%">
          <stop offset="0%" stopColor="#f5f5f5" />
          <stop offset="55%" stopColor="#cdd8ea" />
          <stop offset="100%" stopColor="#5b8def" />
        </linearGradient>
      </defs>
      <path
        d="M46 21 L6 29 L8 38 L44 32 Z M54 21 L94 29 L92 38 L56 32 Z M42 46 L58 46 L52 90 L48 90 Z"
        fill={`url(#${gradientId})`}
      />
    </svg>
  );
};
