import React, { useState, useRef, useEffect } from 'react';
import { config } from '../config';

interface Clip {
    id: string;
    title: string;
    start_time: number;
    end_time: number;
    duration: number;
    blob_url: string;
    thumbnail_url?: string;
    clip_id?: string;
}

interface VideoPlayerModalProps {
    clip: Clip;
    isOpen: boolean;
    onClose: () => void;
}

const VideoPlayerModal: React.FC<VideoPlayerModalProps> = ({ clip, isOpen, onClose }) => {
    const videoRef = useRef<HTMLVideoElement>(null);
    const [currentTime, setCurrentTime] = useState(0);
    const [duration, setDuration] = useState(0);
    const [isPlaying, setIsPlaying] = useState(false);
    const [isLoaded, setIsLoaded] = useState(false);

    if (!isOpen) return null;

    // Reset state when modal opens/closes
    useEffect(() => {
        if (isOpen) {
            setCurrentTime(0);
            setDuration(0);
            setIsPlaying(false);
            setIsLoaded(false);
        }
    }, [isOpen]);

    const handleBackdropClick = (e: React.MouseEvent) => {
        if (e.target === e.currentTarget) {
            onClose();
        }
    };

    // Video event handlers
    const handleLoadedMetadata = () => {
        if (videoRef.current) {
            setDuration(videoRef.current.duration);
            setIsLoaded(true);
        }
    };

    const handleTimeUpdate = () => {
        if (videoRef.current) {
            setCurrentTime(videoRef.current.currentTime);
        }
    };

    const handlePlay = () => setIsPlaying(true);
    const handlePause = () => setIsPlaying(false);

    // Control functions
    const togglePlayPause = () => {
        if (videoRef.current) {
            if (isPlaying) {
                videoRef.current.pause();
            } else {
                videoRef.current.play();
            }
        }
    };

    const handleSeek = (e: React.ChangeEvent<HTMLInputElement>) => {
        const newTime = parseFloat(e.target.value);
        setCurrentTime(newTime);
        if (videoRef.current) {
            videoRef.current.currentTime = newTime;
        }
    };

    // Format time display (mm:ss)
    const formatTime = (seconds: number): string => {
        if (isNaN(seconds)) return '0:00';
        const mins = Math.floor(seconds / 60);
        const secs = Math.floor(seconds % 60);
        return `${mins}:${secs.toString().padStart(2, '0')}`;
    };

    const handleDownload = () => {
        try {
            const link = document.createElement('a');
            link.href = clip.blob_url;
            link.download = `${clip.title.replace(/[^a-zA-Z0-9]/g, '_')}.mp4`;
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
        } catch (error) {
            console.error('Download failed:', error);
        }
    };

    return (
        <div
            className="fixed inset-0 bg-black bg-opacity-75 flex items-center justify-center z-50 p-4"
            onClick={handleBackdropClick}
        >
            <div className="bg-white rounded-lg max-w-sm w-full max-h-[90vh] overflow-hidden">
                {/* Header */}
                <div className="flex justify-between items-center p-4 border-b">
                    <h3 className="text-lg font-semibold text-gray-900 truncate">
                        {clip.title}
                    </h3>
                    <button
                        onClick={onClose}
                        className="text-gray-500 hover:text-gray-700 text-xl font-bold"
                    >
                        ×
                    </button>
                </div>

                {/* Video Player - 9:16 Aspect Ratio */}
                <div className="relative bg-black">
                    <div className="aspect-[9/16]">
                        <video
                            ref={videoRef}
                            src={clip.blob_url}
                            className="w-full h-full object-contain"
                            preload="metadata"
                            onLoadedMetadata={handleLoadedMetadata}
                            onTimeUpdate={handleTimeUpdate}
                            onPlay={handlePlay}
                            onPause={handlePause}
                            onClick={togglePlayPause}
                        >
                            Your browser does not support the video tag.
                        </video>

                        {/* Custom Play/Pause Overlay */}
                        {!isPlaying && isLoaded && (
                            <div
                                className="absolute inset-0 flex items-center justify-center cursor-pointer"
                                onClick={togglePlayPause}
                            >
                                <div className="bg-black bg-opacity-50 rounded-full p-4">
                                    <svg className="w-12 h-12 text-white" fill="currentColor" viewBox="0 0 20 20">
                                        <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM9.555 7.168A1 1 0 008 8v4a1 1 0 001.555.832l3-2a1 1 0 000-1.664l-3-2z" clipRule="evenodd" />
                                    </svg>
                                </div>
                            </div>
                        )}
                    </div>
                </div>

                {/* Custom Video Controls */}
                {isLoaded && (
                    <div className="bg-gray-900 text-white p-4 space-y-3">
                        {/* Time Slider */}
                        <div className="space-y-2">
                            <input
                                type="range"
                                min="0"
                                max={duration || 0}
                                value={currentTime}
                                onChange={handleSeek}
                                className="w-full h-2 bg-gray-700 rounded-lg appearance-none cursor-pointer slider"
                                style={{
                                    background: `linear-gradient(to right, #3b82f6 0%, #3b82f6 ${(currentTime / duration) * 100}%, #374151 ${(currentTime / duration) * 100}%, #374151 100%)`
                                }}
                            />

                            {/* Time Display */}
                            <div className="flex justify-between text-sm text-gray-300">
                                <span>{formatTime(currentTime)}</span>
                                <span>{formatTime(duration)}</span>
                            </div>
                        </div>

                        {/* Control Buttons */}
                        <div className="flex items-center justify-center space-x-4">
                            <button
                                onClick={togglePlayPause}
                                className="flex items-center justify-center w-10 h-10 bg-blue-600 rounded-full hover:bg-blue-700 transition-colors"
                            >
                                {isPlaying ? (
                                    <svg className="w-5 h-5 text-white" fill="currentColor" viewBox="0 0 20 20">
                                        <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zM7 8a1 1 0 012 0v4a1 1 0 11-2 0V8zm5-1a1 1 0 00-1 1v4a1 1 0 102 0V8a1 1 0 00-1-1z" clipRule="evenodd" />
                                    </svg>
                                ) : (
                                    <svg className="w-5 h-5 text-white ml-0.5" fill="currentColor" viewBox="0 0 20 20">
                                        <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM9.555 7.168A1 1 0 008 8v4a1 1 0 001.555.832l3-2a1 1 0 000-1.664l-3-2z" clipRule="evenodd" />
                                    </svg>
                                )}
                            </button>
                        </div>
                    </div>
                )}

                {/* Footer with actions */}
                <div className="p-4 border-t">
                    <div className="flex space-x-2">
                        <button
                            onClick={handleDownload}
                            className="flex-1 px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 transition-colors flex items-center justify-center space-x-2"
                        >
                            <span>📥</span>
                            <span>Download</span>
                        </button>
                        <button
                            onClick={onClose}
                            className="px-4 py-2 bg-gray-300 text-gray-700 rounded hover:bg-gray-400 transition-colors"
                        >
                            Close
                        </button>
                    </div>
                </div>

                {/* Add CSS for custom slider styling */}
                <style dangerouslySetInnerHTML={{
                    __html: `
                        .slider::-webkit-slider-thumb {
                            appearance: none;
                            width: 16px;
                            height: 16px;
                            border-radius: 50%;
                            background: #3b82f6;
                            cursor: pointer;
                            border: 2px solid #ffffff;
                            box-shadow: 0 2px 4px rgba(0, 0, 0, 0.2);
                        }
                        
                        .slider::-moz-range-thumb {
                            width: 16px;
                            height: 16px;
                            border-radius: 50%;
                            background: #3b82f6;
                            cursor: pointer;
                            border: 2px solid #ffffff;
                            box-shadow: 0 2px 4px rgba(0, 0, 0, 0.2);
                        }
                    `
                }} />
            </div>
        </div>
    );
};

export default VideoPlayerModal; 