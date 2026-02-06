import React from 'react';
import { endpoints } from '../config';
import { APP_TEXT } from '../constants/text';
import { useQuery } from '@tanstack/react-query';
import { AlertTriangle, CheckCircle2, TrendingUp, BarChart3, Database, Zap, Shield } from 'lucide-react';
import { LoadingState } from './common/LoadingState';

interface InsightData {
  total_errors: number;
  by_type: Record<string, number>;
  frequent_errors: Array<{ word: string, count: number }>;
  average_wer: number;
}

// ----------------------------------------------------------------------
// INDUSTRIAL SUB-COMPONENTS
// ----------------------------------------------------------------------

const CircularProgress = ({ percentage }: { percentage: number }) => {
  const radius = 42;
  const circumference = 2 * Math.PI * radius;
  const validPercentage = Math.min(Math.max(percentage, 0), 100);
  const strokeDashoffset = circumference - (validPercentage / 100) * circumference;

  return (
    <div className="relative flex items-center justify-center w-32 h-32 bg-[var(--bg-rail)] border border-[rgba(0,0,0,0.2)] rounded-lg shadow-inner">
      <svg className="transform -rotate-90 w-24 h-24">
        <circle
          cx="48"
          cy="48"
          r={radius}
          stroke="currentColor"
          strokeWidth="6"
          fill="transparent"
          className="text-[var(--bg-main)]"
        />
        <circle
          cx="48"
          cy="48"
          r={radius}
          stroke="currentColor"
          strokeWidth="6"
          fill="transparent"
          strokeDasharray={circumference}
          strokeDashoffset={strokeDashoffset}
          className="text-[var(--accent-primary)]"
          strokeLinecap="round"
        />
      </svg>
      <div className="absolute flex flex-col items-center">
        <span className="text-xl font-bold text-white">
          {validPercentage.toFixed(0)}<span className="text-[10px] opacity-60 ml-0.5">%</span>
        </span>
      </div>
    </div>
  );
};

const MetricBlock = ({
  title,
  value,
  icon: Icon,
  unit
}: {
  title: string;
  value: string | number;
  icon: React.ElementType;
  unit?: string;
}) => (
  <div className="bg-[var(--bg-sidebar)] border border-[rgba(0,0,0,0.2)] p-6 rounded-lg shadow-md flex flex-col justify-between group hover:border-[var(--accent-primary)]/40 transition-colors">
    <div className="flex items-center gap-2 mb-4">
        <Icon className="w-4 h-4 text-[var(--accent-primary)]" />
        <h3 className="text-[10px] font-bold text-[var(--text-muted)] uppercase tracking-wider">{title}</h3>
    </div>
    <div className="flex items-baseline gap-2">
      <p className="text-3xl font-bold text-white tracking-tight">{value}</p>
      {unit && <span className="text-[9px] font-bold text-[var(--accent-primary)] uppercase tracking-widest">{unit}</span>}
    </div>
  </div>
);

const IndustrialBar = ({ label, count, total }: { label: string; count: number; total: number }) => {
  const percentage = total > 0 ? (count / total) * 100 : 0;

  return (
    <div className="space-y-2.5 group">
      <div className="flex justify-between items-center text-[10px] font-bold uppercase tracking-wider">
        <span className="text-[var(--text-secondary)] group-hover:text-white transition-colors">{label}</span>
        <span className="text-[var(--accent-primary)] font-bold">[{count}]</span>
      </div>
      <div className="h-2 w-full bg-[var(--bg-rail)] rounded-full overflow-hidden border border-[rgba(0,0,0,0.1)]">
        <div
          className="h-full bg-[var(--accent-primary)] rounded-full"
          style={{ width: `${percentage}%` }}
        />
      </div>
    </div>
  );
};

// ----------------------------------------------------------------------
// MAIN TECHNICAL VIEW
// ----------------------------------------------------------------------

