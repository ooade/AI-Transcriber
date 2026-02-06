export const APP_TEXT = {
	APP_NAME: 'Transcripts.ai',
	APP_TAGLINE: 'Your Intelligent Transcription Assistant',

	NAV: {
		RECORD: 'Record',
		HISTORY: 'My Library',
		INSIGHTS: 'Insights',
		QUEUES: 'Queues',
		LIVE_INDICATOR: 'Session Active',
		LIVE_SHORT: 'REC',
		VERSION: 'v2.5',
	},

	SHELL: {
		SIDEBAR: {
			SESSION_HEADER: 'Current Session',
			LIBRARY_HEADER: 'Your Library',
			STATUS_LABEL: 'Status',
			STATUS_ACTIVE: 'Ready to Record',
			STATUS_RECORDING: 'Capturing Voice',
			HELP_HEADER: 'Quick Tips',
			TIP_1: 'Speak clearly for best accuracy',
			TIP_2: 'Summary appears after recording',
			TIP_3: 'Edit any word in the library',
			SUPPORT_LABEL: 'Need help?',
			PLAN_LABEL: 'Free Plan',
			USER_DEFAULT: 'USER',
		},
	},

	RECORDER: {
		LIVE_STREAM_LABEL: 'Transcription Queue',
		LISTENING_PLACEHOLDER: 'Waiting for audio...',
		PROCESSING_LABEL: 'Preparing Recording',
		POLLING_TITLE: 'Analyzing Conversation',
		POLLING_SUBTITLE: 'Creating your transcript and summary',
		FINAL_RESULT_LABEL: 'Meeting Transcript',
		OPEN_EDITOR_BUTTON: 'Edit Transcript',
		RECORDING: 'Recording...',
		PROCESSING: 'Processing...',
		PROCESSING_MSG: 'Refining accuracy',
		FINALIZING: 'Saving',
		STATUS_CAPTURE: 'ACTIVE',
		STATUS_IDLE: 'READY',
	},

	RECORDER_PAGE: {
		SIGNAL_MONITOR: 'Audio Level',
		INPUT_GAIN: 'Volume',
		LATENCY: 'Connection',
		NEURAL_NODE_ACTIVE: 'Assistant: READY',
		PROCESSING_STREAM: 'Session Analysis',
		OPS_QUEUE_VERIFYING: 'REFINING',
		OPS_QUEUE_LINKING: 'SAVING',
	},

	TRANSCRIPT_EDITOR: {
		BACK_BUTTON: '← Library',
		SAVE_BUTTON: 'Save Changes',
		SAVING_BUTTON: 'Saving...',
		INTERACTIVE_TITLE: 'Interactive Transcript',
		EDIT_TITLE: 'Edit Mode',
		PLACEHOLDER: 'Type your corrections here...',
		NO_WORDS: 'Transcript data unavailable.',
		CONFIDENCE_TOOLTIP: 'Accuracy Score',
		SAVE_SUCCESS: 'Changes saved successfully.',
		SAVE_ERROR: 'Could not save changes.',
		MODE_MANUAL: 'MODE: EDIT',
		ANALYTICS_INSPECTOR: 'Details',
		WORD_CONFIDENCE: 'Accuracy',
		CONFIDENCE_AVG: '92% Accuracy',
		CONFIDENCE_LABEL: 'Average',
		SESSION_INTEGRITY: 'Recording Status',
		HASH_MATCH: 'VERIFIED SECURE',
		STATS: {
			IMPROVEMENTS: 'Improvements Made',
			SESSION_EDITS: 'Session Edits',
			TRACKING_ID: 'Tracking ID',
		},
	},

	HISTORY: {
		TITLE: 'Your Recordings',
		LOADING: 'Loading library...',
		EMPTY_STATE: 'Your library is empty. Start a recording to see it here.',
		DURATION_LABEL: 'Duration',
		NO_TRANSCRIPT: 'Processing...',
		SEARCH_PLACEHOLDER: 'Search by content...',
		UNTITLED: 'Untitled Session',
	},

	HISTORY_VIEW: {
		ARCHIVE_INDEX: 'Recordings Library',
		STATUS_SYNCED: 'STATUS: SYNCED',
		COUNT_LABEL: 'Recordings',
		COUNT_LABEL_SINGULAR: 'Recording',
		TABLE_HEADERS: {
			SUMMARY: 'Meeting Summary',
			DATE: 'Date',
			DURATION: 'Length',
			ACTION: 'View',
		},
		ACTION_OPEN: 'Open',
		UNIT_SECONDS: 'Seconds',
		CLIENT_FOOTER: 'Powered by Transcripts.ai v2.5',
		NODE_ID: 'Stored securely in your workspace',
	},

	INSIGHTS: {
		TITLE: 'Performance',
		SUBTITLE: 'Review transcription accuracy and system health.',

		METRICS: {
			ACCURACY_LABEL: 'Overall Accuracy',
			ACCURACY_DESC: 'Average confidence score across all sessions.',
			CORRECTIONS_LABEL: 'Improvements Made',
			CORRECTIONS_DESC: 'Refinements made to enhance future transcripts.',
			DATASET_LABEL: 'System Health',
			DATASET_STATUS: 'EXCELLENT',
			DATASET_DESC: 'Engine performing optimally.',
			SESSIONS_LABEL: 'Total Sessions',
			CONFIDENCE_PRIMARY: 'Accuracy',
			CONFIDENCE_SECONDARY: 'Confidence',
			CONFIDENCE_DETAIL: 'Based on verified data',
			LIVE_INDICATOR: 'ANALYTICS ENGINE',
			CORE_LOAD: 'System Load: 12%',
			ENGINE_STABLE: 'System Stable',
			UNIT_IMPROVEMENTS: 'Improvements',
			UNIT_TOTAL: 'Total',
		},

		DISTRIBUTION_TITLE: 'Accuracy Details',
		DISTRIBUTION_FOOTNOTE_SUB:
			'* Substitutions: Similar sounding words replaced.',
		DISTRIBUTION_FOOTNOTE_DEL:
			'* Deletions: Missed words during transcription.',
		FREQUENT_TITLE: 'Common Improvements',
		FREQUENT_TOP_BADGE: 'Top',
		TABLE_HEADERS: {
			WORD: 'Word',
			COUNT: 'Count',
		},

		LOADING: 'Loading analytics...',
		ERROR: 'Analytics unavailable.',
	},

	EDITOR: {
		LOADING: 'Loading...',
		ERROR: 'Failed to load transcript.',
	},

	AUDIO_RECORDER: {
		START_BUTTON: 'Start Recording',
		STOP_BUTTON: 'Stop Recording',
		CANCEL_BUTTON: 'Cancel',
	},

	UTILITIES: {
		COPY: 'Copy',
		COPIED: 'Copied',
		COPY_TRANSCRIPT: 'Copy Full Transcript',
		COPY_SUMMARY: 'Copy Summary',
		COPY_SUCCESS: 'Copied to clipboard',
	},

	STATUS_BANNER: {
		UNKNOWN: 'Status: Checking...',
		INITIALIZING: 'Preparing...',
		DEGRADED_PREFIX: 'Status: ',
		DEGRADED_DEFAULT: 'Reduced service',
		ERROR_PREFIX: 'Problem: ',
		ERROR_DEFAULT: 'Could not connect',
	},

	SUMMARY: {
		TITLE: 'Meeting Summary',
		DEFAULT_LOADING: 'Creating summary...',
		STATUS_UPDATING: 'Updating Library',
		STATUS_SAVING: 'Saving recording',
		DELAY_TITLE: 'Summary Pending',
		DELAY_MSG: 'Analyzing conversation context...',
		RETRY_BUTTON: 'Regenerate Summary',
	},

	SETTINGS: {
		TITLE: 'Transcription Settings',
		CLOSE: 'Close',
		BACKEND_LABEL: 'Backend',
		BACKEND_HINT: 'Model size is automatically managed for optimal quality (Large-v3).',
		CURRENT_BACKEND_PREFIX: 'Backend: ',
	},

	CONNECTION: {
		CONNECTING: 'Connecting to server...',
		ATTEMPT_PREFIX: '(Attempt ',
		ATTEMPT_SUFFIX: '/10)',
	},
};
