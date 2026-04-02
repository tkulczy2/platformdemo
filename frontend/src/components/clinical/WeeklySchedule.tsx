import { useEffect, useState } from 'react';
import { getClinicalSchedule } from '@/api/client';
import { classNames } from '@/utils/formatters';

const ROLE_BADGE: Record<string, string> = {
  crossover_patient: 'ring-2 ring-purple-400',
  feedback_patient: 'ring-2 ring-teal-400',
};

interface Props {
  onSelectAppointment: (id: string) => void;
  onShowReview: () => void;
}

export default function WeeklySchedule({ onSelectAppointment, onShowReview }: Props) {
  const [schedule, setSchedule] = useState<Record<string, unknown> | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    (async () => {
      try {
        const data = await getClinicalSchedule();
        setSchedule(data as unknown as Record<string, unknown>);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load schedule');
      } finally {
        setLoading(false);
      }
    })();
  }, []);

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[40vh]">
        <span className="text-sm text-gray-500">Loading clinical schedule...</span>
      </div>
    );
  }

  if (error || !schedule) {
    return (
      <div className="rounded-lg border border-red-200 bg-red-50 p-6 text-center">
        <p className="text-sm text-red-700 mb-2">{error || 'No schedule data'}</p>
        <p className="text-xs text-red-500">Run the pipeline and generate the schedule first.</p>
      </div>
    );
  }

  const week = schedule.schedule_week as Record<string, unknown>;
  const days = schedule.days as Array<Record<string, unknown>>;
  const providers = (week.providers as Array<Record<string, unknown>>) || [];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-lg font-semibold text-gray-900">
            {week.practice_name as string}
          </h2>
          <p className="text-sm text-gray-500">
            Week of {week.start_date as string} — {week.end_date as string}
          </p>
          <div className="flex gap-4 mt-1">
            {providers.map((p) => (
              <span key={p.npi as string} className="text-xs text-gray-400">
                {p.name as string} ({p.panel_size as number} patients)
              </span>
            ))}
          </div>
        </div>
        <button
          onClick={onShowReview}
          className="inline-flex items-center gap-1.5 rounded-lg bg-teal-50 px-3 py-1.5 text-xs font-medium text-teal-700 hover:bg-teal-100 ring-1 ring-inset ring-teal-200"
        >
          Week in Review
        </button>
      </div>

      {/* Day columns */}
      <div className="grid grid-cols-5 gap-3">
        {days.map((day) => {
          const apts = (day.appointments as Array<Record<string, unknown>>) || [];
          return (
            <div
              key={day.date as string}
              className="rounded-xl border border-gray-200 bg-white overflow-hidden"
            >
              <div className="border-b border-gray-100 bg-gray-50 px-3 py-2">
                <p className="text-sm font-semibold text-gray-900">
                  {day.day_name as string}
                </p>
                <p className="text-xs text-gray-400">{day.date as string}</p>
                <p className="text-[10px] text-gray-400 italic mt-0.5">
                  {day.narrative_theme as string}
                </p>
                <span className="inline-flex items-center rounded-full bg-gray-200 px-1.5 py-0.5 text-[10px] font-medium text-gray-600 mt-1">
                  {apts.length} patients
                </span>
              </div>
              <div className="divide-y divide-gray-50 max-h-[60vh] overflow-y-auto">
                {apts.map((apt) => {
                  const role = apt.demo_role as string;
                  return (
                    <button
                      key={apt.appointment_id as string}
                      onClick={() => onSelectAppointment(apt.appointment_id as string)}
                      className={classNames(
                        'w-full text-left px-3 py-2 hover:bg-teal-50 transition-colors',
                        ROLE_BADGE[role] || '',
                      )}
                    >
                      <div className="flex items-center justify-between">
                        <span className="text-xs font-mono text-gray-500">
                          {apt.time as string}
                        </span>
                        <span className="h-2 w-2 rounded-full bg-green-400" />
                      </div>
                      <p className="text-xs text-gray-700 mt-0.5 truncate">
                        {apt.member_id as string}
                      </p>
                      <p className="text-[10px] text-gray-400 truncate">
                        {apt.appointment_type as string}
                      </p>
                    </button>
                  );
                })}
              </div>
            </div>
          );
        })}
      </div>

      {/* Legend */}
      <div className="flex items-center gap-4 text-[10px] text-gray-400">
        <span className="flex items-center gap-1"><span className="h-2 w-2 rounded-full bg-green-400" /> Stable</span>
        <span className="flex items-center gap-1"><span className="h-2 w-2 rounded-full bg-yellow-400" /> Moderate Risk</span>
        <span className="flex items-center gap-1"><span className="h-2 w-2 rounded-full bg-red-400" /> High Risk</span>
        <span className="flex items-center gap-1"><span className="h-2 w-2 rounded-full bg-blue-400" /> New to Panel</span>
      </div>
    </div>
  );
}
