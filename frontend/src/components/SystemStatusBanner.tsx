import React from 'react';
import { useSystemStatus } from '../hooks/useSystemStatus';
import { APP_TEXT } from '../constants/text';

export const SystemStatusBanner: React.FC = () => {
    const { status, isLoading } = useSystemStatus();

    if (isLoading || !status) return null;

    const { overall_status, components } = status;

    if (overall_status === 'ready') return null; // Don't show anything if everything is perfect

    // Helper to get color and message
    let bgColor = 'bg-gray-100';
    let textColor = 'text-gray-800';
    let message = APP_TEXT.STATUS_BANNER.UNKNOWN;

    if (overall_status === 'initializing') {
        bgColor = 'bg-blue-100 border-blue-200';
        textColor = 'text-blue-800';
        message = APP_TEXT.STATUS_BANNER.INITIALIZING;
    } else if (overall_status === 'degraded') {
        bgColor = 'bg-yellow-50 border-yellow-200';
        textColor = 'text-yellow-800';
        if (components.llm.status !== 'ready') {
            message = `${APP_TEXT.STATUS_BANNER.DEGRADED_PREFIX}${components.llm.error || APP_TEXT.STATUS_BANNER.DEGRADED_DEFAULT}`;
        }
    } else if (overall_status === 'error' || overall_status === 'unavailable') {
        bgColor = 'bg-red-100 border-red-200';
        textColor = 'text-red-800';
        message = `${APP_TEXT.STATUS_BANNER.ERROR_PREFIX}${components.transcriber.error || APP_TEXT.STATUS_BANNER.ERROR_DEFAULT}`;
    }

    return (
        <div className={`fixed bottom-0 left-0 right-0 p-2 text-center text-sm font-medium border-t ${bgColor} ${textColor} z-50`}>
            {message}
        </div>
    );
};
