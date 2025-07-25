import React, { useState, useEffect, useMemo } from 'react';
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
    current_step?: string;
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
    blob_url: string;
    thumbnail_url?: string;
    clip_id?: string;
}



const VideoProcessor: React.FC<VideoProcessorProps> = ({ initialUrl = '', onUrlChange }) => {
    const { getToken, isSignedIn, isLoaded } = useAuth();
    const [youtubeUrl, setYoutubeUrl] = useState(initialUrl);
    const [isProcessing, setIsProcessing] = useState(false);
    const [currentTask, setCurrentTask] = useState<ProcessingTask | null>(null);
    const [clips, setClips] = useState<Clip[]>([]);
    const [error, setError] = useState<string | null>(null);
    const [hasActiveTask, setHasActiveTask] = useState(false);
    const [selectedClip, setSelectedClip] = useState<Clip | null>(null);
    const [thumbnailErrors, setThumbnailErrors] = useState<Set<string>>(new Set());
    const [isRestoringTask, setIsRestoringTask] = useState(false);

    // Authentication check
    if (!isLoaded) {
        return (
            <div className="flex items-center justify-center min-h-64">
                <div className="text-center">
                    <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto"></div>
                    <p className="mt-2 text-gray-600">Loading...</p>
                </div>
            </div>
        );
    }

    if (!isSignedIn) {
        return (
            <div className="flex items-center justify-center min-h-64">
                <div className="text-center max-w-md mx-auto p-8 bg-white rounded-lg shadow-md">
                    <div className="text-blue-600 text-4xl mb-4">🔐</div>
                    <h3 className="text-lg font-semibold text-gray-900 mb-2">Authentication Required</h3>
                    <p className="text-gray-600 mb-4">
                        Please sign in to process YouTube videos and create clips. Your videos will be saved to your account and accessible across devices.
                    </p>
                    <div className="text-sm text-gray-500">
                        ✅ Secure video processing<br />
                        ✅ Persistent video storage<br />
                        ✅ Access from any device
                    </div>
                </div>
            </div>
        );
    }

    // Load user's recent videos on mount
    useEffect(() => {
        if (isSignedIn) {
            fetchUserVideos();
        }
    }, [isSignedIn]);

    // Check for any active processing tasks on mount
    useEffect(() => {
        if (isSignedIn) {
            checkForActiveTask();
        }
    }, [isSignedIn]);

    // Notify parent component when URL changes
    useEffect(() => {
        if (onUrlChange) {
            onUrlChange(youtubeUrl);
        }
    }, [youtubeUrl, onUrlChange]);

    // Cleanup function for component unmount
    useEffect(() => {
        return () => {
            // Clean up any active polling intervals when component unmounts
            // Note: The polling intervals are cleared in the pollTaskProgress function
            // when tasks complete, so this is just a safety measure
        };
    }, []);

    // Handle page visibility changes (when user switches tabs or minimizes browser)
    useEffect(() => {
        const handleVisibilityChange = () => {
            if (!document.hidden && hasActiveTask && currentTask) {
                // User came back to the tab, refresh the task status
                console.log('🔄 Page became visible, refreshing task status...');
                if (currentTask.task_id) {
                    pollTaskProgress(currentTask.task_id);
                }
            }
        };

        document.addEventListener('visibilitychange', handleVisibilityChange);
        return () => {
            document.removeEventListener('visibilitychange', handleVisibilityChange);
        };
    }, [hasActiveTask, currentTask]);

    const fetchUserVideos = async () => {
        try {
            const token = await getToken({ template: "cliplink" });

            const response = await fetch(apiUrl('/api/videos?per_page=20'), {
                headers: {
                    'Authorization': `Bearer ${token}`,
                    'Content-Type': 'application/json'
                }
            });

            if (!response.ok) {
                console.warn('Failed to fetch user videos:', response.status);
                return;
            }

            const data = await response.json();

            // Convert user videos to clips format for display
            const allClips: Clip[] = [];

            // Fetch clips for each completed video
            for (const video of data.videos) {
                if (video.status === 'done') {
                    try {
                        const videoDetailResponse = await fetch(apiUrl(`/api/videos/${video.id}`), {
                            headers: {
                                'Authorization': `Bearer ${token}`,
                                'Content-Type': 'application/json'
                            }
                        });

                        if (videoDetailResponse.ok) {
                            const videoDetail = await videoDetailResponse.json();
                            videoDetail.clips?.forEach((clip: any, index: number) => {
                                // Log warnings for missing metadata
                                if (!clip.title) {
                                    console.warn(`⚠️ Clip ${index + 1} (ID: ${clip.id}) is missing title. Using fallback.`);
                                }
                                if (!clip.thumbnail_url) {
                                    console.warn(`⚠️ Clip ${index + 1} (ID: ${clip.id}) is missing thumbnail_url. Thumbnail will not be displayed.`);
                                }
                                if (clip.duration === null || clip.duration === undefined) {
                                    console.warn(`⚠️ Clip ${index + 1} (ID: ${clip.id}) is missing duration. Using calculated duration from start/end times.`);
                                }

                                allClips.push({
                                    id: clip.id,
                                    title: clip.title || `${video.title} - Clip ${index + 1}`,
                                    start_time: clip.start_time,
                                    end_time: clip.end_time,
                                    duration: clip.duration || (clip.end_time - clip.start_time),
                                    blob_url: clip.blob_url, // Use the SAS URL from backend
                                    thumbnail_url: clip.thumbnail_url,
                                    clip_id: clip.id
                                });
                            });
                        }
                    } catch (error) {
                        console.error('Error fetching video details:', error);
                    }
                }
            }

            // Update clips state with user's videos
            if (allClips.length > 0) {
                setClips(allClips);
                console.log(`📊 Loaded ${allClips.length} clips from user's videos`);
            }

        } catch (error) {
            console.error('Error fetching user videos:', error);
        }
    };

    const checkForActiveTask = async () => {
        try {
            // Check for active task ID in localStorage
            const activeTaskId = localStorage.getItem('cliplink_active_task_id');
            const activeTaskData = localStorage.getItem('cliplink_active_task_data');

            if (activeTaskId && activeTaskData) {
                setIsRestoringTask(true);
                try {
                    const taskData = JSON.parse(activeTaskData);

                    // Check if the task is still active by polling the backend
                    const response = await fetch(apiUrl(`/api/workflow/status/${activeTaskId}`), {
                        headers: {
                            'Content-Type': 'application/json'
                        }
                    });

                    if (response.ok) {
                        const currentTaskStatus = await response.json();
                        console.log('🔄 Found active task on page load:', currentTaskStatus);

                        // If task is still processing, restore the state
                        if (currentTaskStatus.status === 'processing' || currentTaskStatus.status === 'pending') {
                            setCurrentTask(currentTaskStatus);
                            setIsProcessing(true);
                            setHasActiveTask(true);

                            // Restore YouTube URL if not already set
                            if (currentTaskStatus.youtube_url && !youtubeUrl) {
                                setYoutubeUrl(currentTaskStatus.youtube_url);
                            }

                            // Resume polling
                            pollTaskProgress(activeTaskId);
                            setIsRestoringTask(false);
                            return;
                        } else if (currentTaskStatus.status === 'done') {
                            // Task completed while page was closed, restore results
                            console.log('✅ Task completed while page was closed, restoring results');
                            setCurrentTask(currentTaskStatus);
                            setIsProcessing(false);
                            setHasActiveTask(false);

                            // Restore clips from the completed task
                            if (currentTaskStatus.result && currentTaskStatus.result.files_created && currentTaskStatus.result.files_created.final_clip_paths) {
                                const clipPaths = currentTaskStatus.result.files_created.final_clip_paths;
                                const segments = currentTaskStatus.result.analysis_results?.segments || [];
                                const thumbnails = currentTaskStatus.result.files_created?.thumbnails || [];

                                const generatedClips = clipPaths.map((path: string, index: number) => {
                                    const segment = segments[index] || {};
                                    const startTime = segment.start || 0;
                                    const endTime = segment.end || 60;
                                    const duration = segment.duration || (endTime - startTime);

                                    const thumbnail = thumbnails.find((t: any) =>
                                        t.clip_path === path || t.clip_id?.includes(String(index + 1))
                                    );

                                    return {
                                        id: `clip-${index}`,
                                        title: segment.title || `Clip ${index + 1}`,
                                        start_time: startTime,
                                        end_time: endTime,
                                        duration: duration,
                                        blob_url: path,
                                        thumbnail_url: thumbnail?.thumbnail_path ?
                                            `${config.API_BASE_URL}/${thumbnail.thumbnail_path}` : null,
                                        clip_id: thumbnail?.clip_id
                                    };
                                });
                                setClips(generatedClips);
                            }

                            // Restore YouTube URL if not already set
                            if (currentTaskStatus.youtube_url && !youtubeUrl) {
                                setYoutubeUrl(currentTaskStatus.youtube_url);
                            }

                            // Clean up localStorage
                            localStorage.removeItem('cliplink_active_task_id');
                            localStorage.removeItem('cliplink_active_task_data');
                            setIsRestoringTask(false);
                            return;
                        } else if (currentTaskStatus.status === 'failed') {
                            // Task failed while page was closed
                            console.log('❌ Task failed while page was closed');
                            setError(currentTaskStatus.error || 'Processing failed');
                            setCurrentTask(currentTaskStatus);
                            setIsProcessing(false);
                            setHasActiveTask(false);

                            // Restore YouTube URL if not already set
                            if (currentTaskStatus.youtube_url && !youtubeUrl) {
                                setYoutubeUrl(currentTaskStatus.youtube_url);
                            }

                            // Clean up localStorage
                            localStorage.removeItem('cliplink_active_task_id');
                            localStorage.removeItem('cliplink_active_task_data');
                            setIsRestoringTask(false);
                            return;
                        }
                    }
                } catch (error) {
                    console.error('Error checking active task status:', error);
                    setIsRestoringTask(false);
                }
            }

            // No active task found or task is no longer valid
            setHasActiveTask(false);
            localStorage.removeItem('cliplink_active_task_id');
            localStorage.removeItem('cliplink_active_task_data');
            setIsRestoringTask(false);

        } catch (error) {
            console.error('Error checking for active tasks:', error);
            setHasActiveTask(false);
            setIsRestoringTask(false);
        }
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
        setCurrentTask(null);
        setHasActiveTask(true);
        setThumbnailErrors(new Set());

        try {
            const token = await getToken({ template: "cliplink" });

            // Start the comprehensive video processing with H.264-first strategy
            // Using best quality with intelligent fallback to avoid AV1 conversion issues
            const response = await fetch(apiUrl('/api/workflow/process-comprehensive-async'), {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${token}`
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

                // Save active task ID and data to localStorage
                localStorage.setItem('cliplink_active_task_id', result.task_id);
                localStorage.setItem('cliplink_active_task_data', JSON.stringify({
                    task_id: result.task_id,
                    youtube_url: youtubeUrl,
                    status: 'processing',
                    progress: 0,
                    stage: 'initializing',
                    message: 'Starting video processing...'
                }));

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
        let retryCount = 0;
        const maxRetries = 5;

        const pollInterval = setInterval(async () => {
            try {
                console.log(`🔄 Polling task status: ${taskId} (attempt ${retryCount + 1})`);
                console.log(`🌐 API URL: ${apiUrl(`/api/workflow/status/${taskId}`)}`);

                const response = await fetch(apiUrl(`/api/workflow/status/${taskId}`), {
                    headers: {
                        'Content-Type': 'application/json'
                    }
                });

                if (!response.ok) {
                    throw new Error(`Status check failed: ${response.status} ${response.statusText}`);
                }

                const taskData = await response.json();
                console.log('📊 Task progress:', taskData);

                // Reset retry count on successful response
                retryCount = 0;

                setCurrentTask(taskData);

                // Update localStorage with current task data
                localStorage.setItem('cliplink_active_task_data', JSON.stringify(taskData));

                if (taskData.status === 'done') {
                    clearInterval(pollInterval);
                    setIsProcessing(false);
                    setHasActiveTask(false);

                    // Clean up localStorage when task completes successfully
                    localStorage.removeItem('cliplink_active_task_id');
                    localStorage.removeItem('cliplink_active_task_data');

                    // Fetch fresh clips from the database after processing completes
                    setTimeout(() => {
                        fetchUserVideos();
                    }, 2000); // Wait 2 seconds for database to be updated

                } else if (taskData.status === 'failed') {
                    clearInterval(pollInterval);
                    setIsProcessing(false);
                    setHasActiveTask(false);
                    setError(taskData.error || 'Processing failed');

                    // Clean up localStorage when task fails
                    localStorage.removeItem('cliplink_active_task_id');
                    localStorage.removeItem('cliplink_active_task_data');
                }

            } catch (err) {
                retryCount++;
                console.error(`❌ Error polling task progress (attempt ${retryCount}):`, err);
                console.error(`🔍 Error details:`, {
                    message: err instanceof Error ? err.message : 'Unknown error',
                    taskId: taskId,
                    apiUrl: apiUrl(`/api/workflow/status/${taskId}`),
                    config: config.API_BASE_URL
                });

                // Only show error after max retries
                if (retryCount >= maxRetries) {
                    clearInterval(pollInterval);
                    setIsProcessing(false);
                    setHasActiveTask(false);

                    const errorMessage = err instanceof Error ? err.message : 'Unknown error';
                    setError(`Failed to check processing status: ${errorMessage}. Please check if the backend is running at ${config.API_BASE_URL}`);

                    // Clean up localStorage on error
                    localStorage.removeItem('cliplink_active_task_id');
                    localStorage.removeItem('cliplink_active_task_data');
                } else {
                    // Continue polling on retry
                    console.log(`🔄 Retrying in 2 seconds... (${retryCount}/${maxRetries})`);
                }
            }
        }, 2000); // Poll every 2 seconds
    };

    const formatTime = (seconds: number): string => {
        const mins = Math.floor(seconds / 60);
        const secs = Math.floor(seconds % 60);
        return `${mins}:${secs.toString().padStart(2, '0')}`;
    };

    const getWaitTimeDisplay = (task: ProcessingTask): string => {
        if (task.status === 'done') {
            return 'Ready! 🎉';
        }

        if (task.status === 'failed') {
            return 'Failed ❌';
        }

        // Map stages to estimated completion times (in minutes)
        const stageTimeMap: { [key: string]: number } = {
            'queued': 8,
            'init': 8,
            'video_info': 7.5,
            'download': 7,
            'transcript': 6,
            'analysis': 5,
            'parallel_processing': 3,
            'finalizing': 1,
            'azure_upload': 2,
            'processing': 6, // fallback
            'pending': 8 // fallback
        };

        // Get the current stage and its estimated remaining time
        const currentStage = task.stage || task.current_step || 'processing';
        const estimatedTotalTime = stageTimeMap[currentStage] || 6;

        // Calculate remaining time based on progress
        const progressPercent = task.progress || 0;
        const remainingPercent = Math.max(0, 100 - progressPercent);
        const remainingMinutes = Math.ceil((estimatedTotalTime * remainingPercent) / 100);

        // Ensure minimum of 1 minute and maximum of estimated time
        const displayMinutes = Math.max(1, Math.min(remainingMinutes, estimatedTotalTime));

        // Format the display text with more dynamic messaging
        if (displayMinutes === 1) {
            return `Almost done! 1 min ⏳`;
        } else if (displayMinutes <= 2) {
            return `Wait: ${displayMinutes} min ⏳`;
        } else if (displayMinutes <= 3) {
            return `Wait: ${displayMinutes} min ⏳`;
        } else if (displayMinutes >= 7) {
            return `Wait: ${displayMinutes} min ⏳`;
        } else {
            return `Wait: ${displayMinutes} min ⏳`;
        }
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
            link.href = clip.blob_url;
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
        setCurrentTask(null);
        setIsProcessing(false);
        setHasActiveTask(false);
        setError(null);
        setIsRestoringTask(false);
        localStorage.removeItem('cliplink_data');
        localStorage.removeItem('cliplink_clips'); // Remove old format if it exists
        localStorage.removeItem('cliplink_active_task_id');
        localStorage.removeItem('cliplink_active_task_data');
        setThumbnailErrors(new Set());
    };

    const testBackendConnection = async () => {
        try {
            console.log('🔍 Testing backend connection...');
            console.log('🌐 API Base URL:', config.API_BASE_URL);

            const response = await fetch(apiUrl('/health'), {
                method: 'GET',
                headers: {
                    'Content-Type': 'application/json'
                }
            });

            if (response.ok) {
                const data = await response.json();
                console.log('✅ Backend connection successful:', data);
                return true;
            } else {
                console.error('❌ Backend health check failed:', response.status, response.statusText);
                return false;
            }
        } catch (err) {
            console.error('❌ Backend connection test failed:', err);
            return false;
        }
    };

    return (
        <div className="space-y-6">
            {/* Section Header */}
            <div className="mb-6">
                <h2 className="text-2xl font-bold text-gray-900 mb-2">🎬 Processing Progress</h2>
                <p className="text-gray-600">Transform YouTube videos into viral vertical clips with AI-powered analysis</p>
            </div>

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

            {/* Task Restoration Notification */}
            {isRestoringTask && (
                <div className="bg-blue-50 border border-blue-200 rounded-md p-4">
                    <div className="flex items-center">
                        <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-blue-600 mr-3"></div>
                        <div className="text-blue-800">
                            <h4 className="font-medium">Restoring Session</h4>
                            <p className="text-sm mt-1">Checking for ongoing video processing...</p>
                        </div>
                    </div>
                </div>
            )}

            {/* Error Display */}
            {error && (
                <div className="bg-red-50 border border-red-200 rounded-md p-4">
                    <div className="flex justify-between items-start">
                        <div className="text-red-800">
                            <h4 className="font-medium">Error</h4>
                            <p className="text-sm mt-1">{error}</p>
                        </div>
                        <div className="flex gap-2">
                            {error.includes('Failed to check processing status') && currentTask?.task_id && (
                                <button
                                    onClick={() => {
                                        setError(null);
                                        setIsProcessing(true);
                                        setHasActiveTask(true);
                                        pollTaskProgress(currentTask.task_id);
                                    }}
                                    className="px-3 py-1 bg-red-600 text-white text-sm rounded hover:bg-red-700 transition-colors"
                                >
                                    Retry
                                </button>
                            )}
                            <button
                                onClick={async () => {
                                    const isConnected = await testBackendConnection();
                                    if (isConnected) {
                                        setError('Backend connection successful! Please try again.');
                                    } else {
                                        setError('Backend connection failed. Please check if the backend is running.');
                                    }
                                }}
                                className="px-3 py-1 bg-blue-600 text-white text-sm rounded hover:bg-blue-700 transition-colors"
                            >
                                Test Connection
                            </button>
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
                            <span className="font-medium text-gray-700">{getWaitTimeDisplay(currentTask)}</span>
                            <span className="text-gray-500">{currentTask.progress}%</span>
                        </div>

                        <div className="w-full bg-gray-200 rounded-full h-2">
                            <div
                                className="bg-blue-600 h-2 rounded-full transition-all duration-300"
                                style={{ width: `${currentTask.progress}%` }}
                            ></div>
                        </div>

                        <p className="text-sm text-gray-600">
                            {currentTask.status === 'done' ? 'Your clips are ready!' : currentTask.message}
                        </p>

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
                                        {clip.blob_url.includes('subtitled_') && (
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