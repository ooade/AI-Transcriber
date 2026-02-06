
import { motion } from 'framer-motion';

export const AudioPulse = ({ isRecording, level = 0 }: { isRecording: boolean; level?: number }) => {
  return (
    <div className="flex items-center justify-center gap-1.5 h-12 w-full max-w-[200px]">
      {[...Array(5)].map((_, i) => (
        <motion.div
          key={i}
          initial={{ height: 4 }}
          animate={{
            height: isRecording
              ? Math.max(4, Math.min(48, 4 + (level * 100 * (0.5 + Math.random())))) // Reactive height based on level
              : 4,
            opacity: isRecording ? 1 : 0.5
          }}
          transition={{
            type: "spring",
            stiffness: 300,
            damping: 20,
            mass: 0.5
          }}
          className="w-1.5 bg-zinc-900 dark:bg-zinc-100 rounded-full"
        />
      ))}
    </div>
  );
};
