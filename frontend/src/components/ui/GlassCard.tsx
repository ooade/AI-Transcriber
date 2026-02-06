import { cn } from '../../utils/cn';

interface GlassCardProps {
  children: React.ReactNode;
  className?: string;
  onClick?: () => void;
  hoverEffect?: boolean;
}

export const GlassCard = ({ children, className, onClick, hoverEffect = false }: GlassCardProps) => {
  return (
    <div
      onClick={onClick}
      className={cn(
        "relative overflow-hidden bg-[var(--bg-card)] border border-[var(--border-subtle)]",
        "rounded-none", /* Industrial/Linear style often uses square or very subtly rounded corners */
        onClick && "cursor-pointer active:bg-[var(--border-subtle)]/50",
        hoverEffect && "hover:border-[var(--text-secondary)]/30",
        className
      )}
    >
      <div className="relative z-10 h-full">
        {children}
      </div>
    </div>
  );
};
