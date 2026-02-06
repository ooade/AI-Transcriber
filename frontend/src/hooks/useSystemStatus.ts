import { useQuery } from '@tanstack/react-query';
import { endpoints } from '../config';

export type ServiceStatus = 'ready' | 'initializing' | 'degraded' | 'error' | 'unavailable';

interface ComponentStatus {
    status: ServiceStatus;
    error: string | null;
}

interface SystemStatus {
    overall_status: ServiceStatus;
    components: {
        transcriber: ComponentStatus;
        llm: ComponentStatus;
    };
}

export const useSystemStatus = () => {
    const query = useQuery({
        queryKey: ['system', 'status'],
        queryFn: async () => {
            const response = await fetch(endpoints.status);
            if (!response.ok) throw new Error("Failed to fetch system status");
            return response.json() as Promise<SystemStatus>;
        },
        staleTime: Infinity, // Rely on SSE for updates
    });

    return {
        status: query.data || null,
        isLoading: query.isLoading
    };
};
