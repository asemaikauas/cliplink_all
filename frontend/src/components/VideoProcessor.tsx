import { useState, useEffect } from 'react';
import { useAuth } from '@clerk/clerk-react';
import VideoPlayerModal from './VideoPlayerModal';
import { apiUrl, clipUrl, config } from '../config';

interface VideoProcessorProps {
    initialUrl?: string;
    onUrlChange?: (url: string) => void;
}

interface ProcessingTask {
    task_id: string;
    status: 'pending' | 'processing' | 'done' | 'failed';
    progress: number;
    stage: string;
    message: string;
    clips?: Array<{
        id: string;
        title: string;
        start: number;
        end: number;
        duration: number;
        url?: string;
    }>;
    error?: string;
}

interface Clip {
    id: string;
    title: string;
    start_time: number;
    end_time: number;
    duration: number;
    s3_url: string;
    thumbnail_url?: string;
    clip_id?: string;
}



const VideoProcessor: React.FC<VideoProcessorProps> = ({ initialUrl = '', onUrlChange }) => {
    // const { getToken } = useAuth();
    const [youtubeUrl, setYoutubeUrl] = useState(initialUrl);
    const [isProcessing, setIsProcessing] = useState(false);
    const [currentTask, setCurrentTask] = useState<ProcessingTask | null>(null);
    const [clips, setClips] = useState<Clip[]>([]);
    const [error, setError] = useState<string | null>(null);
    const [hasActiveTask, setHasActiveTask] = useState(false);
    const [selectedClip, setSelectedClip] = useState<Clip | null>(null);
    const [thumbnailErrors, setThumbnailErrors] = useState<Set<string>>(new Set());

    // Load clips and YouTube URL from localStorage on component mount
    useEffect(() => {
        const savedData = localStorage.getItem('cliplink_data');
        if (savedData) {
            try {
                const parsedData = JSON.parse(savedData);
                if (parsedData.clips) {
                    setClips(parsedData.clips);
                }
                if (parsedData.youtubeUrl && !youtubeUrl) {
                    setYoutubeUrl(parsedData.youtubeUrl);
                }
            } catch (error) {
                console.error('Failed to parse saved data:', error);
                localStorage.removeItem('cliplink_data');
            }
        }
    }, []);

    // Save clips and YouTube URL to localStorage whenever they change
    useEffect(() => {
        if (clips.length > 0 && youtubeUrl) {
            const dataToSave = {
                clips: clips,
                youtubeUrl: youtubeUrl,
                savedAt: new Date().toISOString()
            };
            localStorage.setItem('cliplink_data', JSON.stringify(dataToSave));
        }
    }, [clips, youtubeUrl]);

    // Check for any active processing tasks on mount
    useEffect(() => {
        checkForActiveTask();
    }, []);

    // Notify parent component when URL changes
    useEffect(() => {
        if (onUrlChange) {
            onUrlChange(youtubeUrl);
        }
    }, [youtubeUrl, onUrlChange]);

    const checkForActiveTask = async () => {
        // Note: Since we're using the comprehensive workflow which doesn't save to database,
        // we can't check for active tasks from the database. For now, we assume no active tasks.
        // In a production setup, you might want to store active task IDs in localStorage
        // or implement a different task tracking mechanism.
        setHasActiveTask(false);
    };

    const startVideoProcessing = async () => {
        if (!youtubeUrl.trim()) {
            setError('Please enter a YouTube URL');
            return;
        }

        if (hasActiveTask) {
            setError('You already have a video being processed. Please wait for it to complete.');
            return;
        }

        setIsProcessing(true);
        setError(null);
        setClips([]);
        setCurrentTask(null);
        setHasActiveTask(true);
        setThumbnailErrors(new Set());

        // Clear any saved data from localStorage when starting new processing
        localStorage.removeItem('cliplink_data');
        localStorage.removeItem('cliplink_clips'); // Remove old format if it exists

        try {
            // Start the comprehensive video processing
            const response = await fetch(apiUrl('/api/workflow/process-comprehensive-async'), {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    youtube_url: youtubeUrl.trim(),
                    quality: 'best',
                    create_vertical: true,
                    smoothing_strength: 'very_high',
                    burn_subtitles: true,
                    font_size: 15,
                    export_codec: 'h264'
                })
            });

            if (!response.ok) {
                throw new Error(`Processing failed: ${response.status} ${response.statusText}`);
            }

            const result = await response.json();
            console.log('🚀 Processing started:', result);

            if (result.task_id) {
                setCurrentTask({
                    task_id: result.task_id,
                    status: 'processing',
                    progress: 0,
                    stage: 'initializing',
                    message: 'Starting video processing...'
                });

                // Start polling for progress
                pollTaskProgress(result.task_id);
            } else {
                throw new Error('No task ID received from server');
            }

        } catch (err) {
            console.error('❌ Error starting video processing:', err);
            setError(err instanceof Error ? err.message : 'Failed to start processing');
            setIsProcessing(false);
            setHasActiveTask(false);
        }
    };

    const pollTaskProgress = async (taskId: string) => {
        const pollInterval = setInterval(async () => {
            try {
                const response = await fetch(apiUrl(`/api/workflow/status/${taskId}`), {
                    headers: {
                        'Content-Type': 'application/json'
                    }
                });

                if (!response.ok) {
                    throw new Error(`Status check failed: ${response.status}`);
                }

                const taskData = await response.json();
                console.log('📊 Task progress:', taskData);

                setCurrentTask(taskData);

                if (taskData.status === 'done') {
                    clearInterval(pollInterval);
                    setIsProcessing(false);
                    setHasActiveTask(false);

                    // Get clips from the task result
                    if (taskData.result && taskData.result.files_created && taskData.result.files_created.final_clip_paths) {
                        const clipPaths = taskData.result.files_created.final_clip_paths;
                        const segments = taskData.result.analysis_results?.segments || [];
                        const thumbnails = taskData.result.files_created?.thumbnails || [];

                        const generatedClips = clipPaths.map((path: string, index: number) => {
                            const segment = segments[index] || {};
                            const startTime = segment.start || 0;
                            const endTime = segment.end || 60;
                            const duration = segment.duration || (endTime - startTime);

                            // Find matching thumbnail
                            const thumbnail = thumbnails.find((t: any) =>
                                t.clip_path === path || t.clip_id?.includes(String(index + 1))
                            );

                            return {
                                id: `clip-${index}`,
                                title: segment.title || `Clip ${index + 1}`,
                                start_time: startTime,
                                end_time: endTime,
                                duration: duration,
                                s3_url: path,
                                thumbnail_url: thumbnail?.thumbnail_path ?
                                    `${config.API_BASE_URL}/${thumbnail.thumbnail_path}` : null,
                                clip_id: thumbnail?.clip_id
                            };
                        });
                        setClips(generatedClips);
                    }

                } else if (taskData.status === 'failed') {
                    clearInterval(pollInterval);
                    setIsProcessing(false);
                    setHasActiveTask(false);
                    setError(taskData.error || 'Processing failed');
                }

            } catch (err) {
                console.error('❌ Error polling task progress:', err);
                clearInterval(pollInterval);
                setIsProcessing(false);
                setHasActiveTask(false);
                setError('Failed to check processing status');
            }
        }, 2000); // Poll every 2 seconds
    };

    const formatTime = (seconds: number): string => {
        const mins = Math.floor(seconds / 60);
        const secs = Math.floor(seconds % 60);
        return `${mins}:${secs.toString().padStart(2, '0')}`;
    };

    const openYouTubeClip = (clip: Clip) => {
        // Extract YouTube video ID from the current URL
        const extractVideoId = (url: string) => {
            const regex = /(?:youtube\.com\/watch\?v=|youtu\.be\/|youtube\.com\/embed\/)([^&\n?#]+)/;
            const match = url.match(regex);
            return match ? match[1] : null;
        };

        const videoId = extractVideoId(youtubeUrl);
        if (videoId) {
            const startTime = Math.floor(clip.start_time);
            const youtubeClipUrl = `https://www.youtube.com/watch?v=${videoId}&t=${startTime}s`;
            window.open(youtubeClipUrl, '_blank');
        } else {
            console.error('Could not extract YouTube video ID from URL:', youtubeUrl);
        }
    };

    const handleDownload = (clip: Clip) => {
        try {
            const link = document.createElement('a');
            link.href = clipUrl(clip.s3_url);
            link.download = `${clip.title.replace(/[^a-zA-Z0-9]/g, '_')}.mp4`;
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
        } catch (error) {
            console.error('Download failed:', error);
            setError('Failed to download clip');
        }
    };

    const handleThumbnailError = (clipId: string) => {
        setThumbnailErrors(prev => new Set([...prev, clipId]));
    };

    const clearAllClips = () => {
        setClips([]);
        setYoutubeUrl('');
        localStorage.removeItem('cliplink_data');
        localStorage.removeItem('cliplink_clips'); // Remove old format if it exists
        setThumbnailErrors(new Set());
    };

    return (
        <div className="space-y-6">
            {/* URL Input Section */}
            <div className="bg-white rounded-lg shadow-md p-6">
                <h3 className="text-lg font-semibold text-gray-900 mb-4">
                    Generate Clips from YouTube Video
                </h3>

                <div className="flex gap-4">
                    <input
                        type="text"
                        value={youtubeUrl}
                        onChange={(e) => setYoutubeUrl(e.target.value)}
                        placeholder="Paste YouTube URL here..."
                        className="flex-1 px-4 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                        disabled={isProcessing || hasActiveTask}
                    />
                    <button
                        onClick={startVideoProcessing}
                        disabled={isProcessing || hasActiveTask || !youtubeUrl.trim()}
                        className="px-6 py-2 bg-blue-600 text-white font-medium rounded-md hover:bg-blue-700 disabled:bg-gray-400 disabled:cursor-not-allowed transition-colors"
                    >
                        {isProcessing || hasActiveTask ? 'Processing...' : 'Generate Clips'}
                    </button>
                </div>

                {hasActiveTask && !isProcessing && (
                    <div className="mt-4 p-4 bg-yellow-50 border border-yellow-200 rounded-md">
                        <p className="text-yellow-800 text-sm">
                            ⚠️ You have an active processing task. Please wait for it to complete before starting a new one.
                        </p>
                    </div>
                )}
            </div>

            {/* Error Display */}
            {error && (
                <div className="bg-red-50 border border-red-200 rounded-md p-4">
                    <div className="flex">
                        <div className="text-red-800">
                            <h4 className="font-medium">Error</h4>
                            <p className="text-sm mt-1">{error}</p>
                        </div>
                    </div>
                </div>
            )}

            {/* Processing Progress */}
            {currentTask && (
                <div className="bg-white rounded-lg shadow-md p-6">
                    <h3 className="text-lg font-semibold text-gray-900 mb-4">
                        Processing Progress
                    </h3>

                    <div className="space-y-4">
                        <div className="flex justify-between text-sm">
                            <span className="font-medium text-gray-700">Stage: {currentTask.stage}</span>
                            <span className="text-gray-500">{currentTask.progress}%</span>
                        </div>

                        <div className="w-full bg-gray-200 rounded-full h-2">
                            <div
                                className="bg-blue-600 h-2 rounded-full transition-all duration-300"
                                style={{ width: `${currentTask.progress}%` }}
                            ></div>
                        </div>

                        <p className="text-sm text-gray-600">{currentTask.message}</p>

                        {currentTask.status === 'processing' && (
                            <div className="flex items-center space-x-2">
                                <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-blue-600"></div>
                                <span className="text-sm text-gray-500">Processing...</span>
                            </div>
                        )}
                    </div>
                </div>
            )}

            {/* Generated Clips */}
            {clips.length > 0 && (
                <div className="bg-white rounded-lg shadow-md p-6">
                    <div className="flex justify-between items-center mb-4">
                        <h3 className="text-lg font-semibold text-gray-900">
                            Generated Clips ({clips.length})
                        </h3>
                        <button
                            onClick={clearAllClips}
                            className="px-3 py-1 bg-red-100 text-red-700 text-sm rounded hover:bg-red-200 transition-colors"
                        >
                            Clear All
                        </button>
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                        {clips.map((clip) => (
                            <div key={clip.id} className="border border-gray-200 rounded-lg overflow-hidden hover:shadow-lg transition-shadow">
                                {/* Thumbnail Container - 3:4 Aspect Ratio */}
                                <div className="relative aspect-[3/4] bg-gray-100 cursor-pointer group" onClick={() => setSelectedClip(clip)}>
                                    {clip.thumbnail_url && !thumbnailErrors.has(clip.id) ? (
                                        <>
                                            <img
                                                src={clip.thumbnail_url}
                                                alt={`${clip.title} thumbnail`}
                                                className="w-full h-full object-cover"
                                                onError={() => handleThumbnailError(clip.id)}
                                            />
                                            {/* Play button overlay */}
                                            <div className="absolute inset-0 bg-black bg-opacity-0 group-hover:bg-opacity-30 transition-all duration-200 flex items-center justify-center">
                                                <div className="bg-blue-600 text-white rounded-full p-3 opacity-0 group-hover:opacity-100 transition-opacity duration-200">
                                                    <svg className="w-6 h-6" fill="currentColor" viewBox="0 0 20 20">
                                                        <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM9.555 7.168A1 1 0 008 8v4a1 1 0 001.555.832l3-2a1 1 0 000-1.664l-3-2z" clipRule="evenodd" />
                                                    </svg>
                                                </div>
                                            </div>
                                            {/* Duration badge */}
                                            <div className="absolute bottom-2 right-2 bg-black bg-opacity-75 text-white text-xs px-2 py-1 rounded">
                                                {formatTime(clip.duration)}
                                            </div>
                                        </>
                                    ) : (
                                        <div className="w-full h-full flex flex-col items-center justify-center text-gray-400 cursor-pointer">
                                            <div className="text-4xl mb-2">🎬</div>
                                            <div className="text-sm text-center px-2">
                                                {thumbnailErrors.has(clip.id) ? 'Thumbnail unavailable' : 'Loading thumbnail...'}
                                            </div>
                                            <div className="text-xs text-gray-500 mt-1">{formatTime(clip.duration)}</div>
                                        </div>
                                    )}
                                </div>

                                {/* Clip Info */}
                                <div className="p-4 space-y-3">
                                    <h4 className="font-medium text-gray-900 text-sm line-clamp-2 min-h-[2.5rem]">
                                        {clip.title}
                                    </h4>

                                    <div className="text-xs text-gray-500 space-y-1">
                                        <div>Time: {formatTime(clip.start_time)} - {formatTime(clip.end_time)}</div>
                                        {clip.s3_url.includes('subtitled_') && (
                                            <div className="text-blue-600 font-medium">✨ With subtitles</div>
                                        )}
                                    </div>

                                    {/* Action Buttons */}
                                    <div className="grid grid-cols-2 gap-2 pt-2">
                                        <button
                                            onClick={() => setSelectedClip(clip)}
                                            className="px-3 py-2 bg-blue-600 text-white text-xs rounded hover:bg-blue-700 transition-colors flex items-center justify-center space-x-1"
                                        >
                                            <span>▶</span>
                                            <span>Play</span>
                                        </button>

                                        <button
                                            onClick={() => handleDownload(clip)}
                                            className="px-3 py-2 bg-green-600 text-white text-xs rounded hover:bg-green-700 transition-colors flex items-center justify-center space-x-1"
                                        >
                                            <span>📥</span>
                                            <span>Download</span>
                                        </button>
                                    </div>

                                    <button
                                        onClick={() => openYouTubeClip(clip)}
                                        className="w-full px-3 py-2 bg-red-600 text-white text-xs rounded hover:bg-red-700 transition-colors flex items-center justify-center space-x-1"
                                    >
                                        <span>🎬</span>
                                        <span>Watch on YouTube</span>
                                    </button>
                                </div>
                            </div>
                        ))}
                    </div>
                </div>
            )}

            {/* Empty State */}
            {!isProcessing && !currentTask && clips.length === 0 && (
                <div className="bg-white rounded-lg shadow-md p-12 text-center">
                    <div className="text-gray-400 mb-4">
                        <div className="text-6xl mb-4">🎬</div>
                        <h3 className="text-lg font-medium text-gray-900 mb-2">No clips yet</h3>
                        <p className="text-gray-500">
                            Enter a YouTube URL above and click "Generate Clips" to get started.
                        </p>
                    </div>
                </div>
            )}

            {/* Video Player Modal */}
            {selectedClip && (
                <VideoPlayerModal
                    clip={selectedClip}
                    isOpen={true}
                    onClose={() => setSelectedClip(null)}
                />
            )}
        </div>
    );
};

export default VideoProcessor; 