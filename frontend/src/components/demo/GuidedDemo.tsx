import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { classNames } from '@/utils/formatters';

interface GuidedDemoProps {
  isOpen: boolean;
  onClose: () => void;
}

interface DemoStep {
  title: string;
  description: string;
  actionHint?: string;
  targetPath: string;
}

const STEPS: DemoStep[] = [
  // ── Performance Intelligence ──────────────────────────────────────────────
  {
    title: 'Welcome to the Value Based Intelligence Platform',
    description:
      'This platform demonstrates how a neutral calculation layer can transparently compute VBC performance metrics — and deliver those insights to every audience that needs them. Every number can be traced back to its source data, governing contract language, and executing code.',
    targetPath: '/',
  },
  {
    title: 'Load the Data',
    description:
      'Start by loading demo data — synthetic claims, eligibility, clinical records, and provider rosters for 1,000 Medicare beneficiaries. The platform validates each file and scores data quality automatically.',
    actionHint: 'Click "Load Demo Data" to populate the platform with synthetic data.',
    targetPath: '/',
  },
  {
    title: 'Review the Contract',
    description:
      'The contract defines the rules: how members are attributed, which quality measures are evaluated, how costs are calculated, and the shared savings formula. Every parameter is editable — and changes re-run the affected calculations.',
    actionHint: 'Click "Load Sample Contract" to load an MSSP-style contract, then review the attribution and quality parameters.',
    targetPath: '/contract',
  },
  {
    title: 'Run the Calculation',
    description:
      'The pipeline executes six transparent steps: eligibility filtering, provider attribution, quality measurement, cost calculation, settlement modeling, and payer reconciliation. Each step produces a full provenance trail.',
    actionHint: 'Click "Calculate" to run the full pipeline and watch the metrics populate on the dashboard.',
    targetPath: '/dashboard',
  },
  {
    title: 'Explore a Number',
    description:
      'Every metric on the dashboard is clickable. The three-panel drill-down view shows the contract language that governs the calculation, the data and logic that produced the result, and the exact code that executed it.',
    actionHint: 'Click any metric card to open the drill-down view with contract, logic, and code panels.',
    targetPath: '/dashboard',
  },
  {
    title: "Load the Payer's Report",
    description:
      "Upload the payer's settlement report and the platform automatically compares it against its own calculations. Discrepancies in attribution, quality measures, and cost are surfaced with root-cause explanations.",
    actionHint: 'Click "Load Demo Payer Report" to load a pre-built settlement report with intentional discrepancies.',
    targetPath: '/reconciliation',
  },
  {
    title: 'Find the Discrepancies',
    description:
      'The reconciliation view shows every difference between the platform and payer calculations. Each discrepancy links to the specific members, data rows, and contract clauses involved — enabling evidence-based dispute resolution.',
    actionHint: 'Drill into a discrepancy category to see per-member details and the data driving each difference.',
    targetPath: '/reconciliation',
  },
  {
    title: 'What If We Change the Rules?',
    description:
      'Go back to the contract, change a parameter — like the attribution method, quality measure weights, or minimum savings rate — and recalculate. Instantly see how different contract terms change outcomes. This is the power of a transparent calculation layer.',
    actionHint: 'Navigate to Contract, adjust a parameter, then recalculate to see the impact.',
    targetPath: '/contract',
  },

  // ── Panel Intelligence: Attribution Surveillance ──────────────────────────
  {
    title: 'Panel Intelligence: Attribution Is a Moving Target',
    description:
      'Attribution does not stand still between performance years. Members transfer providers, lapse eligibility, and get claimed by competing ACOs — each event carrying direct financial consequences. The Attribution Surveillance tab makes panel dynamics visible in real time.',
    targetPath: '/surveillance',
  },
  {
    title: 'Panel Overview: Know Your Exposure',
    description:
      'The Panel Overview surfaces the headline numbers a VP of Population Health or CFO needs first: how many members are at risk of leaving, what dollar exposure that represents, and how your panel\'s churn compares to benchmark. The attribution timeline shows net panel change month by month.',
    actionHint: 'Click a bar in the attribution timeline to filter the change events table to that month.',
    targetPath: '/surveillance',
  },
  {
    title: 'Provider Panels: Who Carries the Risk?',
    description:
      'Provider Panels ranks each physician by financial exposure — not just panel size. Cards flag providers with cascade risk (where losing one anchor patient could trigger a chain of losses) so retention efforts can be targeted where they matter most.',
    actionHint: 'Click any provider card to drill into that provider\'s specific change events and at-risk member list.',
    targetPath: '/surveillance',
  },
  {
    title: 'Retention Worklist: Prioritized by ROI',
    description:
      'The Retention Worklist ranks every at-risk member by return on intervention — financial exposure minus estimated outreach cost, divided by likelihood of retention. The highest-value actions surface first. Urgency filters and expand rows show exactly what is at stake for each member.',
    actionHint: 'Expand a worklist row to see member details. Use the urgency filter to focus on critical cases.',
    targetPath: '/surveillance',
  },
  {
    title: 'Financial Impact & Projections: The CFO Story',
    description:
      'The Financial Impact tab translates attribution churn into cumulative settlement impact — exposure, intervention cost, and expected recovery on one chart. The Projections tab models three scenarios (current trajectory, with intervention, worst case) so leadership can quantify the value of acting now versus waiting.',
    actionHint: 'Switch between the Financial Impact and Projections tabs to see scenario modeling.',
    targetPath: '/surveillance',
  },

  // ── Panel Intelligence: Clinical Briefs ───────────────────────────────────
  {
    title: 'Clinical Briefs: One Engine, Two Audiences',
    description:
      'The same calculation pipeline that powers the CFO\'s reconciliation report also powers the clinician\'s pre-visit brief — translated into plain clinical language. This is Panel Intelligence: delivering the right insight to the right person at the right moment.',
    targetPath: '/clinical',
  },
  {
    title: 'Weekly Schedule: The Panel at a Glance',
    description:
      'The weekly schedule shows every patient appointment across the practice week. Each slot surfaces the member\'s visit type and attribution risk at a glance. Special indicators flag crossover patients (who also appear in the reconciliation view) and the feedback patient for the interactive demo.',
    actionHint: 'Click any appointment slot to open the pre-visit patient brief.',
    targetPath: '/clinical',
  },
  {
    title: 'Pre-Visit Brief: Closing Gaps in the Exam Room',
    description:
      'The patient brief gives the clinician a ranked action list before the visit starts: quality gaps that can be closed today, HCC conditions that need documentation, and cost context so the provider understands the member\'s financial footprint. Priority actions are scored by financial impact, urgency, closability, and time pressure.',
    actionHint: 'Click a priority action or care gap row to open the three-panel provenance drill-down.',
    targetPath: '/clinical',
  },
  {
    title: 'Provenance in the Exam Room',
    description:
      'Every recommendation in the brief is traceable. Clicking a priority action opens the same three-panel drill-down used in the finance view — contract language, data interpretation, and source code — now reframed in clinical terms. Trust is built by showing your work, whether the audience is a CFO or a physician.',
    actionHint: 'Click any item in the brief to see the contract, data, and code that produced that recommendation.',
    targetPath: '/clinical',
  },
  {
    title: 'Week in Review: Closing the Loop',
    description:
      'The Week in Review aggregates the practice\'s performance across all scheduled visits: gaps closed, at-risk encounters, quality measure progress, and cost benchmarking. It closes the loop between individual visit actions and panel-level financial outcomes — the same outcomes measured in the Performance Intelligence tab.',
    actionHint: 'Click "Week in Review" in the schedule header to see aggregate weekly statistics.',
    targetPath: '/clinical',
  },
];

