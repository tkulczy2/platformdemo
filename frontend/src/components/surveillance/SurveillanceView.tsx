import { useState } from 'react';
import { classNames } from '@/utils/formatters';
import PanelOverview from './PanelOverview';
import ProviderPanels from './ProviderPanels';
import RetentionWorklist from './RetentionWorklist';
import FinancialImpact from './FinancialImpact';
import ProjectionView from './ProjectionView';

type Screen = 'overview' | 'providers' | 'worklist' | 'financial' | 'projections';

const TABS: { key: Screen; label: string }[] = [
  { key: 'overview', label: 'Panel Overview' },
  { key: 'providers', label: 'Provider Panels' },
  { key: 'worklist', label: 'Retention Worklist' },
  { key: 'financial', label: 'Financial Impact' },
  { key: 'projections', label: 'Projections' },
];

export default function SurveillanceView() {
  const [screen, setScreen] = useState<Screen>('overview');
  const [selectedProvider, setSelectedProvider] = useState<string | null>(null);

  function handleProviderSelect(npi: string) {
    setSelectedProvider(npi);
  }

  return (
    <div className="space-y-4">
      {/* Sub-navigation */}
      <div className="border-b border-gray-200">
        <nav className="-mb-px flex gap-4">
          {TABS.map((tab) => (
            <button
              key={tab.key}
              onClick={() => setScreen(tab.key)}
              className={classNames(
                'whitespace-nowrap border-b-2 px-1 py-3 text-sm font-medium transition-colors',
                screen === tab.key
                  ? 'border-slate-700 text-slate-900'
                  : 'border-transparent text-gray-500 hover:border-gray-300 hover:text-gray-700',
              )}
            >
              {tab.label}
            </button>
          ))}
        </nav>
      </div>

      {/* Content */}
      {screen === 'overview' && <PanelOverview />}
      {screen === 'providers' && (
        <ProviderPanels
          selectedNpi={selectedProvider}
          onSelectProvider={handleProviderSelect}
        />
      )}
      {screen === 'worklist' && <RetentionWorklist />}
      {screen === 'financial' && <FinancialImpact />}
      {screen === 'projections' && <ProjectionView />}
    </div>
  );
}
