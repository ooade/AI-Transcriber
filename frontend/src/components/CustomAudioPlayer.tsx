import React, { useState, useEffect, useRef } from 'react';
import { Play, Pause, Volume2, RotateCcw } from 'lucide-react';
import { cn } from '../utils/cn';

interface CustomAudioPlayerProps {
  src: string;
  onTimeUpdate?: (currentTime: number) => void;
  audioRef?: React.RefObject<HTMLAudioElement | null>;
}

export const CustomAudioPlayer: React.FC<CustomAudioPlayerProps> = ({ src, onTimeUpdate, audioRef: externalRef }) => {
  const [isPlaying, setIsPlaying] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(0);
  const [volume, setVolume] = useState(1);
  const [isMuted, setIsMuted] = useState(false);
  const internalRef = useRef<HTMLAudioElement>(null);
  const audioRef = (externalRef || internalRef) as React.RefObject<HTMLAudioElement>;

  useEffect(() => {
    const audio = audioRef.current;
    if (!audio) return;

    const handleTimeUpdate = () => {
      setCurrentTime(audio.currentTime);
      if (onTimeUpdate) onTimeUpdate(audio.currentTime);
    };

    const handleLoadedMetadata = () => {
      setDuration(audio.duration);
    };

    const handlePlay = () => setIsPlaying(true);
    const handlePause = () => setIsPlaying(false);
    const handleEnded = () => setIsPlaying(false);

    audio.addEventListener('timeupdate', handleTimeUpdate);
    audio.addEventListener('loadedmetadata', handleLoadedMetadata);
    audio.addEventListener('play', handlePlay);
    audio.addEventListener('pause', handlePause);
    audio.addEventListener('ended', handleEnded);

    return () => {
      audio.removeEventListener('timeupdate', handleTimeUpdate);
      audio.removeEventListener('loadedmetadata', handleLoadedMetadata);
      audio.removeEventListener('play', handlePlay);
      audio.removeEventListener('pause', handlePause);
      audio.removeEventListener('ended', handleEnded);
    };
  }, [audioRef, onTimeUpdate]);

  const togglePlay = () => {
    if (audioRef.current) {
      if (isPlaying) {
        audioRef.current.pause();
      } else {
        audioRef.current.play();
      }
    }
  };

  const handleSeek = (e: React.ChangeEvent<HTMLInputElement>) => {
    const time = parseFloat(e.target.value);
    if (audioRef.current) {
      audioRef.current.currentTime = time;
      setCurrentTime(time);
    }
  };

  const skip = (seconds: number) => {
    if (audioRef.current) {
      audioRef.current.currentTime += seconds;
    }
  };

  const formatTime = (time: number) => {
    const minutes = Math.floor(time / 60);
    const seconds = Math.floor(time % 60);
    return `${minutes}:${seconds.toString().padStart(2, '0')}`;
  };

  const handleVolumeChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const val = parseFloat(e.target.value);
    setVolume(val);
    if (audioRef.current) {
        audioRef.current.volume = val;
        audioRef.current.muted = val === 0;
        setIsMuted(val === 0);
    }
  };

  const toggleMute = () => {
    if (audioRef.current) {
        const newMute = !isMuted;
        setIsMuted(newMute);
        audioRef.current.muted = newMute;
    }
  };

  return (
    <div className={cn("w-full flex items-center gap-6 py-2 px-1 group/player")}>
      <audio ref={audioRef} src={src} className="hidden" />

      {/* 1. Play/Pause Controller - ELEVATED */}
      <div className="flex items-center gap-4 shrink-0">
        <button
            onClick={() => skip(-10)}
            className="text-[var(--text-muted)] hover:text-white transition-all p-2 hover:bg-[rgba(255,255,255,0.04)] rounded-full active:scale-95"
            title="Skip back 10s"
        >
            <RotateCcw className="w-4 h-4" />
        </button>

        <button
            onClick={togglePlay}
            className="w-10 h-10 flex items-center justify-center bg-white text-black rounded-full hover:scale-105 transition-all shadow-[0_4px_12px_rgba(0,0,0,0.3)] active:scale-95 shrink-0"
        >
            {isPlaying ? <Pause className="w-5 h-5 fill-current" /> : <Play className="w-5 h-5 fill-current ml-0.5" />}
        </button>
      </div>

      {/* 2. Progress Slider Area - SYMMETRICAL TRACKING */}
      <div className="flex-1 flex items-center gap-4">
        <span className="text-[10px] font-bold text-[var(--text-muted)] tabular-nums w-10 text-right opacity-60">
          {formatTime(currentTime)}
        </span>

        <div className="flex-1 relative flex items-center h-10 group/slider">
          <input
            type="range"
            min="0"
            max={duration || 100}
            value={currentTime}
            onChange={handleSeek}
            className="absolute inset-x-0 w-full h-full bg-transparent appearance-none cursor-pointer outline-none z-10"
          />

          {/* Custom Visual Track */}
          <div className="absolute inset-x-0 h-[3px] bg-white/10 rounded-full overflow-hidden">
             <div
                className="h-full bg-[var(--accent-primary)] shadow-[0_0_12px_rgba(88,101,242,0.6)]"
                style={{ width: `${(currentTime / (duration || 1)) * 100}%` }}
             />
          </div>

          {/* High-Fidelity Handle - Visible on Track */}
          <div
            className="absolute w-3 h-3 bg-white rounded-full shadow-[0_2px_10px_rgba(0,0,0,0.8)] pointer-events-none transition-all duration-150 z-20 group-hover/slider:scale-110"
            style={{
                left: `calc(${(currentTime / (duration || 1)) * 100}% - 6px)`,
                opacity: duration > 0 ? 1 : 0
            }}
          />
        </div>

        <span className="text-[10px] font-bold text-[var(--text-muted)] tabular-nums w-10 opacity-60">
          {formatTime(duration)}
        </span>
      </div>

      {/* 3. Volume Indicator - FUNCTIONAL */}
      <div className="flex items-center gap-3 px-4 border-l border-white/5 shrink-0 h-8 group/volume">
        <button onClick={toggleMute} className="text-[var(--text-muted)] hover:text-white transition-colors">
            {isMuted || volume === 0 ? (
                <Volume2 className="w-3.5 h-3.5 opacity-20" />
            ) : (
                <Volume2 className="w-3.5 h-3.5 opacity-50 group-hover/volume:opacity-100" />
            )}
        </button>
        <div className="w-16 relative flex items-center h-8">
            <input
                type="range"
                min="0"
                max="1"
                step="0.01"
                value={isMuted ? 0 : volume}
                onChange={handleVolumeChange}
                className="absolute inset-x-0 w-full h-full bg-transparent appearance-none cursor-pointer z-10"
            />
            <div className="absolute inset-x-0 h-[2px] bg-white/5 rounded-full overflow-hidden">
                <div
                    className="h-full bg-[var(--text-muted)] opacity-30"
                    style={{ width: `${(isMuted ? 0 : volume) * 100}%` }}
                />
            </div>
        </div>
      </div>
    </div>
  );
};
