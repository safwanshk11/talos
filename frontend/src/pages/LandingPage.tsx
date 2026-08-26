import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { motion } from 'framer-motion';
import { Reveal } from '../components/ui/Reveal';
import {
  ShieldCheck,
  Search,
  Wrench,
  GitPullRequest,
  ArrowRight,
  CheckCircle2,
  UserCheck,
  Brain,
  Github,
  Lock,
} from 'lucide-react';

const NAV_LINKS = [
  { label: 'Product', href: '#product' },
  { label: 'How It Works', href: '#how-it-works' },
  { label: 'Security', href: '#security' },
];

const WORKFLOW_STAGES = [
  { icon: ShieldCheck, label: 'ISSUE DETECTED', detail: 'axios security vulnerability' },
  { icon: Wrench, label: 'PATCH PREPARED', detail: '2 files changed' },
  { icon: CheckCircle2, label: 'VERIFICATION PASSED', detail: 'Build · Tests · Audit' },
  { icon: GitPullRequest, label: 'PR CREATED', detail: '#42 Ready for review' },
];

function Navbar() {
  const [scrolled, setScrolled] = useState(false);
  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 12);
    window.addEventListener('scroll', onScroll);
    return () => window.removeEventListener('scroll', onScroll);
  }, []);

  return (
    <div className="fixed top-4 inset-x-0 z-50 flex justify-center px-4">
      <nav
        className={`glass-pill rounded-full flex items-center gap-1 pl-4 pr-1.5 py-1.5 transition-shadow duration-300 ${
          scrolled ? 'shadow-lift' : ''
        }`}
      >
        <div className="flex items-center gap-2 pr-4 mr-2 border-r border-subtle">
          <ShieldCheck className="w-4 h-4 text-blue-400" />
          <span className="font-bold text-sm tracking-wider font-mono text-text-primary">TALOS</span>
        </div>
        {NAV_LINKS.map((link) => (
          <a
            key={link.href}
            href={link.href}
            className="hidden sm:inline-block px-3 py-1.5 rounded-full text-xs font-medium text-text-secondary hover:text-text-primary hover:bg-white/5 transition-colors"
          >
            {link.label}
          </a>
        ))}
        <Link
          to="/login"
          className="px-3 py-1.5 rounded-full text-xs font-medium text-text-secondary hover:text-text-primary hover:bg-white/5 transition-colors"
        >
          Login
        </Link>
        <Link to="/app" className="btn btn-primary text-xs ml-1 rounded-full">
          Get Started
        </Link>
      </nav>
    </div>
  );
}

