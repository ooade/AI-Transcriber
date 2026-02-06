import { useServerEvents } from '../contexts/ServerEventsContext';
import { APP_TEXT } from '../constants/text';
import { Wifi, WifiOff } from 'lucide-react';

export const ConnectionStatusBanner = () => {
	const { isConnected, connectionError, retryCount } = useServerEvents();

	// Don't show banner if connected
	if (isConnected && !connectionError) {
		return null;
	}

	return (
		<div
			className={`fixed top-0 left-0 right-0 z-50 flex items-center justify-center gap-2 px-4 py-2 text-sm ${
				connectionError
					? 'bg-red-500/90 text-white'
					: 'bg-yellow-500/90 text-black'
			}`}
		>
			{connectionError ? (
				<>
					<WifiOff className="h-4 w-4" />
					<span className="font-medium">{connectionError}</span>
					{retryCount > 0 && (
						<span className="text-xs opacity-90">
							{APP_TEXT.CONNECTION.ATTEMPT_PREFIX}{retryCount}{APP_TEXT.CONNECTION.ATTEMPT_SUFFIX}
						</span>
					)}
				</>
			) : (
				<>
					<Wifi className="h-4 w-4 animate-pulse" />
					<span>{APP_TEXT.CONNECTION.CONNECTING}</span>
				</>
			)}
		</div>
	);
};
