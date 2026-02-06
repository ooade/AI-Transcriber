import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { endpoints } from '../config';

export interface QueueSnapshot {
	workers: string[];
	active: Record<string, any[]>;
	reserved: Record<string, any[]>;
	scheduled: Record<string, any[]>;
	pending: Record<string, any[]>;
	counts: {
		active: number;
		reserved: number;
		scheduled: number;
		total: number;
	};
	pending_counts: Record<string, number>;
	pending_total: number;
}

export const useQueues = () => {
	return useQuery<QueueSnapshot>({
		queryKey: ['queues'],
		queryFn: async () => {
			const response = await fetch(endpoints.queues);
			if (!response.ok) {
				throw new Error('Failed to fetch queues');
			}
			return response.json();
		},
		// Optimization: Polling disabled in favor of SSE Push (broadcast_queue_stats_task)
		// refetchInterval: 3000,
		staleTime: Infinity,
	});
};

export const useRevokeTask = () => {
	const queryClient = useQueryClient();
	return useMutation({
		mutationFn: async (taskId: string) => {
			const response = await fetch(endpoints.queueRevoke(taskId), {
				method: 'POST',
			});
			if (!response.ok) {
				throw new Error('Failed to revoke task');
			}
			return response.json();
		},
		onSuccess: () => {
			queryClient.invalidateQueries({ queryKey: ['queues'] });
		},
	});
};

export const usePurgeQueues = () => {
	const queryClient = useQueryClient();
	return useMutation({
		mutationFn: async () => {
			const response = await fetch(endpoints.queuePurge, {
				method: 'POST',
			});
			if (!response.ok) {
				throw new Error('Failed to purge queues');
			}
			return response.json();
		},
		onSuccess: () => {
			queryClient.invalidateQueries({ queryKey: ['queues'] });
		},
	});
};