function HeroVisual() {
  const [active, setActive] = useState(0);
  useEffect(() => {
    const id = setInterval(() => setActive((a) => (a + 1) % WORKFLOW_STAGES.length), 2200);
    return () => clearInterval(id);
  }, []);

  return (
    <div className="relative w-full max-w-sm mx-auto">
      <div
        className="absolute inset-0 -z-10 blur-3xl opacity-20"
        style={{ background: 'radial-gradient(circle at 50% 30%, #3b82f6, transparent 60%)' }}
      />
      <div className="rounded-2xl border border-subtle bg-card/80 backdrop-blur-sm overflow-hidden shadow-lift">
        {WORKFLOW_STAGES.map((stage, idx) => {
          const Icon = stage.icon;
          const isActive = idx === active;
          const isDone = idx < active;
          return (
            <div
              key={stage.label}
              className={`relative flex items-center gap-3 px-4 py-4 ${
                idx !== WORKFLOW_STAGES.length - 1 ? 'border-b border-subtle' : ''
              }`}
            >
              {idx !== WORKFLOW_STAGES.length - 1 && (
                <div className="absolute left-[27px] top-full h-2 w-px bg-white/10" />
              )}
              <motion.div
                className={`w-7 h-7 rounded-full flex items-center justify-center shrink-0 border ${
                  isActive
                    ? 'bg-blue-500/15 border-blue-500/40 text-blue-400'
                    : isDone
                    ? 'bg-emerald-500/10 border-emerald-500/30 text-emerald-400'
                    : 'bg-white/[0.03] border-subtle text-text-muted'
                }`}
                animate={isActive ? { boxShadow: ['0 0 0 0 rgba(59,130,246,0.35)', '0 0 0 6px rgba(59,130,246,0)'] } : {}}
                transition={{ duration: 1.4, repeat: isActive ? Infinity : 0 }}
              >
                <Icon className="w-3.5 h-3.5" />
              </motion.div>
              <div className="min-w-0">
                <div className={`text-[11px] font-mono font-semibold tracking-wide truncate ${isActive ? 'text-text-primary' : 'text-text-secondary'}`}>
                  {stage.label}
                </div>
                <div className="text-[11px] text-text-muted truncate">{stage.detail}</div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

export const LandingPage: React.FC = () => {
  return (
    <div className="bg-dark text-text-primary min-h-screen overflow-x-hidden">
      <Navbar />

      {/* Hero */}
      <section className="relative pt-40 pb-28 px-6">
        <div
          className="absolute inset-0 -z-10 opacity-[0.04]"
          style={{
            backgroundImage:
              'linear-gradient(to right, #fff 1px, transparent 1px), linear-gradient(to bottom, #fff 1px, transparent 1px)',
            backgroundSize: '64px 64px',
            maskImage: 'radial-gradient(ellipse 80% 60% at 50% 0%, black 40%, transparent 100%)',
          }}
        />
        <div className="max-w-6xl mx-auto grid lg:grid-cols-2 gap-16 items-center">
          <div>
            <motion.div
              initial={{ opacity: 0, y: 16 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.6, ease: [0.16, 1, 0.3, 1] }}
            >
              <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full border border-subtle bg-white/[0.03] text-[11px] font-mono text-text-secondary mb-6">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
                Evidence over confidence — every patch is proven, not assumed
              </div>
              <h1 className="text-5xl sm:text-6xl font-bold tracking-tight leading-[1.05]">
                Autonomous maintenance.
                <br />
                <span className="text-blue-400">Human control.</span>
              </h1>
              <p className="text-base text-text-secondary mt-6 max-w-lg leading-relaxed">
                TALOS detects repository maintenance issues, prepares fixes, verifies them with
                real engineering checks, and delivers review-ready pull requests.
              </p>
              <div className="flex items-center gap-3 mt-8">
                <Link to="/app" className="btn btn-primary text-sm px-5 py-2.5">
                  <span>Get Started</span>
                  <ArrowRight className="w-4 h-4" />
                </Link>
                <a href="#how-it-works" className="btn btn-secondary text-sm px-5 py-2.5">
                  See How It Works
                </a>
              </div>
            </motion.div>
          </div>
          <motion.div
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ duration: 0.7, delay: 0.15, ease: [0.16, 1, 0.3, 1] }}
          >
            <HeroVisual />
          </motion.div>
        </div>
      </section>

      {/* Old way vs TALOS way */}
      <section id="product" className="py-24 px-6 border-t border-subtle">
        <div className="max-w-6xl mx-auto grid lg:grid-cols-2 gap-16 items-start">
          <Reveal>
            <div className="text-[11px] font-mono uppercase tracking-[0.18em] text-text-muted mb-3">
              The Old Way vs. The TALOS Way
            </div>
            <h2 className="text-3xl font-bold tracking-tight leading-tight">
              Stop maintaining.
              <br />
              Start reviewing.
            </h2>
            <p className="text-sm text-text-secondary mt-4 leading-relaxed max-w-md">
              Repository maintenance repeatedly interrupts development work: alerts,
              investigation, patches, testing, and pull requests — all by hand, every time.
            </p>
          </Reveal>
          <div className="grid sm:grid-cols-2 gap-4">
            <Reveal delay={0.05}>
              <div className="rounded-xl border border-red-500/15 bg-red-500/[0.03] p-5 h-full">
                <div className="text-xs font-mono font-semibold text-red-400/90 mb-4">THE OLD WAY</div>
                <ul className="space-y-3 text-sm text-text-secondary">
                  {['Security alert', 'Developer investigates', 'Patch written manually', 'Tests executed', 'PR prepared manually'].map((s) => (
                    <li key={s} className="flex items-center gap-2.5">
                      <span className="w-1 h-1 rounded-full bg-red-400/60 shrink-0" />
                      {s}
                    </li>
                  ))}
                </ul>
              </div>
            </Reveal>
            <Reveal delay={0.15}>
              <div className="rounded-xl border border-emerald-500/15 bg-emerald-500/[0.03] p-5 h-full">
                <div className="text-xs font-mono font-semibold text-emerald-400/90 mb-4">THE TALOS WAY</div>
                <ul className="space-y-3 text-sm text-text-secondary">
                  {['Issue detected', 'Patch prepared', 'Verified', 'PR delivered'].map((s) => (
                    <li key={s} className="flex items-center gap-2.5">
                      <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400 shrink-0" />
                      {s}
                    </li>
                  ))}
                </ul>
              </div>
            </Reveal>
          </div>
        </div>
      </section>

      {/* Autonomous workflows — stacked cards */}
      <section className="py-24 px-6 border-t border-subtle">
        <div className="max-w-4xl mx-auto text-center mb-16">
          <Reveal>
            <h2 className="text-3xl font-bold tracking-tight">
              Autonomous workflows
              <br />
              that do the work for you.
            </h2>
          </Reveal>
        </div>
        <div className="max-w-2xl mx-auto space-y-4">
          {[
            { icon: Search, title: 'Vulnerability Detection', desc: 'Real OSV advisory queries against your actual dependency manifests — no guessing.' },
            { icon: Brain, title: 'Patch Generation', desc: 'AI reasons about the fix; deterministic package-manager commands make the actual change.' },
            { icon: ShieldCheck, title: 'Deterministic Verification', desc: 'Sandboxed build, test, lint, and security-audit checks — real exit codes, not confidence scores.' },
            { icon: GitPullRequest, title: 'Pull Request Delivery', desc: 'The exact verified commit, pushed to its own branch, opened as a real PR. Never merged automatically.' },
          ].map((card, idx) => {
            const Icon = card.icon;
            return (
              <Reveal key={card.title} delay={idx * 0.08}>
                <div
                  className="rounded-xl border border-subtle bg-card p-5 flex items-center gap-4 card-interactive"
                  style={{ marginLeft: idx * 14, marginRight: idx * 14 }}
                >
                  <div className="w-10 h-10 rounded-lg bg-blue-500/10 border border-blue-500/20 text-blue-400 flex items-center justify-center shrink-0">
                    <Icon className="w-5 h-5" />
                  </div>
                  <div>
                    <div className="text-sm font-semibold text-text-primary">{card.title}</div>
                    <div className="text-xs text-text-muted mt-0.5">{card.desc}</div>
                  </div>
                </div>
              </Reveal>
            );
          })}
        </div>
      </section>

      {/* How it works */}
      <section id="how-it-works" className="py-24 px-6 border-t border-subtle">
        <div className="max-w-6xl mx-auto">
          <Reveal>
            <h2 className="text-3xl font-bold tracking-tight text-center mb-4">How TALOS works</h2>
            <p className="text-sm text-text-secondary text-center max-w-lg mx-auto mb-16">
              TALOS does the repetitive engineering work. The developer retains control.
            </p>
          </Reveal>
          <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-6">
            {[
              ['01', 'DETECT', 'Real OSV advisory scans against your dependency manifests.'],
              ['02', 'UNDERSTAND', 'Context gathered from the actual repository, not assumptions.'],
              ['03', 'PATCH', 'A deterministic dependency update, applied on an isolated branch.'],
              ['04', 'VERIFY', 'Install, build, lint, test, and audit — inside a disposable sandbox.'],
              ['05', 'DELIVER', 'The verified commit, pushed and opened as a real GitHub pull request.'],
              ['06', 'YOU REVIEW', 'TALOS never merges. You decide what ships.'],
            ].map(([num, title, desc], idx) => (
              <Reveal key={title} delay={idx * 0.06}>
                <div className="p-5 rounded-xl border border-subtle bg-white/[0.015]">
                  <div className="text-2xl font-mono font-bold text-white/10 mb-3">{num}</div>
                  <div className="text-sm font-semibold text-text-primary tracking-wide">{title}</div>
                  <p className="text-xs text-text-muted mt-1.5 leading-relaxed">{desc}</p>
                </div>
              </Reveal>
            ))}
          </div>
        </div>
      </section>

      {/* Verification */}
      <section id="security" className="py-24 px-6 border-t border-subtle">
        <div className="max-w-3xl mx-auto grid lg:grid-cols-2 gap-12 items-center">
          <Reveal>
            <div className="text-[11px] font-mono uppercase tracking-[0.18em] text-text-muted mb-3">
              Why TALOS is different
            </div>
            <h2 className="text-3xl font-bold tracking-tight leading-tight">
              Proof, not confidence.
            </h2>
            <p className="text-sm text-text-secondary mt-4 leading-relaxed">
              AI-generated code is untrusted until it's verified with real engineering checks.
              TALOS never fabricates a test count or a passing grade — only what actually ran,
              actually reported.
            </p>
            <div className="flex items-center gap-2 mt-6 text-xs text-text-muted">
              <Lock className="w-3.5 h-3.5" />
              <span>Verification runs in an isolated sandbox with zero access to your credentials.</span>
            </div>
          </Reveal>
          <Reveal delay={0.1}>
            <div className="rounded-xl border border-subtle bg-card overflow-hidden">
              <div className="px-4 py-3 border-b border-subtle text-[11px] font-mono uppercase tracking-wide text-text-muted">
                Verification Report
              </div>
              <div className="divide-y divide-white/[0.06]">
                {[
                  ['Build', 'PASS'],
                  ['Tests', 'PASS'],
                  ['Type Check', 'PASS'],
                  ['Security Audit', 'PASS'],
                  ['Original Issue', 'REMOVED'],
                ].map(([label, result], idx) => (
                  <Reveal key={label} delay={0.15 + idx * 0.08}>
                    <div className="px-4 py-2.5 flex items-center justify-between text-xs font-mono">
                      <span className="text-text-secondary">{label}</span>
                      <span className="text-emerald-400 font-semibold flex items-center gap-1.5">
                        <CheckCircle2 className="w-3.5 h-3.5" />
                        {result}
                      </span>
                    </div>
                  </Reveal>
                ))}
              </div>
              <div className="px-4 py-3 bg-emerald-500/[0.06] border-t border-emerald-500/15 text-xs font-mono font-semibold text-emerald-400 text-center">
                PATCH VERIFIED
              </div>
            </div>
          </Reveal>
        </div>
      </section>

      {/* Final CTA */}
      <section className="py-32 px-6 border-t border-subtle text-center">
        <Reveal>
          <h2 className="text-4xl font-bold tracking-tight max-w-lg mx-auto leading-tight">
            Ready to stop maintaining and start reviewing?
          </h2>
          <p className="text-sm text-text-secondary mt-4 max-w-md mx-auto">
            Connect a repository and let TALOS handle the repetitive maintenance workflow.
          </p>
          <Link to="/app" className="btn btn-primary text-sm px-6 py-3 mt-8 inline-flex">
            <Github className="w-4 h-4" />
            <span>Connect GitHub</span>
            <ArrowRight className="w-4 h-4" />
          </Link>
        </Reveal>
      </section>

      {/* Footer */}
      <footer className="border-t border-subtle py-10 px-6">
        <div className="max-w-6xl mx-auto flex flex-col sm:flex-row items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-2">
              <ShieldCheck className="w-4 h-4 text-blue-400" />
              <span className="font-bold text-sm font-mono">TALOS</span>
            </div>
            <p className="text-xs text-text-muted mt-1">Autonomous. Verified. Delivered.</p>
          </div>
          <div className="flex items-center gap-6 text-xs text-text-muted">
            <a href="https://github.com" target="_blank" rel="noreferrer" className="hover:text-text-primary transition-colors flex items-center gap-1.5">
              <UserCheck className="w-3.5 h-3.5" /> GitHub
            </a>
            <a href="#security" className="hover:text-text-primary transition-colors">Security</a>
          </div>
        </div>
      </footer>
    </div>
  );
};
