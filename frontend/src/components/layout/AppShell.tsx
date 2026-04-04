import { useState } from 'react';
import { Outlet, Link, useLocation, useNavigate } from 'react-router-dom';
import { classNames } from '@/utils/formatters';
import StepIndicator from './StepIndicator';
import GuidedDemo from '@/components/demo/GuidedDemo';

const PERFORMANCE_PATHS = ['/', '/contract', '/dashboard', '/drilldown', '/reconciliation'];
const PANEL_PATHS = ['/surveillance', '/clinical'];

function isPanelActive(pathname: string) {
  return PANEL_PATHS.some((p) => pathname.startsWith(p));
}

function isPerformanceActive(pathname: string) {
  return !isPanelActive(pathname);
}

export default function AppShell() {
  const [demoOpen, setDemoOpen] = useState(false);
  const { pathname } = useLocation();
  const navigate = useNavigate();

  const panelActive = isPanelActive(pathname);

  return (
    <div className="flex min-h-screen flex-col bg-gray-50">
      {/* ------------------------------------------------------------------ */}
      {/* Top navigation bar                                                  */}
      {/* ------------------------------------------------------------------ */}
      <header className="sticky top-0 z-30 border-b border-gray-200 bg-white/95 backdrop-blur supports-[backdrop-filter]:bg-white/80">
        <div className="mx-auto flex h-14 max-w-screen-2xl items-center justify-between px-4 sm:px-6 lg:px-8">
          {/* Brand */}
          <Link to="/" className="flex items-center gap-2.5 shrink-0">
            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-brand-600 text-white">
              <svg className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth={2.5} viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" d="M3 13.125C3 12.504 3.504 12 4.125 12h2.25c.621 0 1.125.504 1.125 1.125v6.75C7.5 20.496 6.996 21 6.375 21h-2.25A1.125 1.125 0 013 19.875v-6.75zM9.75 8.625c0-.621.504-1.125 1.125-1.125h2.25c.621 0 1.125.504 1.125 1.125v11.25c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 01-1.125-1.125V8.625zM16.5 4.125c0-.621.504-1.125 1.125-1.125h2.25C20.496 3 21 3.504 21 4.125v15.75c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 01-1.125-1.125V4.125z" />
              </svg>
            </div>
            <span className="text-sm font-semibold text-gray-900 tracking-tight whitespace-nowrap">
              Value Based Intelligence Platform
            </span>
          </Link>

          {/* Primary product tabs — centered */}
          <nav className="hidden md:flex items-center gap-1">
            <button
              onClick={() => { if (panelActive) navigate('/'); }}
              className={classNames(
                'rounded-md px-4 py-1.5 text-sm font-medium transition-colors',
                !panelActive
                  ? 'bg-brand-600 text-white shadow-sm'
                  : 'text-gray-600 hover:bg-gray-100 hover:text-gray-900',
              )}
            >
              Performance Intelligence
            </button>
            <button
              onClick={() => { if (!panelActive) navigate('/surveillance'); }}
              className={classNames(
                'rounded-md px-4 py-1.5 text-sm font-medium transition-colors',
                panelActive
                  ? 'bg-brand-600 text-white shadow-sm'
                  : 'text-gray-600 hover:bg-gray-100 hover:text-gray-900',
              )}
            >
              Panel Intelligence
            </button>
          </nav>

          {/* Right side — guided demo toggle */}
          <div className="flex items-center gap-2">
            <button
              onClick={() => setDemoOpen((o) => !o)}
              className={classNames(
                'inline-flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-medium transition-colors',
                demoOpen
                  ? 'bg-brand-600 text-white'
                  : 'bg-brand-50 text-brand-700 hover:bg-brand-100 ring-1 ring-inset ring-brand-200',
              )}
            >
              <svg className="h-3.5 w-3.5" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" d="M5.25 5.653c0-.856.917-1.398 1.667-.986l11.54 6.348a1.125 1.125 0 010 1.971l-11.54 6.347a1.125 1.125 0 01-1.667-.985V5.653z" />
              </svg>
              {demoOpen ? 'Demo Running' : 'Start Demo'}
            </button>
          </div>
        </div>

        {/* Sub-tab indicator bar */}
        <div className="mx-auto max-w-screen-2xl border-t border-gray-100 px-4 py-2 sm:px-6 lg:px-8">
          <StepIndicator panelActive={panelActive} />
        </div>
      </header>

      {/* ------------------------------------------------------------------ */}
      {/* Main content area                                                   */}
      {/* ------------------------------------------------------------------ */}
      <main className="flex-1">
        <div className="mx-auto max-w-screen-2xl px-4 py-6 sm:px-6 lg:px-8">
          <Outlet />
        </div>
      </main>

      {/* ------------------------------------------------------------------ */}
      {/* Footer                                                              */}
      {/* ------------------------------------------------------------------ */}
      <footer className="border-t border-gray-200 bg-white">
        <div className="mx-auto max-w-screen-2xl px-4 py-3 sm:px-6 lg:px-8">
          <p className="text-center text-xs text-gray-400">
            Value Based Intelligence Platform -- All data is synthetic. No real PHI.
          </p>
        </div>
      </footer>

      {/* Guided demo overlay */}
      <GuidedDemo isOpen={demoOpen} onClose={() => setDemoOpen(false)} />
    </div>
  );
}
