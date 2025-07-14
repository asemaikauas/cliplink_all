#!/usr/bin/env python3
"""
Скрипт для проверки качества скачанных видео
Показывает разрешение, битрейт, размер файла и другие параметры качества
"""

import os
import json
import subprocess
from pathlib import Path
from typing import Dict, List, Optional
import shutil

def get_ffprobe_info(video_path: Path) -> Optional[Dict]:
    """
    Получить детальную информацию о видео с помощью ffprobe
    """
    if not shutil.which('ffprobe'):
        print("⚠️ ffprobe не найден. Установите ffmpeg для полной информации.")
        return None
    
    try:
        cmd = [
            'ffprobe', '-v', 'quiet', '-print_format', 'json', '-show_format', '-show_streams',
            str(video_path)
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        
        if result.returncode == 0:
            return json.loads(result.stdout)
        else:
            print(f"❌ Ошибка ffprobe: {result.stderr}")
            return None
    except Exception as e:
        print(f"❌ Ошибка при выполнении ffprobe: {e}")
        return None

def format_file_size(size_bytes: int) -> str:
    """
    Форматировать размер файла в читаемый вид
    """
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    elif size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.1f} MB"
    else:
        return f"{size_bytes / (1024 * 1024 * 1024):.1f} GB"

def format_bitrate(bitrate: int) -> str:
    """
    Форматировать битрейт в читаемый вид
    """
    if bitrate < 1000:
        return f"{bitrate} bps"
    elif bitrate < 1000000:
        return f"{bitrate / 1000:.1f} Kbps"
    else:
        return f"{bitrate / 1000000:.1f} Mbps"

def get_quality_rating(width: int, height: int) -> str:
    """
    Определить рейтинг качества на основе разрешения
    """
    if height >= 4320:
        return "🏆 8K (Ultra)"
    elif height >= 2160:
        return "💎 4K (Very High)"
    elif height >= 1440:
        return "⭐ 2K/1440p (High)"
    elif height >= 1080:
        return "✨ Full HD (Good)"
    elif height >= 720:
        return "📺 HD (Standard)"
    elif height >= 480:
        return "📱 SD (Low)"
    else:
        return "❌ Very Low"

def analyze_video_quality(video_path: Path) -> Dict:
    """
    Анализировать качество видео
    """
    analysis = {
        'file_path': str(video_path),
        'file_name': video_path.name,
        'file_size': video_path.stat().st_size,
        'file_size_formatted': format_file_size(video_path.stat().st_size)
    }
    
    # Получить информацию с помощью ffprobe
    ffprobe_data = get_ffprobe_info(video_path)
    
    if ffprobe_data:
        # Найти видео поток
        video_stream = None
        audio_stream = None
        
        for stream in ffprobe_data.get('streams', []):
            if stream.get('codec_type') == 'video' and not video_stream:
                video_stream = stream
            elif stream.get('codec_type') == 'audio' and not audio_stream:
                audio_stream = stream
        
        # Информация о видео
        if video_stream:
            width = int(video_stream.get('width', 0))
            height = int(video_stream.get('height', 0))
            
            analysis.update({
                'width': width,
                'height': height,
                'resolution': f"{width}x{height}",
                'quality_rating': get_quality_rating(width, height),
                'video_codec': video_stream.get('codec_name', 'unknown'),
                'video_profile': video_stream.get('profile', 'unknown'),
                'fps': float(video_stream.get('r_frame_rate', '0/1').split('/')[0]) / float(video_stream.get('r_frame_rate', '0/1').split('/')[1]) if '/' in str(video_stream.get('r_frame_rate', '0/1')) else 0,
                'pixel_format': video_stream.get('pix_fmt', 'unknown')
            })
            
            # Битрейт видео
            if 'bit_rate' in video_stream:
                video_bitrate = int(video_stream['bit_rate'])
                analysis['video_bitrate'] = video_bitrate
                analysis['video_bitrate_formatted'] = format_bitrate(video_bitrate)
        
        # Информация об аудио
        if audio_stream:
            analysis.update({
                'audio_codec': audio_stream.get('codec_name', 'unknown'),
                'audio_channels': audio_stream.get('channels', 0),
                'audio_sample_rate': audio_stream.get('sample_rate', 0)
            })
            
            if 'bit_rate' in audio_stream:
                audio_bitrate = int(audio_stream['bit_rate'])
                analysis['audio_bitrate'] = audio_bitrate
                analysis['audio_bitrate_formatted'] = format_bitrate(audio_bitrate)
        
        # Общая информация
        format_data = ffprobe_data.get('format', {})
        if 'duration' in format_data:
            duration = float(format_data['duration'])
            analysis['duration'] = duration
            analysis['duration_formatted'] = f"{int(duration // 60)}:{int(duration % 60):02d}"
        
        if 'bit_rate' in format_data:
            total_bitrate = int(format_data['bit_rate'])
            analysis['total_bitrate'] = total_bitrate
            analysis['total_bitrate_formatted'] = format_bitrate(total_bitrate)
    
    return analysis

