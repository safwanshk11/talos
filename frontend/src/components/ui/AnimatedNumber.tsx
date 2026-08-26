import React, { useEffect, useRef, useState } from 'react';
import { useReducedMotion } from 'framer-motion';

interface AnimatedNumberProps {
  value: number;
  duration?: number;
}

/** Counts smoothly from the previously-displayed value to the new one — never
 * from zero on every rerender, and instant under prefers-reduced-motion. */
export const AnimatedNumber: React.FC<AnimatedNumberProps> = ({ value, duration = 600 }) => {
  const [display, setDisplay] = useState(value);
  const prevValue = useRef(value);
  const reducedMotion = useReducedMotion();

  useEffect(() => {
    const from = prevValue.current;
    const to = value;
    prevValue.current = value;
    if (from === to) return;
    if (reducedMotion) {
      setDisplay(to);
      return;
    }
    const start = performance.now();
    let raf: number;
    const tick = (now: number) => {
      const t = Math.min(1, (now - start) / duration);
      const eased = 1 - Math.pow(1 - t, 3);
      setDisplay(Math.round(from + (to - from) * eased));
      if (t < 1) raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [value]);

  return <>{display}</>;
};
