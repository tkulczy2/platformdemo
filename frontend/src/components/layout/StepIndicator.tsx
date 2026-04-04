import { useLocation, Link } from 'react-router-dom';
import { classNames } from '@/utils/formatters';

interface Step {
  number: number;
  label: string;
  path: string;
  matchPaths: string[];
}

const PERFORMANCE_STEPS: Step[] = [
  { number: 1, label: 'Data Upload', path: '/', matchPaths: ['/'] },
  { number: 2, label: 'Contract Config', path: '/contract', matchPaths: ['/contract'] },
  { number: 3, label: 'Dashboard', path: '/dashboard', matchPaths: ['/dashboard'] },
  { number: 4, label: 'Drill-Down', path: '/dashboard', matchPaths: ['/drilldown'] },
  { number: 5, label: 'Reconciliation', path: '/reconciliation', matchPaths: ['/reconciliation'] },
];

const PANEL_STEPS: Step[] = [
  { number: 1, label: 'Attribution Surveillance', path: '/surveillance', matchPaths: ['/surveillance'] },
  { number: 2, label: 'Clinical Briefs', path: '/clinical', matchPaths: ['/clinical'] },
];

function stepStatus(step: Step, pathname: string, allSteps: Step[]): 'active' | 'completed' | 'upcoming' {
  const isMatch = step.matchPaths.some((p) =>
    p === '/' ? pathname === '/' : pathname.startsWith(p),
  );
  if (isMatch) return 'active';

  const activeIndex = allSteps.findIndex((s) =>
    s.matchPaths.some((p) => (p === '/' ? pathname === '/' : pathname.startsWith(p))),
  );
  if (activeIndex === -1) return 'upcoming';
  const thisIndex = allSteps.indexOf(step);
  return thisIndex < activeIndex ? 'completed' : 'upcoming';
}

interface StepIndicatorProps {
  panelActive: boolean;
}

export default function StepIndicator({ panelActive }: StepIndicatorProps) {
  const { pathname } = useLocation();
  const steps = panelActive ? PANEL_STEPS : PERFORMANCE_STEPS;

  return (
    <nav className="flex items-center gap-1" aria-label="Progress">
      {steps.map((step, i) => {
        const status = stepStatus(step, pathname, steps);
        return (
          <div key={step.number} className="flex items-center">
            <Link
              to={step.path}
              className={classNames(
                'flex items-center gap-2 rounded-lg px-3 py-1.5 text-xs font-medium transition-colors',
                status === 'active' && 'bg-brand-600 text-white shadow-sm',
                status === 'completed' && 'bg-brand-50 text-brand-700 hover:bg-brand-100',
                status === 'upcoming' && 'text-gray-400 hover:text-gray-600',
              )}
            >
              <span
                className={classNames(
                  'flex h-5 w-5 items-center justify-center rounded-full text-[10px] font-bold',
                  status === 'active' && 'bg-white/20 text-white',
                  status === 'completed' && 'bg-brand-200 text-brand-700',
                  status === 'upcoming' && 'bg-gray-200 text-gray-500',
                )}
              >
                {status === 'completed' ? (
                  <svg className="h-3 w-3" fill="currentColor" viewBox="0 0 20 20">
                    <path
                      fillRule="evenodd"
                      d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z"
                      clipRule="evenodd"
                    />
                  </svg>
                ) : (
                  step.number
                )}
              </span>
              <span className="hidden sm:inline">{step.label}</span>
            </Link>

            {i < steps.length - 1 && (
              <svg
                className="mx-1 h-4 w-4 flex-shrink-0 text-gray-300"
                fill="currentColor"
                viewBox="0 0 20 20"
              >
                <path
                  fillRule="evenodd"
                  d="M7.21 14.77a.75.75 0 01.02-1.06L11.168 10 7.23 6.29a.75.75 0 111.04-1.08l4.5 4.25a.75.75 0 010 1.08l-4.5 4.25a.75.75 0 01-1.06-.02z"
                  clipRule="evenodd"
                />
              </svg>
            )}
          </div>
        );
      })}
    </nav>
  );
}
