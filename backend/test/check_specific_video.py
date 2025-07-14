#!/usr/bin/env python3
"""
Скрипт для проверки качества конкретного видео файла
Использование: python check_specific_video.py path/to/video.mp4
"""

import sys
import os
from pathlib import Path

# Добавить путь к модулям приложения
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from backend.test.check_video_quality import analyze_video_quality, print_video_quality

def main():
    """
    Проверить качество конкретного видео файла
    """
    if len(sys.argv) != 2:
        print("❌ Использование: python check_specific_video.py path/to/video.mp4")
        print("\nПример:")
        print("  python check_specific_video.py downloads/video.mp4")
        print("  python check_specific_video.py ../downloads/UHQ-video.mp4")
        return
    
    video_path = Path(sys.argv[1])
    
    if not video_path.exists():
        print(f"❌ Файл не найден: {video_path}")
        return
    
    if not video_path.is_file():
        print(f"❌ Указанный путь не является файлом: {video_path}")
        return
    
    # Проверить расширение
    video_extensions = ['.mp4', '.mkv', '.avi', '.mov', '.webm', '.flv', '.m4v']
    if video_path.suffix.lower() not in video_extensions:
        print(f"⚠️ Предупреждение: {video_path.suffix} может не быть видео файлом")
    
    print(f"🔍 Анализ видео: {video_path.name}")
    print("="*60)
    
    try:
        analysis = analyze_video_quality(video_path)
        print_video_quality(analysis)
        
        # Дополнительная информация
        print(f"\n📍 Полный путь: {video_path.absolute()}")
        
        # Рекомендации по качеству
        if 'quality_rating' in analysis:
            rating = analysis['quality_rating']
            print(f"\n💡 РЕКОМЕНДАЦИИ:")
            
            if "8K" in rating:
                print("   🏆 Превосходное качество! Идеально для профессиональной работы.")
            elif "4K" in rating:
                print("   💎 Отличное качество! Подходит для создания контента высокого качества.")
            elif "1440p" in rating:
                print("   ⭐ Хорошее качество! Оптимально для большинства задач.")
            elif "Full HD" in rating:
                print("   ✨ Стандартное HD качество. Подходит для веб-контента.")
            elif "HD" in rating:
                print("   📺 Базовое HD качество. Приемлемо для простых задач.")
            else:
                print("   ⚠️ Низкое качество. Рекомендуется перескачать в лучшем качестве.")
        
        # Информация о размере
        if 'file_size' in analysis:
            size_mb = analysis['file_size'] / (1024 * 1024)
            duration = analysis.get('duration', 0)
            
            if duration > 0:
                mb_per_minute = size_mb / (duration / 60)
                print(f"   📊 Размер: {mb_per_minute:.1f} MB на минуту")
                
                if mb_per_minute > 100:
                    print("   💾 Большой размер файла - высокое качество")
                elif mb_per_minute > 50:
                    print("   📦 Средний размер файла - хорошее качество")
                else:
                    print("   📱 Компактный размер файла - подходит для мобильных устройств")
        
    except Exception as e:
        print(f"❌ Ошибка при анализе: {e}")
        return 1
    
    print(f"\n✅ Анализ завершен!")
    return 0

if __name__ == "__main__":
    exit(main()) 