export default function GuidedDemo({ isOpen, onClose }: GuidedDemoProps) {
  const [currentStep, setCurrentStep] = useState(0);
  const navigate = useNavigate();

  const step = STEPS[currentStep];
  const totalSteps = STEPS.length;
  const isFirst = currentStep === 0;
  const isLast = currentStep === totalSteps - 1;
  const progressPct = ((currentStep + 1) / totalSteps) * 100;

  // Navigate to the target path when the step changes
  useEffect(() => {
    if (isOpen && step.targetPath) {
      navigate(step.targetPath);
    }
  }, [currentStep, isOpen, step.targetPath, navigate]);

  // Reset to first step when opened
  useEffect(() => {
    if (isOpen) {
      setCurrentStep(0);
    }
  }, [isOpen]);

  if (!isOpen) return null;

  function handlePrevious() {
    if (!isFirst) setCurrentStep((s) => s - 1);
  }

  function handleNext() {
    if (!isLast) setCurrentStep((s) => s + 1);
  }

  function handleFinish() {
    onClose();
  }

  function handleDotClick(index: number) {
    setCurrentStep(index);
  }

  return (
    <div className="fixed inset-x-0 bottom-6 z-50 flex justify-center pointer-events-none">
      <div className="pointer-events-auto w-full max-w-lg mx-4 rounded-xl border border-brand-200 bg-white shadow-2xl">
        {/* Progress bar */}
        <div className="h-1 w-full overflow-hidden rounded-t-xl bg-brand-100">
          <div
            className="h-full bg-brand-600 transition-all duration-300 ease-in-out"
            style={{ width: `${progressPct}%` }}
          />
        </div>

        {/* Header: step counter + close button */}
        <div className="flex items-center justify-between px-5 pt-3 pb-1">
          <span className="text-xs font-medium text-brand-600">
            Step {currentStep + 1} of {totalSteps}
          </span>
          <button
            type="button"
            onClick={onClose}
            className="rounded-md p-1 text-gray-400 hover:bg-gray-100 hover:text-gray-600 transition-colors"
            aria-label="Close guided demo"
          >
            <svg className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Step content */}
        <div className="px-5 pb-3">
          <h3 className="text-base font-semibold text-gray-900 leading-snug">{step.title}</h3>
          <p className="mt-1.5 text-sm text-gray-600 leading-relaxed">{step.description}</p>

          {/* Action hint */}
          {step.actionHint && (
            <div className="mt-3 rounded-lg bg-brand-50 border border-brand-100 px-3 py-2">
              <p className="text-sm font-medium text-brand-800">{step.actionHint}</p>
            </div>
          )}
        </div>

        {/* Footer: nav buttons + dots */}
        <div className="flex items-center justify-between border-t border-gray-100 px-5 py-3">
          {/* Previous */}
          <button
            type="button"
            onClick={handlePrevious}
            disabled={isFirst}
            className={classNames(
              'rounded-md px-3 py-1.5 text-sm font-medium transition-colors',
              isFirst
                ? 'text-gray-300 cursor-not-allowed'
                : 'text-gray-600 hover:bg-gray-100 hover:text-gray-900',
            )}
          >
            Previous
          </button>

          {/* Step dots */}
          <div className="flex items-center gap-1.5">
            {STEPS.map((_, index) => (
              <button
                key={index}
                type="button"
                onClick={() => handleDotClick(index)}
                aria-label={`Go to step ${index + 1}`}
                className={classNames(
                  'h-2 w-2 rounded-full transition-all duration-200',
                  index === currentStep
                    ? 'bg-brand-600 scale-125'
                    : index < currentStep
                      ? 'bg-brand-300 hover:bg-brand-400'
                      : 'bg-gray-200 hover:bg-gray-300',
                )}
              />
            ))}
          </div>

          {/* Next / Finish */}
          {isLast ? (
            <button
              type="button"
              onClick={handleFinish}
              className="rounded-md bg-brand-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-brand-700 transition-colors"
            >
              Finish
            </button>
          ) : (
            <button
              type="button"
              onClick={handleNext}
              className="rounded-md bg-brand-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-brand-700 transition-colors"
            >
              Next
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
