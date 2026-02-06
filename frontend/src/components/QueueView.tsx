import React, { useMemo } from 'react';
import { Trash2, XCircle, RefreshCcw } from 'lucide-react';
import { LoadingState } from './common/LoadingState';
import { useQueues, usePurgeQueues, useRevokeTask } from '../hooks/useQueues';
import { cn } from '../utils/cn';

interface QueueTask {
	id?: string;
	name?: string;
	args?: any[];
	kwargs?: Record<string, any>;
	argsrepr?: string;
	kwargsrepr?: string;
	eta?: string | null;
	__worker?: string;
	queue?: string;
	raw?: string;
}

const TaskTable: React.FC<{
	label: string;
	tasks: QueueTask[];
	onRevoke: (taskId: string) => void;
	isRevoking: boolean;
}> = ({ label, tasks, onRevoke, isRevoking }) => {
	return (
		<div className="rounded-xl border border-[rgba(255,255,255,0.06)] bg-[rgba(10,10,10,0.25)] shadow-[0_10px_30px_rgba(0,0,0,0.25)]">
			<div className="flex items-center justify-between px-5 py-4 border-b border-[rgba(255,255,255,0.06)]">
				<div className="text-xs font-bold uppercase tracking-[0.2em] text-[var(--text-muted)]">
					{label}
				</div>
				<div className="text-[11px] text-[var(--text-secondary)]">
					{tasks.length} {tasks.length === 1 ? 'task' : 'tasks'}
				</div>
			</div>
			<div className="overflow-x-auto">
				<table className="w-full text-left text-[12px]">
					<thead className="bg-[rgba(255,255,255,0.03)] text-[10px] uppercase tracking-[0.2em] text-[var(--text-muted)]">
						<tr>
							<th className="px-5 py-3">Task</th>
							<th className="px-5 py-3">Worker</th>
							<th className="px-5 py-3">Args</th>
							<th className="px-5 py-3">ETA</th>
							<th className="px-5 py-3 text-right">Action</th>
						</tr>
					</thead>
					<tbody className="divide-y divide-[rgba(255,255,255,0.04)]">
						{tasks.length === 0 && (
							<tr>
								<td
									className="px-5 py-4 text-[11px] text-[var(--text-muted)]"
									colSpan={5}
								>
									No tasks in this queue.
								</td>
							</tr>
						)}
						{tasks.map((task) => (
							<tr
								key={`${task.__worker ?? 'worker'}-${task.id ?? Math.random()}`}
							>
								<td className="px-5 py-4">
									<div className="text-[12px] font-semibold text-white">
										{task.name || 'Unknown task'}
									</div>
									<div className="text-[10px] text-[var(--text-muted)] break-all">
										{task.id || 'No task id'}
									</div>
								</td>
								<td className="px-5 py-4 text-[11px] text-[var(--text-secondary)]">
									{task.__worker || 'N/A'}
								</td>
								<td className="px-5 py-4 text-[10px] text-[var(--text-muted)] max-w-[320px]">
									<div className="truncate">
										{task.argsrepr
											? task.argsrepr
											: task.args
												? JSON.stringify(task.args)
												: task.raw || '[]'}
									</div>
								</td>
								<td className="px-5 py-4 text-[11px] text-[var(--text-secondary)]">
									{task.eta || '—'}
								</td>
								<td className="px-5 py-4 text-right">
									<button
										className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-md bg-[var(--accent-danger)]/15 text-[var(--accent-danger)] text-[10px] font-bold uppercase tracking-wider disabled:opacity-50"
										onClick={() => task.id && onRevoke(task.id)}
										disabled={!task.id || isRevoking}
									>
										<XCircle className="w-3 h-3" />
										Revoke
									</button>
								</td>
							</tr>
						))}
					</tbody>
				</table>
			</div>
		</div>
	);
};

