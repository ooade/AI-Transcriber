import React, {
	createContext,
	useContext,
	useEffect,
	useRef,
	useState,
	useCallback,
	useMemo,
} from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { API_BASE_URL } from '../config';

interface ServerEvent {
	type: string;
	payload: any;
}

interface ServerEventsContextType {
	lastEvent: ServerEvent | null;
	subscribe: (
		eventType: string,
		callback: (payload: any) => void,
	) => () => void;
	isConnected: boolean;
	connectionError: string | null;
	retryCount: number;
	setSSETaskId: (id: string | null) => void;
}

const ServerEventsContext = createContext<ServerEventsContextType | null>(null);

// Exponential backoff configuration
const INITIAL_RETRY_DELAY = 1000; // 1 second
const MAX_RETRY_DELAY = 30000; // 30 seconds
const MAX_RETRY_ATTEMPTS = 10;
const BACKOFF_MULTIPLIER = 2;

export const ServerEventsProvider: React.FC<{ children: React.ReactNode }> = ({
	children,
}) => {
	const [isConnected, setIsConnected] = useState(false);
	const [connectionError, setConnectionError] = useState<string | null>(null);
	const [retryCount, setRetryCount] = useState(0);
	const [lastEvent, setLastEvent] = useState<ServerEvent | null>(null);
	const [activeTaskId, setActiveTaskId] = useState<string | null>(null);
	const eventSourceRef = useRef<EventSource | null>(null);
	const retryTimeoutRef = useRef<NodeJS.Timeout | null>(null);
	const isManualClose = useRef(false);

	const queryClient = useQueryClient();

	// Subscribers map: eventType -> Set of callbacks
	const subscribersRef = useRef<Map<string, Set<(payload: any) => void>>>(
		new Map(),
	);

	const calculateRetryDelay = (attempt: number): number => {
		const delay = Math.min(
			INITIAL_RETRY_DELAY * Math.pow(BACKOFF_MULTIPLIER, attempt),
			MAX_RETRY_DELAY,
		);
		// Add jitter (±20%) to prevent thundering herd
		const jitter = delay * 0.2 * (Math.random() - 0.5);
		return Math.floor(delay + jitter);
	};

	const connect = useCallback(
		(taskId: string | null) => {
			// Clear any pending retry
			if (retryTimeoutRef.current) {
				clearTimeout(retryTimeoutRef.current);
				retryTimeoutRef.current = null;
			}

			// Close existing connection
			if (eventSourceRef.current) {
				isManualClose.current = true;
				eventSourceRef.current.close();
				eventSourceRef.current = null;
			}

			console.log(
				`🔌 Connecting to SSE stream${taskId ? ` (Task: ${taskId})` : ''}... (Attempt ${retryCount + 1})`,
			);

			const url = new URL(`${API_BASE_URL}/events`);
			if (taskId) {
				url.searchParams.set('task_id', taskId);
			}

			try {
				const eventSource = new EventSource(url.toString());
				eventSourceRef.current = eventSource;
				isManualClose.current = false;

				eventSource.onopen = () => {
					console.log('✅ SSE Connected');
					setIsConnected(true);
					setConnectionError(null);
					setRetryCount(0); // Reset retry count on successful connection
				};

				eventSource.onmessage = (event) => {
					try {
						const parsedData = JSON.parse(event.data);
						if (
							!parsedData ||
							typeof parsedData !== 'object' ||
							!('type' in parsedData)
						) {
							// Ignore internal messages (like Celery noise)
							return;
						}

						const { type, payload } = parsedData;

						console.log(`📩 SSE Received: ${type}`, payload);
						setLastEvent({ type, payload });

						// Principal Move: Synchronize the global query cache based on the event
						if (type === 'task_progress' || type === 'transcription_complete') {
							const taskId = payload.task_id || payload.id;
							if (taskId) {
								// Update the task query data directly
								queryClient.setQueryData(['task', taskId], (old: any) => {
									return {
										...old,
										status:
											payload.status ||
											(type === 'transcription_complete'
												? 'SUCCESS'
												: old?.status),
										result:
											type === 'transcription_complete' ? payload : old?.result,
										message: payload.message || old?.message,
									};
								});

								// If it's a completion event, we also want to invalidate the history to show the new item
								if (type === 'transcription_complete') {
									queryClient.invalidateQueries({ queryKey: ['history'] });
								}
							}
						}

						if (type === 'summary_complete' || type === 'summary_failed') {
							// Update the specific transcription detail in cache
							queryClient.invalidateQueries({
								queryKey: ['transcription', payload.id],
							});
							// Also refresh history to show the new summary/meeting type in the list
							queryClient.invalidateQueries({ queryKey: ['history'] });
						}

						if (type === 'system_status') {
							// Sync the global system health status
							queryClient.setQueryData(['system', 'status'], payload);
						}

						if (type === 'queue_update') {
							// Real-time queue stats push
							queryClient.setQueryData(['queues'], payload);
						}

						const callbacks = subscribersRef.current.get(type);
						if (callbacks) {
							callbacks.forEach((cb) => cb(payload));
						}
					} catch (e) {
						console.error('Failed to parse SSE message', e, event.data);
					}
				};

				eventSource.onerror = (err) => {
					console.error('SSE Error', err);
					setIsConnected(false);

					// Don't retry if it was a manual close
					if (isManualClose.current) {
						console.log('SSE connection closed manually, not retrying');
						return;
					}

					eventSource.close();
					eventSourceRef.current = null;

					// Attempt reconnection with exponential backoff
					if (retryCount < MAX_RETRY_ATTEMPTS) {
						const delay = calculateRetryDelay(retryCount);
						const errorMsg = `Connection lost. Retrying in ${Math.round(delay / 1000)}s... (${retryCount + 1}/${MAX_RETRY_ATTEMPTS})`;
						setConnectionError(errorMsg);
						console.log(`⏳ ${errorMsg}`);

						setRetryCount((prev) => prev + 1);

						retryTimeoutRef.current = setTimeout(() => {
							connect(taskId);
						}, delay);
					} else {
						const errorMsg =
							'Connection failed after maximum retry attempts. Please refresh the page.';
						setConnectionError(errorMsg);
						console.error(`❌ ${errorMsg}`);
					}
				};
			} catch (error) {
				console.error('Failed to create EventSource:', error);
				setConnectionError('Failed to establish connection');
				setIsConnected(false);
			}
		},
		[retryCount, queryClient],
	);

	// Handle online/offline events
	useEffect(() => {
		const handleOnline = () => {
			console.log('🌐 Network online, reconnecting SSE...');
			setRetryCount(0); // Reset retry count when network comes back
			connect(activeTaskId);
		};

		const handleOffline = () => {
			console.log('📡 Network offline');
			setConnectionError('Network offline');
			setIsConnected(false);
		};

		window.addEventListener('online', handleOnline);
		window.addEventListener('offline', handleOffline);

		return () => {
			window.removeEventListener('online', handleOnline);
			window.removeEventListener('offline', handleOffline);
		};
	}, [activeTaskId, connect]);

	useEffect(() => {
		connect(activeTaskId);
		return () => {
			// Cleanup on unmount
			if (retryTimeoutRef.current) {
				clearTimeout(retryTimeoutRef.current);
			}
			if (eventSourceRef.current) {
				isManualClose.current = true;
				eventSourceRef.current.close();
			}
		};
	}, [activeTaskId, connect]);

	const subscribe = useCallback(
		(eventType: string, callback: (payload: any) => void) => {
			if (!subscribersRef.current.has(eventType)) {
				subscribersRef.current.set(eventType, new Set());
			}
			subscribersRef.current.get(eventType)?.add(callback);
			return () => {
				subscribersRef.current.get(eventType)?.delete(callback);
			};
		},
		[],
	);

	const contextValue = useMemo(
		() => ({
			lastEvent,
			subscribe,
			isConnected,
			connectionError,
			retryCount,
			setSSETaskId: setActiveTaskId,
		}),
		[lastEvent, subscribe, isConnected, connectionError, retryCount],
	);

	return (
		<ServerEventsContext.Provider value={contextValue}>
			{children}
		</ServerEventsContext.Provider>
	);
};

export const useServerEvents = () => {
	const context = useContext(ServerEventsContext);
	if (!context) {
		throw new Error(
			'useServerEvents must be used within a ServerEventsProvider',
		);
	}
	return context;
};
