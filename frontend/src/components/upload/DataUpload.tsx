import { useState, useCallback, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { loadDemoData, uploadData, getDataStatus } from '@/api/client';
import { FileQualityScore } from '@/types';
import { classNames, formatPercent } from '@/utils/formatters';
import DataQualityCard from './DataQualityCard';

/** The nine expected file types in order. */
const EXPECTED_FILES = [
  { key: 'members.csv', label: 'Members' },
  { key: 'providers.csv', label: 'Providers' },
  { key: 'eligibility.csv', label: 'Eligibility' },
  { key: 'claims_professional.csv', label: 'Professional Claims' },
  { key: 'claims_facility.csv', label: 'Facility Claims' },
  { key: 'claims_pharmacy.csv', label: 'Pharmacy Claims' },
  { key: 'lab_results.csv', label: 'Lab Results' },
  { key: 'screenings.csv', label: 'Screenings' },
  { key: 'vitals.csv', label: 'Vitals' },
] as const;

export default function DataUpload() {
  const navigate = useNavigate();
  const fileInputRef = useRef<HTMLInputElement>(null);

  const [loading, setLoading] = useState(false);
  const [loadingMessage, setLoadingMessage] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [files, setFiles] = useState<Record<string, FileQualityScore> | null>(null);
  const [overallQuality, setOverallQuality] = useState<number | null>(null);
  const [ready, setReady] = useState(false);
  const [dragOver, setDragOver] = useState(false);

  // -----------------------------------------------------------------------
  // Fetch data status after loading / uploading
  // -----------------------------------------------------------------------
  const fetchStatus = useCallback(async () => {
    const status = await getDataStatus();
    setFiles(status.files as unknown as Record<string, FileQualityScore>);
    setOverallQuality(status.overall_quality);
    setReady(status.ready);
  }, []);

  // -----------------------------------------------------------------------
  // Load demo data
  // -----------------------------------------------------------------------
  const handleLoadDemo = useCallback(async () => {
    setLoading(true);
    setLoadingMessage('Loading synthetic demo data...');
    setError(null);
    try {
      await loadDemoData();
      await fetchStatus();
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load demo data');
    } finally {
      setLoading(false);
      setLoadingMessage('');
    }
  }, [fetchStatus]);

  // -----------------------------------------------------------------------
  // Upload CSV files
  // -----------------------------------------------------------------------
  const handleUpload = useCallback(
    async (fileList: FileList | File[]) => {
      const csvFiles = Array.from(fileList).filter(
        (f) => f.name.endsWith('.csv') || f.type === 'text/csv',
      );
      if (csvFiles.length === 0) {
        setError('Please select CSV files to upload.');
        return;
      }
      setLoading(true);
      setLoadingMessage(`Uploading ${csvFiles.length} file${csvFiles.length > 1 ? 's' : ''}...`);
      setError(null);
      try {
        await uploadData(csvFiles);
        await fetchStatus();
      } catch (e) {
        setError(e instanceof Error ? e.message : 'Upload failed');
      } finally {
        setLoading(false);
        setLoadingMessage('');
      }
    },
    [fetchStatus],
  );

  // -----------------------------------------------------------------------
  // Drag-and-drop handlers
  // -----------------------------------------------------------------------
  const onDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(true);
  }, []);

  const onDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(false);
  }, []);

  const onDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setDragOver(false);
      if (e.dataTransfer.files.length > 0) {
        handleUpload(e.dataTransfer.files);
      }
    },
    [handleUpload],
  );

  const onFileInputChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      if (e.target.files && e.target.files.length > 0) {
        handleUpload(e.target.files);
      }
    },
    [handleUpload],
  );

  // -----------------------------------------------------------------------
  // Derived state
  // -----------------------------------------------------------------------
  const loadedFileKeys = files ? Object.keys(files) : [];
  const dataLoaded = loadedFileKeys.length > 0;

  return (
    <div className="space-y-8">
      {/* Page header */}
      <div>
        <h1>Data Upload</h1>
        <p className="mt-1 text-gray-500">
          Upload claims, eligibility, clinical, and provider data files — or load the built-in demo
          dataset to explore the platform immediately.
        </p>
      </div>

      {/* ----------------------------------------------------------------- */}
      {/* Demo data CTA */}
      {/* ----------------------------------------------------------------- */}
      <div className="card">
        <div className="card-body flex flex-col items-center text-center py-8 gap-4">
          <div className="rounded-full bg-brand-50 p-3">
            <svg
              className="h-8 w-8 text-brand-600"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
              strokeWidth={1.5}
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M3.75 13.5l10.5-11.25L12 10.5h8.25L9.75 21.75 12 13.5H3.75z"
              />
            </svg>
          </div>
          <div>
            <h2 className="text-lg font-semibold text-gray-900">Quick Start with Demo Data</h2>
            <p className="mt-1 text-sm text-gray-500 max-w-md">
              Load 1,000 synthetic Medicare beneficiaries with claims, lab results, and provider
              data. All data is pre-generated and deterministic.
            </p>
          </div>
          <button
            onClick={handleLoadDemo}
            disabled={loading}
            className="btn-primary px-8 py-3 text-base"
          >
            {loading && loadingMessage.includes('demo') ? (
              <>
                <Spinner />
                Loading Demo Data...
              </>
            ) : (
              'Load Demo Data'
            )}
          </button>
        </div>
      </div>

      {/* ----------------------------------------------------------------- */}
      {/* File upload zone */}
      {/* ----------------------------------------------------------------- */}
      <div className="card">
        <div className="card-header">
          <h2 className="text-base font-semibold text-gray-900">Upload Your Data</h2>
          <p className="mt-0.5 text-xs text-gray-500">
            Drag and drop CSV files, or click to browse. Multiple files can be uploaded at once.
          </p>
        </div>
        <div className="card-body">
          <div
            onDragOver={onDragOver}
            onDragLeave={onDragLeave}
            onDrop={onDrop}
            onClick={() => fileInputRef.current?.click()}
            className={classNames(
              'relative flex flex-col items-center justify-center rounded-lg border-2 border-dashed px-6 py-10 cursor-pointer transition-colors',
              dragOver
                ? 'border-brand-400 bg-brand-50'
                : 'border-gray-300 hover:border-gray-400 bg-gray-50/50',
            )}
          >
            <svg
              className={classNames(
                'h-10 w-10 mb-3',
                dragOver ? 'text-brand-500' : 'text-gray-400',
              )}
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
              strokeWidth={1.5}
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M12 16.5V9.75m0 0l3 3m-3-3l-3 3M6.75 19.5a4.5 4.5 0 01-1.41-8.775 5.25 5.25 0 0110.233-2.33 3 3 0 013.758 3.848A3.752 3.752 0 0118 19.5H6.75z"
              />
            </svg>
            <p className="text-sm text-gray-600">
              <span className="font-semibold text-brand-600">Click to upload</span> or drag and
              drop
            </p>
            <p className="mt-1 text-xs text-gray-400">CSV files only</p>
            <input
              ref={fileInputRef}
              type="file"
              accept=".csv,text/csv"
              multiple
              className="hidden"
              onChange={onFileInputChange}
            />
            {loading && loadingMessage.includes('Uploading') && (
              <div className="absolute inset-0 flex items-center justify-center rounded-lg bg-white/80">
                <div className="flex items-center gap-2 text-sm text-brand-700 font-medium">
                  <Spinner />
                  {loadingMessage}
                </div>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* ----------------------------------------------------------------- */}
      {/* File checklist */}
      {/* ----------------------------------------------------------------- */}
      <div className="card">
        <div className="card-header">
          <h2 className="text-base font-semibold text-gray-900">Expected Files</h2>
        </div>
        <div className="card-body">
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-x-6 gap-y-2">
            {EXPECTED_FILES.map(({ key, label }) => {
              const loaded = loadedFileKeys.includes(key);
              return (
                <label key={key} className="flex items-center gap-2 py-1 text-sm">
                  <span
                    className={classNames(
                      'flex h-5 w-5 items-center justify-center rounded border transition-colors',
                      loaded
                        ? 'bg-emerald-500 border-emerald-500 text-white'
                        : 'border-gray-300 bg-white',
                    )}
                  >
                    {loaded && (
                      <svg className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={3}>
                        <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
                      </svg>
                    )}
                  </span>
                  <span className={loaded ? 'text-gray-900 font-medium' : 'text-gray-500'}>
                    {label}
                  </span>
                  <span className="text-xs text-gray-400 font-mono">{key}</span>
                </label>
              );
            })}
          </div>
        </div>
      </div>

      {/* ----------------------------------------------------------------- */}
      {/* Error banner */}
      {/* ----------------------------------------------------------------- */}
      {error && (
        <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 flex items-start gap-3">
          <svg
            className="h-5 w-5 text-red-500 mt-0.5 shrink-0"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
            strokeWidth={2}
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126zM12 15.75h.007v.008H12v-.008z"
            />
          </svg>
          <div>
            <p className="text-sm font-medium text-red-800">Something went wrong</p>
            <p className="mt-0.5 text-sm text-red-700">{error}</p>
          </div>
          <button
            onClick={() => setError(null)}
            className="ml-auto text-red-400 hover:text-red-600"
            aria-label="Dismiss"
          >
            <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>
      )}

      {/* ----------------------------------------------------------------- */}
      {/* Loading spinner overlay (for demo data) */}
      {/* ----------------------------------------------------------------- */}
      {loading && loadingMessage.includes('demo') && (
        <div className="flex items-center justify-center gap-3 py-6">
          <Spinner size="lg" />
          <span className="text-sm text-gray-600 font-medium">{loadingMessage}</span>
        </div>
      )}

      {/* ----------------------------------------------------------------- */}
      {/* Data quality grid */}
      {/* ----------------------------------------------------------------- */}
      {dataLoaded && files && (
        <div>
          <div className="flex items-center justify-between mb-4">
            <h2>Data Quality Summary</h2>
            {overallQuality !== null && (
              <span
                className={classNames(
                  overallQuality >= 0.95 && 'badge-success',
                  overallQuality >= 0.90 && overallQuality < 0.95 && 'badge-warning',
                  overallQuality < 0.90 && 'badge-error',
                )}
              >
                Overall: {formatPercent(overallQuality)}
              </span>
            )}
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {Object.values(files).map((fq) => (
              <DataQualityCard key={fq.file_name} quality={fq} />
            ))}
          </div>
        </div>
      )}

      {/* ----------------------------------------------------------------- */}
      {/* Continue button */}
      {/* ----------------------------------------------------------------- */}
      <div className="flex justify-end pb-4">
        <button
          onClick={() => navigate('/contract')}
          disabled={!ready}
          className="btn-primary px-6 py-2.5"
        >
          Continue to Contract Configuration
          <svg
            className="ml-2 h-4 w-4"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
            strokeWidth={2}
          >
            <path strokeLinecap="round" strokeLinejoin="round" d="M13.5 4.5L21 12m0 0l-7.5 7.5M21 12H3" />
          </svg>
        </button>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Small spinner component
// ---------------------------------------------------------------------------

function Spinner({ size = 'sm' }: { size?: 'sm' | 'lg' }) {
  const dim = size === 'lg' ? 'h-6 w-6' : 'h-4 w-4';
  return (
    <svg
      className={classNames('animate-spin text-current', dim)}
      xmlns="http://www.w3.org/2000/svg"
      fill="none"
      viewBox="0 0 24 24"
    >
      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
      <path
        className="opacity-75"
        fill="currentColor"
        d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
      />
    </svg>
  );
}