export const InsightsView: React.FC = () => {
  const { data: insights, isLoading } = useQuery<InsightData>({
    queryKey: ['insights'],
    queryFn: async () => {
      const response = await fetch(endpoints.insights);
      if (!response.ok) throw new Error('Failed to fetch insights');
      return response.json();
    }
  });

  if (isLoading) {
    return (
      <LoadingState message={APP_TEXT.INSIGHTS.LOADING} />
    );
  }

  if (!insights) return <div className="text-[var(--accent-danger)] text-[11px] font-bold uppercase p-6 bg-[var(--accent-danger)]/5 rounded-lg border border-[var(--accent-danger)]/10">{APP_TEXT.INSIGHTS.ERROR}</div>;

  const accuracy = (1 - insights.average_wer) * 100;

  return (
    <div className="max-w-6xl mx-auto space-y-10 animate-none pb-12">

      {/* Modern Analytics Header */}
      <div className="pb-6">
          <div className="flex items-center justify-between mb-2">
             <h2 className="text-3xl font-bold text-white tracking-tight">{APP_TEXT.INSIGHTS.TITLE}</h2>
             <div className="flex items-center gap-3">
                <div className="flex items-center gap-2 px-3 py-1 bg-[var(--bg-sidebar)] border border-[rgba(0,0,0,0.2)] rounded-md shadow-sm">
                    <Zap className="w-3.5 h-3.5 text-amber-500 fill-amber-500" />
                    <span className="text-[10px] font-bold text-white uppercase">{APP_TEXT.INSIGHTS.METRICS.CORE_LOAD}</span>
                </div>
                <div className="flex items-center gap-2 px-3 py-1 bg-[var(--accent-success)]/10 border border-[var(--accent-success)]/20 rounded-md">
                    <Shield className="w-3.5 h-3.5 text-[var(--accent-success)]" />
                    <span className="text-[10px] font-bold text-[var(--accent-success)] uppercase">{APP_TEXT.INSIGHTS.METRICS.ENGINE_STABLE}</span>
                </div>
             </div>
          </div>
          <p className="text-sm text-[var(--text-secondary)] leading-relaxed max-w-2xl">{APP_TEXT.INSIGHTS.SUBTITLE}</p>
      </div>

      {/* Elevated Metric Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
         <div className="flex items-center justify-center bg-[var(--bg-sidebar)] border border-[rgba(0,0,0,0.2)] p-6 rounded-lg shadow-md">
            <CircularProgress percentage={accuracy} />
         </div>

         <MetricBlock
            title={APP_TEXT.INSIGHTS.METRICS.CORRECTIONS_LABEL}
            value={insights.total_errors}
            icon={AlertTriangle}
            unit={APP_TEXT.INSIGHTS.METRICS.UNIT_IMPROVEMENTS}
          />
          <MetricBlock
            title={APP_TEXT.INSIGHTS.METRICS.SESSIONS_LABEL}
            value="142"
            icon={CheckCircle2}
            unit={APP_TEXT.INSIGHTS.METRICS.UNIT_TOTAL}
          />
          <MetricBlock
             title={APP_TEXT.INSIGHTS.METRICS.DATASET_LABEL}
             value={APP_TEXT.INSIGHTS.METRICS.DATASET_STATUS}
             icon={TrendingUp}
          />
      </div>

      {/* Deep Inspector Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">

        {/* Neural Distribution */}
        <div className="lg:col-span-5 space-y-6">
          <div className="flex items-center gap-2 ml-1">
             <BarChart3 className="w-4 h-4 text-[var(--accent-primary)]" />
             <h3 className="text-[11px] font-bold text-white uppercase tracking-wider">
                {APP_TEXT.INSIGHTS.DISTRIBUTION_TITLE}
            </h3>
          </div>

          <div className="bg-[var(--bg-sidebar)] border border-[rgba(0,0,0,0.2)] p-8 rounded-lg shadow-lg space-y-8">
            {Object.entries(insights.by_type).map(([type, count]) => (
              <IndustrialBar
                key={type}
                label={type}
                count={count}
                total={insights.total_errors}
              />
            ))}

            <div className="pt-6 border-t border-[rgba(0,0,0,0.1)] mt-8">
              <p className="text-[10px] text-[var(--text-muted)] leading-relaxed italic">
                {APP_TEXT.INSIGHTS.DISTRIBUTION_FOOTNOTE_SUB} <br/>
                {APP_TEXT.INSIGHTS.DISTRIBUTION_FOOTNOTE_DEL}
              </p>
            </div>
          </div>
        </div>

        {/* Failure Intelligence */}
        <div className="lg:col-span-7 space-y-6">
          <div className="flex items-center gap-2 ml-1">
             <Database className="w-4 h-4 text-[var(--accent-primary)]" />
             <h3 className="text-[11px] font-bold text-white uppercase tracking-wider">
                 {APP_TEXT.INSIGHTS.FREQUENT_TITLE}
             </h3>
          </div>

          <div className="bg-[var(--bg-sidebar)] border border-[rgba(0,0,0,0.2)] rounded-lg overflow-hidden shadow-lg">
            <table className="w-full text-left border-collapse font-sans">
              <thead>
                <tr className="bg-[rgba(0,0,0,0.1)] border-b border-[rgba(0,0,0,0.2)] text-[10px] font-bold uppercase tracking-widest text-[var(--text-muted)]">
                  <th className="px-6 py-4 tracking-wider">{APP_TEXT.INSIGHTS.TABLE_HEADERS.WORD}</th>
                  <th className="px-6 py-4 text-right tracking-wider">{APP_TEXT.INSIGHTS.TABLE_HEADERS.COUNT}</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[rgba(0,0,0,0.1)]">
                {insights.frequent_errors.map((err, idx) => (
                  <tr key={idx} className="hover:bg-[rgba(255,255,255,0.01)] transition-colors">
                    <td className="px-6 py-4 text-sm font-bold text-white">
                       <span className="text-[var(--accent-primary)] opacity-40 mr-2">{idx + 1}</span>
                       {err.word}
                    </td>
                    <td className="px-6 py-4 text-right text-base font-bold text-[var(--accent-primary)]">
                         {err.count}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
};
