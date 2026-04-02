import { useState } from 'react';
import { classNames } from '@/utils/formatters';

const OPTIONS = [
  { value: 'completed', label: 'Completed', description: 'Gap was closed during the encounter' },
  { value: 'patient_declined', label: 'Patient Declined', description: 'Patient was offered but declined' },
  { value: 'clinically_inappropriate', label: 'Clinically Inappropriate', description: 'Recommendation not applicable' },
  { value: 'already_addressed', label: 'Already Addressed', description: 'Data is stale — already done' },
];

interface Props {
  isOpen: boolean;
  onClose: () => void;
  onSubmit: (feedback: string, note: string) => void;
}

export default function FeedbackModal({ isOpen, onClose, onSubmit }: Props) {
  const [selected, setSelected] = useState<string>('');
  const [note, setNote] = useState('');

  if (!isOpen) return null;

  function handleSubmit() {
    if (selected) {
      onSubmit(selected, note);
      setSelected('');
      setNote('');
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30">
      <div className="w-full max-w-md rounded-xl bg-white shadow-xl p-6">
        <h3 className="text-sm font-semibold text-gray-900 mb-4">Provider Feedback</h3>

        <div className="space-y-2 mb-4">
          {OPTIONS.map((opt) => (
            <button
              key={opt.value}
              onClick={() => setSelected(opt.value)}
              className={classNames(
                'w-full text-left rounded-lg border p-3 transition-colors',
                selected === opt.value
                  ? 'border-teal-300 bg-teal-50'
                  : 'border-gray-200 hover:bg-gray-50',
              )}
            >
              <p className="text-sm font-medium text-gray-900">{opt.label}</p>
              <p className="text-xs text-gray-500">{opt.description}</p>
            </button>
          ))}
        </div>

        <textarea
          value={note}
          onChange={(e) => setNote(e.target.value)}
          placeholder="Optional note..."
          className="w-full rounded-lg border border-gray-200 px-3 py-2 text-xs text-gray-700 placeholder:text-gray-400 focus:border-teal-300 focus:ring-1 focus:ring-teal-300 mb-4"
          rows={2}
        />

        <div className="flex justify-end gap-2">
          <button
            onClick={onClose}
            className="rounded-lg px-3 py-1.5 text-xs font-medium text-gray-600 hover:bg-gray-100"
          >
            Cancel
          </button>
          <button
            onClick={handleSubmit}
            disabled={!selected}
            className="rounded-lg bg-teal-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-teal-700 disabled:opacity-50"
          >
            Submit
          </button>
        </div>
      </div>
    </div>
  );
}