export const QueueView: React.FC = () => {
	const { data, isLoading, error, refetch, isFetching } = useQueues();
	const revokeMutation = useRevokeTask();
	const purgeMutation = usePurgeQueues();

	const { activeTasks, reservedTasks, scheduledTasks, pendingByQueue } =
		useMemo(() => {
			const flatten = (bucket: Record<string, any[]>) =>
				Object.entries(bucket || {}).flatMap(([worker, tasks]) =>
					tasks.map((task) => ({ ...task, __worker: worker })),
				);

			const pendingBuckets = Object.entries(data?.pending || {}).reduce(
				(acc, [queue, tasks]) => {
					acc[queue] = tasks.map((task: QueueTask) => ({
						...task,
						__worker: queue,
					}));
					return acc;
				},
				{} as Record<string, QueueTask[]>,
			);

			return {
				activeTasks: flatten(data?.active || {}),
				reservedTasks: flatten(data?.reserved || {}),
				scheduledTasks: flatten(data?.scheduled || {}),
				pendingByQueue: pendingBuckets,
			};
		}, [data]);

	if (isLoading) {
		return <LoadingState message="Loading queues..." />;
	}

	if (error || !data) {
		return (
			<div className="text-[11px] font-bold uppercase p-6 bg-[var(--accent-danger)]/5 rounded-lg border border-[var(--accent-danger)]/10 text-[var(--accent-danger)]">
				Unable to load queue state.
			</div>
		);
	}

	return (
		<div className="space-y-6">
			<div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
				<div>
					<h2 className="text-lg font-bold text-white">Task Queue</h2>
					<p className="text-[12px] text-[var(--text-muted)]">
						Monitor active work and remove stuck tasks.
					</p>
				</div>
				<div className="flex items-center gap-2">
					<button
						className={cn(
							'inline-flex items-center gap-2 px-3 py-2 rounded-md text-[10px] font-bold uppercase tracking-wider',
							'bg-[rgba(255,255,255,0.06)] text-[var(--text-secondary)]',
							'hover:bg-[rgba(255,255,255,0.1)]',
						)}
						onClick={() => refetch()}
						disabled={isFetching}
					>
						<RefreshCcw
							className={cn('w-3 h-3', isFetching && 'animate-spin')}
						/>
						Refresh
					</button>
					<button
						className="inline-flex items-center gap-2 px-3 py-2 rounded-md bg-[var(--accent-danger)]/15 text-[var(--accent-danger)] text-[10px] font-bold uppercase tracking-wider disabled:opacity-50"
						onClick={() => purgeMutation.mutate()}
						disabled={purgeMutation.isPending}
					>
						<Trash2 className="w-3 h-3" />
						Purge Pending
					</button>
				</div>
			</div>

			<div className="grid grid-cols-1 md:grid-cols-4 gap-4">
				{[
					{ label: 'Active', value: data.counts.active },
					{ label: 'Reserved', value: data.counts.reserved },
					{ label: 'Scheduled', value: data.counts.scheduled },
					{ label: 'Pending', value: data.pending_total ?? 0 },
				].map((card) => (
					<div
						key={card.label}
						className="rounded-lg border border-[rgba(255,255,255,0.06)] bg-[rgba(10,10,10,0.35)] px-4 py-4"
					>
						<div className="text-[10px] uppercase tracking-[0.2em] text-[var(--text-muted)]">
							{card.label}
						</div>
						<div className="text-2xl font-bold text-white mt-1">
							{card.value}
						</div>
					</div>
				))}
			</div>

			<TaskTable
				label="Active"
				tasks={activeTasks}
				onRevoke={(taskId) => revokeMutation.mutate(taskId)}
				isRevoking={revokeMutation.isPending}
			/>
			<TaskTable
				label="Reserved"
				tasks={reservedTasks}
				onRevoke={(taskId) => revokeMutation.mutate(taskId)}
				isRevoking={revokeMutation.isPending}
			/>
			<TaskTable
				label="Scheduled"
				tasks={scheduledTasks}
				onRevoke={(taskId) => revokeMutation.mutate(taskId)}
				isRevoking={revokeMutation.isPending}
			/>

			{Object.entries(pendingByQueue).map(([queueName, tasks]) => (
				<TaskTable
					key={queueName}
					label={`Pending (${queueName})`}
					tasks={tasks}
					onRevoke={(taskId) => revokeMutation.mutate(taskId)}
					isRevoking={revokeMutation.isPending}
				/>
			))}
		</div>
	);
};
