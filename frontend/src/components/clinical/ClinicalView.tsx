import { useState } from 'react';
import WeeklySchedule from './WeeklySchedule';
import PatientBrief from './PatientBrief';
import BriefDrilldown from './BriefDrilldown';
import WeekInReview from './WeekInReview';

type ClinicalScreen = 'schedule' | 'brief' | 'drilldown' | 'review';

interface DrilldownTarget {
  appointmentId: string;
  itemType: string;
  itemId: string;
}

export default function ClinicalView() {
  const [screen, setScreen] = useState<ClinicalScreen>('schedule');
  const [selectedAppointment, setSelectedAppointment] = useState<string | null>(null);
  const [drilldownTarget, setDrilldownTarget] = useState<DrilldownTarget | null>(null);

  function handleSelectAppointment(appointmentId: string) {
    setSelectedAppointment(appointmentId);
    setScreen('brief');
  }

  function handleDrilldown(appointmentId: string, itemType: string, itemId: string) {
    setDrilldownTarget({ appointmentId, itemType, itemId });
    setScreen('drilldown');
  }

  function handleBack() {
    if (screen === 'drilldown') {
      setScreen('brief');
    } else if (screen === 'brief') {
      setScreen('schedule');
    } else if (screen === 'review') {
      setScreen('schedule');
    }
  }

  return (
    <div>
      {screen === 'schedule' && (
        <WeeklySchedule
          onSelectAppointment={handleSelectAppointment}
          onShowReview={() => setScreen('review')}
        />
      )}
      {screen === 'brief' && selectedAppointment && (
        <PatientBrief
          appointmentId={selectedAppointment}
          onBack={handleBack}
          onDrilldown={(itemType, itemId) =>
            handleDrilldown(selectedAppointment, itemType, itemId)
          }
        />
      )}
      {screen === 'drilldown' && drilldownTarget && (
        <BriefDrilldown
          appointmentId={drilldownTarget.appointmentId}
          itemType={drilldownTarget.itemType}
          itemId={drilldownTarget.itemId}
          onBack={handleBack}
        />
      )}
      {screen === 'review' && <WeekInReview onBack={handleBack} />}
    </div>
  );
}
