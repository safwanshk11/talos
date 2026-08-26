import React, { useEffect, useMemo, useRef, useState } from 'react';
import { AnimatePresence, motion, useReducedMotion } from 'framer-motion';
import { TalosMark } from './ui/TalosMark';

const STORAGE_KEY = 'talos_initialized';

const STAGES = ['Initializing', 'Connecting', 'Modules', 'Securing', 'Ready'];

// Presentation states only — deliberately worded so nothing here claims a
// real backend operation occurred during app boot (there isn't one).
const STATUS_LABELS = [
  'Loading interface…',
  'Connecting to services…',
  'Loading modules…',
  'Preparing workspace…',
  'TALOS ready.',
];

function shouldShowIntro(): boolean {
  try {
    const params = new URLSearchParams(window.location.search);
    if (params.get('intro') === 'true') return true;
    return localStorage.getItem(STORAGE_KEY) !== 'true';
  } catch {
    // localStorage unavailable (private mode, disabled, etc.) — never block
    // access to the app over a cosmetic feature.
    return false;
  }
}

function markInitialized() {
  try {
    localStorage.setItem(STORAGE_KEY, 'true');
  } catch {
    // ignore — worst case the intro replays next visit, harmless
  }
}

/** Thin, broken-arc ring — not a solid neon circle. One arc slowly rotates. */
const OrbitRing: React.FC = () => (
  <motion.svg
    width="220"
    height="220"
    viewBox="0 0 220 220"
    className="absolute inset-0 m-auto"
    style={{ pointerEvents: 'none' }}
    animate={{ rotate: 360 }}
    transition={{ duration: 14, repeat: Infinity, ease: 'linear' }}
  >
    <circle cx="110" cy="110" r="104" fill="none" stroke="rgba(255,255,255,0.06)" strokeWidth="1" />
    <circle
      cx="110" cy="110" r="104" fill="none"
      stroke="rgba(59,130,246,0.55)" strokeWidth="1.5" strokeLinecap="round"
      strokeDasharray="40 610"
    />
    <circle
      cx="110" cy="110" r="104" fill="none"
      stroke="rgba(255,255,255,0.25)" strokeWidth="1" strokeLinecap="round"
      strokeDasharray="18 610" strokeDashoffset="-260"
    />
  </motion.svg>
);

const BootSequence: React.FC<{ onComplete: () => void }> = ({ onComplete }) => {
  const [stageIndex, setStageIndex] = useState(0);
  const [exiting, setExiting] = useState(false);
  const completedRef = useRef(false);

  const complete = useMemo(
    () => () => {
      if (completedRef.current) return;
      completedRef.current = true;
      markInitialized();
      onComplete();
    },
    [onComplete]
  );

  useEffect(() => {
    // Fail-safe: the splash is presentation only — it can never be allowed
    // to permanently block access to the app if a timer/animation misfires.
    const hardStop = setTimeout(complete, 8000);

    const stageDelays = [2000, 2450, 2900, 3350, 3750];
    const stageTimers = stageDelays.map((delay, idx) => setTimeout(() => setStageIndex(idx), delay));
    const exitTimer = setTimeout(() => setExiting(true), 4200);
    const doneTimer = setTimeout(complete, 4700);

    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') complete();
    };
    window.addEventListener('keydown', onKey);

    return () => {
      clearTimeout(hardStop);
      stageTimers.forEach(clearTimeout);
      clearTimeout(exitTimer);
      clearTimeout(doneTimer);
      window.removeEventListener('keydown', onKey);
    };
  }, [complete]);

  const [skippable, setSkippable] = useState(false);
  useEffect(() => {
    const t = setTimeout(() => setSkippable(true), 500);
    return () => clearTimeout(t);
  }, []);

  return (
    <motion.div
      className="fixed inset-0 z-[9999] flex items-center justify-center bg-dark overflow-hidden"
      initial={{ opacity: 1 }}
      animate={{ opacity: exiting ? 0 : 1 }}
      transition={{ duration: 0.5, ease: [0.16, 1, 0.3, 1] }}
    >
      {/* Barely-visible radial glow behind center */}
      <motion.div
        className="absolute inset-0"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ duration: 1.2, delay: 0.15 }}
        style={{ background: 'radial-gradient(circle at 50% 45%, rgba(59,130,246,0.06), transparent 55%)' }}
      />

      <div className="relative flex flex-col items-center px-6">
        {/* Symbol + orbit ring */}
        <div className="relative w-[220px] h-[220px] flex items-center justify-center">
          <OrbitRing />
          <motion.div
            className="animate-breathe"
            initial={{ opacity: 0, scale: 0.92, filter: 'blur(8px)' }}
            animate={{ opacity: 1, scale: 1, filter: 'blur(0px)' }}
            transition={{ duration: 1.0, ease: [0.16, 1, 0.3, 1] }}
            style={{ filter: 'drop-shadow(0 0 18px rgba(91,141,239,0.35))' }}
          >
            <TalosMark size={72} />
          </motion.div>
        </div>

        {/* Wordmark */}
        <motion.h1
          className="text-5xl font-black tracking-[0.12em] font-sans text-text-primary mt-3"
          initial={{ opacity: 0, y: 8, letterSpacing: '0.3em' }}
          animate={{ opacity: 1, y: 0, letterSpacing: '0.12em' }}
          transition={{ duration: 0.6, delay: 1.3, ease: [0.16, 1, 0.3, 1] }}
        >
          TALOS
        </motion.h1>

        <motion.p
          className="text-[11px] font-mono uppercase tracking-[0.25em] text-text-muted mt-2"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 0.5, delay: 1.85 }}
        >
          Autonomous Repository Maintenance
        </motion.p>

        {/* Status + progress */}
        <motion.div
          className="mt-10 w-[340px] sm:w-[440px] flex flex-col items-center"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 0.4, delay: 2.05 }}
        >
          <div className="text-xs font-mono text-text-secondary h-4">
            {stageIndex < STAGES.length - 1 ? `Initializing TALOS…` : 'TALOS Ready'}
          </div>

          <div className="w-full h-[2px] bg-white/[0.07] rounded-full mt-3 overflow-hidden">
            <motion.div
              className="h-full bg-blue-500/70 rounded-full"
              initial={{ width: '0%' }}
              animate={{ width: `${((stageIndex + 1) / STAGES.length) * 100}%` }}
              transition={{ duration: 0.35, ease: 'easeOut' }}
            />
          </div>

          <div className="flex items-center gap-2 mt-4">
            {STAGES.map((stage, idx) => (
              <React.Fragment key={stage}>
                {idx > 0 && <div className="w-3 h-px bg-white/10" />}
                <span
                  className={`text-[9px] font-mono uppercase tracking-wide whitespace-nowrap transition-colors duration-300 ${
                    idx < stageIndex
                      ? 'text-emerald-400/70'
                      : idx === stageIndex
                      ? 'text-blue-400'
                      : 'text-text-muted/50'
                  }`}
                >
                  {stage}
                </span>
              </React.Fragment>
            ))}
          </div>

          <div className="text-[10px] font-mono text-text-muted mt-6 h-3">
            {STATUS_LABELS[Math.min(stageIndex, STATUS_LABELS.length - 1)]}
          </div>
        </motion.div>
      </div>

      <AnimatePresence>
        {skippable && !exiting && (
          <motion.button
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={complete}
            className="absolute bottom-6 right-6 text-[11px] font-mono text-text-muted hover:text-text-secondary transition-colors"
          >
            Skip
          </motion.button>
        )}
      </AnimatePresence>
    </motion.div>
  );
};