def print_video_quality(analysis: Dict):
    """
    Красиво вывести информацию о качестве видео
    """
    print(f"\n{'='*60}")
    print(f"📁 Файл: {analysis['file_name']}")
    print(f"{'='*60}")
    
    # Основная информация
    print(f"📏 Размер файла: {analysis['file_size_formatted']}")
    
    if 'resolution' in analysis:
        print(f"🎯 Разрешение: {analysis['resolution']}")
        print(f"⭐ Качество: {analysis['quality_rating']}")
        print(f"🎬 FPS: {analysis.get('fps', 'N/A'):.1f}")
        
        if 'duration_formatted' in analysis:
            print(f"⏱️ Длительность: {analysis['duration_formatted']}")
    
    # Видео информация
    print(f"\n🎥 ВИДЕО:")
    if 'video_codec' in analysis:
        print(f"   Кодек: {analysis['video_codec']}")
        print(f"   Профиль: {analysis['video_profile']}")
        print(f"   Пиксельный формат: {analysis['pixel_format']}")
        
        if 'video_bitrate_formatted' in analysis:
            print(f"   Битрейт: {analysis['video_bitrate_formatted']}")
    
    # Аудио информация
    print(f"\n🔊 АУДИО:")
    if 'audio_codec' in analysis:
        print(f"   Кодек: {analysis['audio_codec']}")
        print(f"   Каналы: {analysis['audio_channels']}")
        print(f"   Частота дискретизации: {analysis.get('audio_sample_rate', 0)} Hz")
        
        if 'audio_bitrate_formatted' in analysis:
            print(f"   Битрейт: {analysis['audio_bitrate_formatted']}")
    
    # Общий битрейт
    if 'total_bitrate_formatted' in analysis:
        print(f"\n📊 Общий битрейт: {analysis['total_bitrate_formatted']}")

def scan_downloads_folder(downloads_dir: Path = Path("downloads")) -> List[Path]:
    """
    Найти все видео файлы в папке downloads
    """
    if not downloads_dir.exists():
        print(f"❌ Папка {downloads_dir} не найдена")
        return []
    
    video_extensions = ['.mp4', '.mkv', '.avi', '.mov', '.webm']
    video_files = []
    
    for ext in video_extensions:
        video_files.extend(downloads_dir.glob(f"*{ext}"))
    
    return sorted(video_files)

def main():
    """
    Основная функция для проверки качества видео
    """
    print("🔍 Проверка качества скачанных видео")
    print("="*60)
    
    # Перейти в папку backend если нужно
    if Path("backend").exists() and not Path("downloads").exists():
        os.chdir("backend")
        print("📂 Переключился в папку backend")
    
    downloads_dir = Path("downloads")
    video_files = scan_downloads_folder(downloads_dir)
    
    if not video_files:
        print("❌ Видео файлы не найдены в папке downloads")
        print(f"📁 Проверьте наличие файлов в: {downloads_dir.absolute()}")
        return
    
    print(f"✅ Найдено {len(video_files)} видео файлов")
    
    # Анализировать каждое видео
    all_analyses = []
    
    for video_file in video_files:
        try:
            analysis = analyze_video_quality(video_file)
            all_analyses.append(analysis)
            print_video_quality(analysis)
        except Exception as e:
            print(f"❌ Ошибка при анализе {video_file.name}: {e}")
    
    # Сводная таблица
    if all_analyses:
        print(f"\n{'='*80}")
        print("📊 СВОДНАЯ ТАБЛИЦА КАЧЕСТВА")
        print(f"{'='*80}")
        print(f"{'Файл':<40} {'Разрешение':<12} {'Размер':<10} {'Качество':<15}")
        print("-" * 80)
        
        for analysis in all_analyses:
            filename = analysis['file_name'][:37] + "..." if len(analysis['file_name']) > 40 else analysis['file_name']
            resolution = analysis.get('resolution', 'N/A')
            file_size = analysis['file_size_formatted']
            quality = analysis.get('quality_rating', 'N/A').split(' ')[1] if ' ' in analysis.get('quality_rating', '') else analysis.get('quality_rating', 'N/A')
            
            print(f"{filename:<40} {resolution:<12} {file_size:<10} {quality:<15}")
    
    print(f"\n🎉 Анализ завершен! Проверено {len(all_analyses)} файлов.")

if __name__ == "__main__":
    main() 