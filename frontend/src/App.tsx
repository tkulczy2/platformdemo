import { Routes, Route } from 'react-router-dom';
import AppShell from '@/components/layout/AppShell';
import DataUpload from '@/components/upload/DataUpload';
import ContractEditor from '@/components/contract/ContractEditor';
import ResultsDashboard from '@/components/dashboard/ResultsDashboard';
import DrilldownView from '@/components/drilldown/DrilldownView';
import ReconciliationView from '@/components/reconciliation/ReconciliationView';

export default function App() {
  return (
    <Routes>
      <Route element={<AppShell />}>
        <Route path="/" element={<DataUpload />} />
        <Route path="/contract" element={<ContractEditor />} />
        <Route path="/dashboard" element={<ResultsDashboard />} />
        <Route path="/drilldown/:stepNum/:memberId" element={<DrilldownView />} />
        <Route path="/drilldown/metric/:metricName" element={<DrilldownView />} />
        <Route path="/reconciliation" element={<ReconciliationView />} />
      </Route>
    </Routes>
  );
}
