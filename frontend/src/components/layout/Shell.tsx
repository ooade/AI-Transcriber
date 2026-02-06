import { Mic, FileText, BarChart2, Radio, ListChecks } from 'lucide-react';
import { APP_TEXT } from '../../constants/text';
import { cn } from '../../utils/cn';

interface ShellProps {
	children: React.ReactNode;
	activeView: string;
	onViewChange: (view: any) => void;
	isRecording?: boolean;
}

export const Shell = ({
	children,
	activeView,
	onViewChange,
	isRecording,
}: ShellProps) => {
	const navItems = [
		{ id: 'recorder', icon: Mic, label: APP_TEXT.NAV.RECORD },
		{ id: 'history', icon: FileText, label: APP_TEXT.NAV.HISTORY },
		{ id: 'insights', icon: BarChart2, label: APP_TEXT.NAV.INSIGHTS },
		{ id: 'queues', icon: ListChecks, label: APP_TEXT.NAV.QUEUES },
	];

	return (
		<div className="flex h-screen w-screen bg-[var(--bg-main)] text-[var(--text-primary)] overflow-hidden font-sans selection:bg-[var(--selection-bg)]">
			{/* 1. Unified Side Navigation */}
			<aside className="w-64 bg-[var(--bg-sidebar)] flex flex-col shrink-0 border-r border-[rgba(0,0,0,0.2)]">
				{/* Sidebar Header */}
				<header className="h-12 px-4 flex items-center border-b border-[rgba(0,0,0,0.2)] shadow-sm shrink-0">
					<div className="flex items-center gap-2">
						<Radio className="w-5 h-5 text-[var(--accent-primary)]" />
						<h1 className="text-sm font-bold tracking-tight text-white uppercase truncate">
							{APP_TEXT.APP_NAME}
						</h1>
					</div>
				</header>

				{/* Sidebar Content */}
				<div className="flex-1 overflow-y-auto custom-scrollbar p-3 space-y-6">
					{/* Primary Navigation */}
					<nav className="space-y-1">
						{navItems.map((item) => {
							const isActive =
								activeView === item.id ||
								(item.id === 'history' && activeView === 'editor');
							return (
								<button
									key={item.id}
									onClick={() => onViewChange(item.id)}
									className={cn(
										'w-full flex items-center gap-3 px-3 py-2 rounded-md transition-all duration-200 group text-left',
										isActive
											? 'bg-[var(--accent-primary)] text-white shadow-[0_4px_12px_rgba(88,101,242,0.3)]'
											: 'text-[var(--text-secondary)] hover:bg-[var(--bg-modifier-hover)] hover:text-white',
									)}
								>
									<item.icon
										className={cn(
											'w-5 h-5 transition-colors',
											isActive
												? 'text-white'
												: 'text-[var(--text-muted)] group-hover:text-white',
										)}
										strokeWidth={2.5}
									/>
									<span className="text-[13px] font-bold tracking-tight">
										{item.label}
									</span>
								</button>
							);
						})}
					</nav>

					<div className="h-[1px] bg-[var(--border-subtle)] opacity-10 mx-1" />

					{/* Contextual Status / Info */}
					<section className="space-y-4">
						<div>
							<div className="text-[10px] font-bold uppercase tracking-widest text-[var(--text-muted)] mb-2 px-3 opacity-60">
								{activeView === 'recorder'
									? APP_TEXT.SHELL.SIDEBAR.SESSION_HEADER
									: APP_TEXT.SHELL.SIDEBAR.LIBRARY_HEADER}
							</div>
							<div className="px-3 py-3 rounded-lg bg-[rgba(0,0,0,0.2)] border border-[rgba(255,255,255,0.02)] shadow-inner">
								<div className="flex items-center gap-2.5">
									<div
										className={cn(
											'w-2 h-2 rounded-full',
											isRecording
												? 'bg-[var(--accent-success)] shadow-[0_0_8px_rgba(35,165,89,0.5)]'
												: 'bg-[var(--text-muted)]/50',
										)}
									/>
									<span className="text-[12px] font-bold text-white">
										{isRecording
											? APP_TEXT.SHELL.SIDEBAR.STATUS_RECORDING
											: APP_TEXT.SHELL.SIDEBAR.STATUS_ACTIVE}
									</span>
								</div>
							</div>
						</div>

						<div className="px-3">
							<div className="text-[10px] font-bold uppercase tracking-widest text-[var(--text-muted)] mb-3 opacity-60">
								{APP_TEXT.SHELL.SIDEBAR.HELP_HEADER}
							</div>
							<ul className="space-y-3">
								<li className="flex gap-2.5">
									<span className="text-[11px] text-[var(--text-secondary)] leading-snug">
										{APP_TEXT.SHELL.SIDEBAR.TIP_1}
									</span>
								</li>
								<li className="flex gap-2.5">
									<span className="text-[11px] text-[var(--text-secondary)] leading-snug">
										{APP_TEXT.SHELL.SIDEBAR.TIP_2}
									</span>
								</li>
							</ul>
						</div>
					</section>
				</div>
			</aside>

			{/* 2. Main content Area */}
			<main className="flex-1 flex flex-col min-w-0 bg-[var(--bg-main)]">
				{/* Main Content Header - MINIMAL */}
				<header className="h-12 px-6 flex items-center glass-header shrink-0 z-40 sticky top-0">
					<div className="flex items-center gap-3">
						<span className="text-sm font-bold text-white uppercase tracking-wider opacity-80">
							{navItems.find((i) => i.id === activeView)?.label}
						</span>
					</div>

					<div className="ml-auto flex items-center gap-4">
						{isRecording && (
							<div className="flex items-center gap-2 px-2.5 py-0.5 bg-[var(--accent-danger)]/10 border border-[var(--accent-danger)]/20 rounded-md">
								<div className="w-1.5 h-1.5 bg-[var(--accent-danger)] rounded-full recording-pulse shadow-[0_0_8px_rgba(242,63,67,0.5)]" />
								<span className="text-[10px] font-black text-[var(--accent-danger)] uppercase">
									{APP_TEXT.NAV.LIVE_SHORT}
								</span>
							</div>
						)}
						<div className="flex items-center gap-3 px-2 py-0.5 bg-[rgba(0,0,0,0.1)] rounded-md border border-[rgba(255,255,255,0.02)]">
							<span className="text-[10px] text-[var(--text-muted)] uppercase tracking-wider font-bold">
								v{APP_TEXT.NAV.VERSION}
							</span>
						</div>
					</div>
				</header>

				{/* Primary Scrollable Content */}
				<div className="flex-1 overflow-y-auto custom-scrollbar">
					<div className="max-w-6xl mx-auto p-8 lg:p-12">{children}</div>
				</div>
			</main>
		</div>
	);
};