/** Minimal, fast variant for prefers-reduced-motion — logo, short fade, done. */
const ReducedMotionBoot: React.FC<{ onComplete: () => void }> = ({ onComplete }) => {
  useEffect(() => {
    markInitialized();
    const t = setTimeout(onComplete, 400);
    return () => clearTimeout(t);
  }, [onComplete]);

  return (
    <div className="fixed inset-0 z-[9999] flex items-center justify-center bg-dark">
      <div className="flex flex-col items-center gap-3">
        <TalosMark size={56} />
        <span className="text-2xl font-black tracking-[0.12em] font-sans text-text-primary">TALOS</span>
      </div>
    </div>
  );
};

/**
 * Local to the boot sequence only. If the intro throws for any reason, this
 * swallows it and marks the intro "seen" rather than letting it bubble up to
 * the app-wide ErrorBoundary — which would otherwise blank out the already-
 * rendered landing page underneath over a purely cosmetic failure.
 */
class BootErrorBoundary extends React.Component<{ children: React.ReactNode }, { failed: boolean }> {
  state = { failed: false };
  static getDerivedStateFromError() {
    return { failed: true };
  }
  componentDidCatch() {
    markInitialized();
  }
  render() {
    return this.state.failed ? null : this.props.children;
  }
}

interface FirstBootExperienceProps {
  children: React.ReactNode;
}

/**
 * Cinematic first-boot sequence, isolated from the rest of the app on
 * purpose (App -> FirstBootExperience -> children) — safe to remove by
 * unwrapping, and it can never block access: any failure (localStorage
 * unavailable, animation error) falls straight through to `children`.
 */
export const FirstBootExperience: React.FC<FirstBootExperienceProps> = ({ children }) => {
  const reduceMotion = useReducedMotion();
  const [showIntro, setShowIntro] = useState<boolean>(() => {
    try {
      return shouldShowIntro();
    } catch {
      return false;
    }
  });

  const handleComplete = () => setShowIntro(false);

  return (
    <>
      {children}
      <BootErrorBoundary>
        <AnimatePresence>
          {showIntro &&
            (reduceMotion ? (
              <ReducedMotionBoot key="boot" onComplete={handleComplete} />
            ) : (
              <BootSequence key="boot" onComplete={handleComplete} />
            ))}
        </AnimatePresence>
      </BootErrorBoundary>
    </>
  );
};
