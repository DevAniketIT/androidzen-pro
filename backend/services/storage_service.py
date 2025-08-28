"""
Storage Management Service for AndroidZen Pro

This service provides comprehensive storage analysis and optimization:
- Storage usage analysis via ADB commands
- Cache detection and cleaning recommendations
- Large file detection algorithms
- Storage categorization (apps, media, system, etc.)
- AI-based storage optimization suggestions
- Historical trend analysis
"""

import asyncio
import json
import logging
import re
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any, NamedTuple
from dataclasses import dataclass, field
from pathlib import Path
import statistics

from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_, desc

from .core.adb_manager import AdbManager
from .models.device import Device
from .models.analytics import Analytics, StorageTrend
from .core.database import get_db


class StorageCategory(NamedTuple):
    """Storage category information"""
    name: str
    size_mb: int
    percentage: float
    file_count: int
    path: str
    subcategories: List[Dict[str, Any]] = []


@dataclass
class LargeFile:
    """Large file information"""
    path: str
    size_mb: float
    category: str
    last_accessed: Optional[datetime] = None
    is_cache: bool = False
    is_temp: bool = False
    recommendations: List[str] = field(default_factory=list)


@dataclass
class CacheInfo:
    """Cache information"""
    app_name: str
    package_name: str
    cache_size_mb: float
    cache_path: str
    last_cleared: Optional[datetime] = None
    can_clear: bool = True
    priority: str = "medium"  # low, medium, high


@dataclass
class StorageAnalysis:
    """Comprehensive storage analysis result"""
    total_storage_mb: int
    used_storage_mb: int
    available_storage_mb: int
    usage_percentage: float
    categories: List[StorageCategory]
    large_files: List[LargeFile]
    cache_info: List[CacheInfo]
    recommendations: List[str]
    optimization_potential_mb: int


@dataclass
class StorageOptimization:
    """AI-based storage optimization suggestions"""
    device_id: str
    total_savings_mb: int
    confidence_score: float
    suggestions: List[Dict[str, Any]]
    risk_level: str  # low, medium, high
    execution_time_estimate: int  # minutes


class StorageService:
    """
    Comprehensive storage management service
    """
    
    def __init__(self, adb_manager: AdbManager):
        self.adb_manager = adb_manager
        self.logger = logging.getLogger(__name__)
        
        # Cache patterns for detection
        self.cache_patterns = [
            r".*\/cache\/.*",
            r".*\/\.cache\/.*",
            r".*\/tmp\/.*",
            r".*\/temp\/.*",
            r".*\.tmp$",
            r".*\.cache$",
            r".*\/thumbnails\/.*",
            r".*\/webview.*cache.*",
            r".*\/app_cache\/.*",
        ]
        
        # Temporary file patterns
        self.temp_patterns = [
            r".*\.tmp$",
            r".*\.temp$",
            r".*\/tmp\/.*",
            r".*\/temp\/.*",
            r".*~$",
            r".*\.bak$",
            r".*\.log$",
        ]
        
        # Large file thresholds (MB)
        self.large_file_thresholds = {
            "video": 100,
            "image": 10,
            "audio": 20,
            "document": 50,
            "archive": 100,
            "other": 50
        }
        
        # Storage categories mapping
        self.category_paths = {
            "apps": ["/data/app/", "/system/app/", "/system/priv-app/"],
            "media": ["/sdcard/DCIM/", "/sdcard/Pictures/", "/sdcard/Movies/", 
                     "/sdcard/Music/", "/sdcard/Download/"],
            "system": ["/system/", "/vendor/", "/boot/"],
            "data": ["/data/data/", "/data/user/"],
            "cache": ["/cache/", "/data/cache/"],
            "logs": ["/data/log/", "/cache/log/"]
        }

    async def analyze_storage(self, device_id: str, detailed: bool = True) -> StorageAnalysis:
        """
        Perform comprehensive storage analysis
        
        Args:
            device_id: Target device ID
            detailed: Whether to perform detailed analysis (slower but more thorough)
            
        Returns:
            StorageAnalysis object with complete storage information
        """
        self.logger.info(f"Starting storage analysis for device {device_id}")
        
        try:
            # Get basic storage info
            storage_info = await self._get_storage_info(device_id)
            if not storage_info:
                raise Exception("Failed to get storage information")
            
            # Analyze storage categories
            categories = await self._analyze_storage_categories(device_id, detailed)
            
            # Find large files
            large_files = await self._find_large_files(device_id) if detailed else []
            
            # Analyze cache
            cache_info = await self._analyze_cache(device_id) if detailed else []
            
            # Generate recommendations
            recommendations = self._generate_storage_recommendations(
                storage_info, categories, large_files, cache_info
            )
            
            # Calculate optimization potential
            optimization_potential = sum([
                sum(cache.cache_size_mb for cache in cache_info),
                sum(f.size_mb for f in large_files if f.is_temp or f.is_cache)
            ])
            
            analysis = StorageAnalysis(
                total_storage_mb=storage_info["total"],
                used_storage_mb=storage_info["used"],
                available_storage_mb=storage_info["available"],
                usage_percentage=storage_info["usage_percentage"],
                categories=categories,
                large_files=large_files,
                cache_info=cache_info,
                recommendations=recommendations,
                optimization_potential_mb=int(optimization_potential)
            )
            
            self.logger.info(f"Storage analysis completed for device {device_id}")
            return analysis
            
        except Exception as e:
            self.logger.error(f"Storage analysis failed for device {device_id}: {e}")
            raise

    async def _get_storage_info(self, device_id: str) -> Optional[Dict[str, Any]]:
        """Get basic storage information using ADB commands"""
        try:
            # Get storage info using df command
            result = await self.adb_manager.execute_command(device_id, "df -h /data")
            if not result.success:
                # Fallback to alternative command
                result = await self.adb_manager.execute_command(device_id, "df /data")
            
            if not result.success:
                self.logger.error(f"Failed to get storage info: {result.error}")
                return None
            
            # Parse df output
            lines = result.output.strip().split('\n')
            if len(lines) < 2:
                return None
            
            data_line = lines[1].split()
            if len(data_line) < 6:
                return None
            
            # Parse sizes (handle both human readable and byte formats)
            def parse_size(size_str: str) -> int:
                """Convert size string to MB"""
                if size_str.endswith('K'):
                    return int(float(size_str[:-1]) / 1024)
                elif size_str.endswith('M'):
                    return int(float(size_str[:-1]))
                elif size_str.endswith('G'):
                    return int(float(size_str[:-1]) * 1024)
                elif size_str.endswith('T'):
                    return int(float(size_str[:-1]) * 1024 * 1024)
                else:
                    # Assume bytes
                    return int(int(size_str) / (1024 * 1024))
            
            total_mb = parse_size(data_line[1])
            used_mb = parse_size(data_line[2])
            available_mb = parse_size(data_line[3])
            usage_percentage = (used_mb / total_mb * 100) if total_mb > 0 else 0
            
            return {
                "total": total_mb,
                "used": used_mb,
                "available": available_mb,
                "usage_percentage": round(usage_percentage, 2)
            }
            
        except Exception as e:
            self.logger.error(f"Error getting storage info: {e}")
            return None

    async def _analyze_storage_categories(self, device_id: str, detailed: bool = True) -> List[StorageCategory]:
        """Analyze storage usage by categories"""
        categories = []
        
        try:
            total_size = 0
            
            for category, paths in self.category_paths.items():
                category_size = 0
                file_count = 0
                subcategories = []
                
                for path in paths:
                    try:
                        # Check if path exists
                        check_result = await self.adb_manager.execute_command(
                            device_id, f"test -d '{path}' && echo 'exists'"
                        )
                        
                        if not check_result.success or 'exists' not in check_result.output:
                            continue
                        
                        # Get directory size and file count
                        if detailed:
                            du_result = await self.adb_manager.execute_command(
                                device_id, f"du -sm '{path}' 2>/dev/null || echo '0'"
                            )
                            if du_result.success and du_result.output:
                                size_line = du_result.output.strip().split('\n')[0]
                                try:
                                    path_size = int(size_line.split()[0])
                                    category_size += path_size
                                except (ValueError, IndexError):
                                    pass
                            
                            # Count files
                            count_result = await self.adb_manager.execute_command(
                                device_id, f"find '{path}' -type f 2>/dev/null | wc -l"
                            )
                            if count_result.success:
                                try:
                                    file_count += int(count_result.output.strip())
                                except ValueError:
                                    pass
                            
                            # Get subcategory breakdown for detailed analysis
                            if category_size > 100:  # Only for categories > 100MB
                                subcat_result = await self.adb_manager.execute_command(
                                    device_id, f"du -sm '{path}'/* 2>/dev/null | head -10"
                                )
                                if subcat_result.success:
                                    for line in subcat_result.output.strip().split('\n'):
                                        if line.strip():
                                            try:
                                                parts = line.split('\t', 1)
                                                sub_size = int(parts[0])
                                                sub_path = parts[1] if len(parts) > 1 else "unknown"
                                                if sub_size > 10:  # Only include subcategories > 10MB
                                                    subcategories.append({
                                                        "name": Path(sub_path).name,
                                                        "path": sub_path,
                                                        "size_mb": sub_size,
                                                        "percentage": (sub_size / category_size * 100) if category_size > 0 else 0
                                                    })
                                            except (ValueError, IndexError):
                                                continue
                        else:
                            # Quick estimation for non-detailed mode
                            category_size += await self._estimate_directory_size(device_id, path)
                    except Exception as e:
                        self.logger.debug(f"Error analyzing path {path}: {e}")
                        continue

                total_size += category_size
                
                if category_size > 0:  # Only include categories with actual content
                    categories.append(StorageCategory(
                        name=category,
                        size_mb=category_size,
                        percentage=0,  # Will be calculated after getting total
                        file_count=file_count,
                        path=paths[0] if paths else "",
                        subcategories=subcategories[:5]  # Top 5 subcategories
                    ))
            
            # Calculate percentages
            for category in categories:
                category = category._replace(
                    percentage=round((category.size_mb / total_size * 100) if total_size > 0 else 0, 2)
                )
            
            # Sort by size
            categories.sort(key=lambda x: x.size_mb, reverse=True)
            
            return categories
            
        except Exception as e:
            self.logger.error(f"Error analyzing storage categories: {e}")
            return []

    async def _estimate_directory_size(self, device_id: str, path: str) -> int:
        """Estimate directory size quickly (less accurate but faster)"""
        try:
            result = await self.adb_manager.execute_command(
                device_id, f"du -s '{path}' 2>/dev/null || echo '0'"
            )
            if result.success and result.output:
                try:
                    # Convert KB to MB
                    kb_size = int(result.output.strip().split()[0])
                    return max(1, kb_size // 1024)
                except (ValueError, IndexError):
                    pass
            return 0
        except:
            return 0

    async def _find_large_files(self, device_id: str, min_size_mb: int = 50) -> List[LargeFile]:
        """Find large files on the device"""
        large_files = []
        
        try:
            # Search for large files in common directories
            search_paths = ["/sdcard/", "/data/data/", "/storage/"]
            
            for search_path in search_paths:
                try:
                    # Check if path exists
                    check_result = await self.adb_manager.execute_command(
                        device_id, f"test -d '{search_path}' && echo 'exists'"
                    )
                    
                    if not check_result.success or 'exists' not in check_result.output:
                        continue
                    
                    # Find large files
                    find_result = await self.adb_manager.execute_command(
                        device_id, 
                        f"find '{search_path}' -type f -size +{min_size_mb}M 2>/dev/null | head -50",
                        timeout=60
                    )
                    
                    if not find_result.success:
                        continue
                    
                    for file_path in find_result.output.strip().split('\n'):
                        if not file_path.strip():
                            continue
                        
                        # Get file size and details
                        file_info = await self._get_file_info(device_id, file_path)
                        if file_info:
                            large_files.append(file_info)
                            
                except Exception as e:
                    self.logger.debug(f"Error searching in {search_path}: {e}")
                    continue
            
            # Sort by size (largest first)
            large_files.sort(key=lambda x: x.size_mb, reverse=True)
            
            # Limit to top 100 files to avoid overwhelming results
            return large_files[:100]
            
        except Exception as e:
            self.logger.error(f"Error finding large files: {e}")
            return []

    async def _get_file_info(self, device_id: str, file_path: str) -> Optional[LargeFile]:
        """Get detailed information about a file"""
        try:
            # Get file stats
            stat_result = await self.adb_manager.execute_command(
                device_id, f"stat '{file_path}' 2>/dev/null"
            )
            
            if not stat_result.success:
                # Fallback to ls
                stat_result = await self.adb_manager.execute_command(
                    device_id, f"ls -la '{file_path}' 2>/dev/null"
                )
            
            if not stat_result.success:
                return None
            
            # Parse file size
            size_mb = self._parse_file_size(stat_result.output)
            if size_mb < 1:
                return None
            
            # Determine category
            category = self._categorize_file(file_path)
            
            # Check if it's cache or temp
            is_cache = any(re.match(pattern, file_path, re.IGNORECASE) for pattern in self.cache_patterns)
            is_temp = any(re.match(pattern, file_path, re.IGNORECASE) for pattern in self.temp_patterns)
            
            # Generate recommendations
            recommendations = self._generate_file_recommendations(file_path, size_mb, category, is_cache, is_temp)
            
            return LargeFile(
                path=file_path,
                size_mb=size_mb,
                category=category,
                is_cache=is_cache,
                is_temp=is_temp,
                recommendations=recommendations
            )
            
        except Exception as e:
            self.logger.debug(f"Error getting file info for {file_path}: {e}")
            return None

    def _parse_file_size(self, stat_output: str) -> float:
        """Parse file size from stat or ls output"""
        try:
            lines = stat_output.strip().split('\n')
            for line in lines:
                # Look for Size: line in stat output
                if 'Size:' in line:
                    size_match = re.search(r'Size:\s*(\d+)', line)
                    if size_match:
                        bytes_size = int(size_match.group(1))
                        return bytes_size / (1024 * 1024)  # Convert to MB
                
                # Parse ls -la output
                elif line.strip() and not line.startswith('total'):
                    parts = line.split()
                    if len(parts) >= 5:
                        try:
                            bytes_size = int(parts[4])
                            return bytes_size / (1024 * 1024)  # Convert to MB
                        except (ValueError, IndexError):
                            continue
            
            return 0.0
        except:
            return 0.0

    def _categorize_file(self, file_path: str) -> str:
        """Categorize file based on path and extension"""
        path_lower = file_path.lower()
        
        # Video files
        if any(ext in path_lower for ext in ['.mp4', '.avi', '.mkv', '.mov', '.wmv', '.flv']):
            return 'video'
        
        # Audio files
        elif any(ext in path_lower for ext in ['.mp3', '.wav', '.flac', '.aac', '.m4a']):
            return 'audio'
        
        # Image files
        elif any(ext in path_lower for ext in ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp']):
            return 'image'
        
        # Archives
        elif any(ext in path_lower for ext in ['.zip', '.rar', '.7z', '.tar', '.gz']):
            return 'archive'
        
        # Documents
        elif any(ext in path_lower for ext in ['.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt']):
            return 'document'
        
        # Applications
        elif '.apk' in path_lower:
            return 'application'
        
        # Databases
        elif any(ext in path_lower for ext in ['.db', '.sqlite', '.sql']):
            return 'database'
        
        else:
            return 'other'

    def _generate_file_recommendations(self, file_path: str, size_mb: float, category: str, 
                                     is_cache: bool, is_temp: bool) -> List[str]:
        """Generate recommendations for a large file"""
        recommendations = []
        
        if is_temp:
            recommendations.append("This appears to be a temporary file that can likely be safely deleted")
        
        if is_cache:
            recommendations.append("This is a cache file that can be cleared to free up space")
        
        if category == 'video' and size_mb > 500:
            recommendations.append("Consider moving large videos to external storage or cloud")
        
        elif category == 'image' and size_mb > 50:
            recommendations.append("Consider compressing images or moving to cloud storage")
        
        elif category == 'archive' and size_mb > 100:
            recommendations.append("Check if this archive is still needed or can be moved to external storage")
        
        elif category == 'application' and 'cache' not in file_path.lower():
            recommendations.append("Consider if this APK file is still needed")
        
        elif category == 'database' and size_mb > 100:
            recommendations.append("Large database file - check if cleanup or archiving is possible")
        
        if not recommendations:
            recommendations.append("Large file detected - review if still needed")
        
        return recommendations

    async def _analyze_cache(self, device_id: str) -> List[CacheInfo]:
        """Analyze cache usage by applications"""
        cache_info = []
        
        try:
            # Get list of installed packages
            packages_result = await self.adb_manager.execute_command(
                device_id, "pm list packages -3"  # User-installed packages only
            )
            
            if not packages_result.success:
                return []
            
            packages = []
            for line in packages_result.output.strip().split('\n'):
                if line.startswith('package:'):
                    packages.append(line.replace('package:', '').strip())
            
            # Analyze cache for each package (limit to top 20 to avoid timeout)
            for package in packages[:20]:
                cache_data = await self._get_package_cache_info(device_id, package)
                if cache_data and cache_data.cache_size_mb > 1:  # Only include caches > 1MB
                    cache_info.append(cache_data)
            
            # Sort by cache size
            cache_info.sort(key=lambda x: x.cache_size_mb, reverse=True)
            
            return cache_info[:50]  # Return top 50
            
        except Exception as e:
            self.logger.error(f"Error analyzing cache: {e}")
            return []

    async def _get_package_cache_info(self, device_id: str, package_name: str) -> Optional[CacheInfo]:
        """Get cache information for a specific package"""
        try:
            # Get package info
            package_info_result = await self.adb_manager.execute_command(
                device_id, f"dumpsys package {package_name} | grep -E '(applicationInfo|dataDir)'"
            )
            
            # Get app name
            app_name_result = await self.adb_manager.execute_command(
                device_id, f"dumpsys package {package_name} | grep -E 'versionName|name='"
            )
            
            app_name = package_name  # Fallback to package name
            if app_name_result.success:
                for line in app_name_result.output.split('\n'):
                    if 'name=' in line and package_name in line:
                        # Try to extract a more readable name
                        name_match = re.search(r'name=([^,\s]+)', line)
                        if name_match:
                            app_name = name_match.group(1)
                        break
            
            # Get cache directory size
            cache_paths = [
                f"/data/data/{package_name}/cache",
                f"/data/data/{package_name}/app_cache",
                f"/data/data/{package_name}/files/cache"
            ]
            
            total_cache_size = 0
            cache_path = ""
            
            for path in cache_paths:
                cache_result = await self.adb_manager.execute_command(
                    device_id, f"du -sm '{path}' 2>/dev/null || echo '0 {path}'"
                )
                
                if cache_result.success and cache_result.output.strip():
                    try:
                        size_str = cache_result.output.strip().split()[0]
                        size = int(size_str)
                        if size > 0:
                            total_cache_size += size
                            if not cache_path:
                                cache_path = path
                    except (ValueError, IndexError):
                        continue
            
            if total_cache_size == 0:
                return None
            
            # Determine priority based on cache size
            if total_cache_size > 100:
                priority = "high"
            elif total_cache_size > 20:
                priority = "medium"
            else:
                priority = "low"
            
            return CacheInfo(
                app_name=app_name,
                package_name=package_name,
                cache_size_mb=total_cache_size,
                cache_path=cache_path,
                can_clear=True,
                priority=priority
            )
            
        except Exception as e:
            self.logger.debug(f"Error getting cache info for {package_name}: {e}")
            return None

    def _generate_storage_recommendations(self, storage_info: Dict[str, Any], 
                                        categories: List[StorageCategory],
                                        large_files: List[LargeFile],
                                        cache_info: List[CacheInfo]) -> List[str]:
        """Generate storage optimization recommendations"""
        recommendations = []
        usage_percentage = storage_info.get("usage_percentage", 0)
        
        # Critical storage warnings
        if usage_percentage > 95:
            recommendations.append("🚨 CRITICAL: Storage is nearly full! Immediate action required.")
            recommendations.append("🔧 Clear app caches and remove unnecessary files immediately")
        elif usage_percentage > 90:
            recommendations.append("⚠️ WARNING: Storage usage is very high (>90%)")
            recommendations.append("🧹 Perform storage cleanup to prevent performance issues")
        elif usage_percentage > 80:
            recommendations.append("📊 Storage usage is high - consider cleanup")
        
        # Cache recommendations
        total_cache_mb = sum(cache.cache_size_mb for cache in cache_info)
        if total_cache_mb > 500:
            recommendations.append(f"🗑️ Clear app caches to free up ~{total_cache_mb:.0f}MB")
        
        high_priority_caches = [c for c in cache_info if c.priority == "high"]
        if high_priority_caches:
            top_cache = high_priority_caches[0]
            recommendations.append(f"🎯 Clear {top_cache.app_name} cache ({top_cache.cache_size_mb:.0f}MB)")
        
        # Large file recommendations
        temp_files_size = sum(f.size_mb for f in large_files if f.is_temp)
        if temp_files_size > 100:
            recommendations.append(f"🗂️ Remove temporary files to free up ~{temp_files_size:.0f}MB")
        
        # Category-specific recommendations
        for category in categories:
            if category.name == "media" and category.size_mb > 5000:  # >5GB
                recommendations.append(f"📱 Media files are using {category.size_mb//1024:.1f}GB - consider cloud backup")
            elif category.name == "cache" and category.size_mb > 1000:  # >1GB
                recommendations.append(f"🧹 System cache is large ({category.size_mb//1024:.1f}GB) - safe to clear")
            elif category.name == "logs" and category.size_mb > 500:  # >500MB
                recommendations.append(f"📝 Log files are using {category.size_mb}MB - can be cleared")
        
        # General recommendations
        if not recommendations:
            recommendations.append("✅ Storage usage looks healthy")
            if total_cache_mb > 50:
                recommendations.append("💡 You can still free up some space by clearing app caches")
        
        return recommendations

    async def generate_ai_optimization_suggestions(self, device_id: str, 
                                                 db: Session) -> StorageOptimization:
        """Generate AI-based storage optimization suggestions"""
        try:
            # Get storage analysis
            analysis = await self.analyze_storage(device_id, detailed=True)
            
            # Get historical data for trend analysis
            trends = await self._get_storage_trends(device_id, db, days=30)
            
            # Calculate optimization suggestions
            suggestions = []
            total_savings = 0
            confidence_scores = []
            
            # Cache cleaning suggestions
            if analysis.cache_info:
                cache_suggestion = self._generate_cache_optimization(analysis.cache_info)
                if cache_suggestion:
                    suggestions.append(cache_suggestion)
                    total_savings += cache_suggestion.get("potential_savings_mb", 0)
                    confidence_scores.append(cache_suggestion.get("confidence", 0.8))
            
            # Large file optimization
            if analysis.large_files:
                file_suggestion = self._generate_file_optimization(analysis.large_files)
                if file_suggestion:
                    suggestions.append(file_suggestion)
                    total_savings += file_suggestion.get("potential_savings_mb", 0)
                    confidence_scores.append(file_suggestion.get("confidence", 0.7))
            
            # Trend-based suggestions
            if trends:
                trend_suggestion = self._generate_trend_optimization(trends, analysis)
                if trend_suggestion:
                    suggestions.append(trend_suggestion)
                    confidence_scores.append(trend_suggestion.get("confidence", 0.6))
            
            # Category-specific suggestions
            category_suggestion = self._generate_category_optimization(analysis.categories)
            if category_suggestion:
                suggestions.append(category_suggestion)
                total_savings += category_suggestion.get("potential_savings_mb", 0)
                confidence_scores.append(category_suggestion.get("confidence", 0.7))
            
            # Calculate overall confidence and risk
            overall_confidence = statistics.mean(confidence_scores) if confidence_scores else 0.5
            risk_level = self._calculate_risk_level(suggestions, analysis)
            execution_time = self._estimate_execution_time(suggestions)
            
            return StorageOptimization(
                device_id=device_id,
                total_savings_mb=total_savings,
                confidence_score=round(overall_confidence, 2),
                suggestions=suggestions,
                risk_level=risk_level,
                execution_time_estimate=execution_time
            )
            
        except Exception as e:
            self.logger.error(f"Error generating AI optimization suggestions: {e}")
            return StorageOptimization(
                device_id=device_id,
                total_savings_mb=0,
                confidence_score=0.0,
                suggestions=[],
                risk_level="unknown",
                execution_time_estimate=0
            )

    def _generate_cache_optimization(self, cache_info: List[CacheInfo]) -> Optional[Dict[str, Any]]:
        """Generate cache optimization suggestions"""
        if not cache_info:
            return None
        
        # Sort by priority and size
        high_priority = [c for c in cache_info if c.priority == "high"]
        medium_priority = [c for c in cache_info if c.priority == "medium"]
        
        total_savings = sum(c.cache_size_mb for c in cache_info)
        safe_to_clear = [c for c in cache_info if c.can_clear]
        
        return {
            "type": "cache_cleanup",
            "title": "App Cache Optimization",
            "description": f"Clear app caches to free up {total_savings:.0f}MB of storage",
            "potential_savings_mb": int(total_savings),
            "confidence": 0.9,  # High confidence for cache clearing
            "risk_level": "low",
            "actions": [
                {
                    "action": "clear_cache",
                    "target": c.package_name,
                    "app_name": c.app_name,
                    "size_mb": c.cache_size_mb,
                    "priority": c.priority
                }
                for c in safe_to_clear[:10]  # Top 10 caches
            ],
            "estimated_time_minutes": len(safe_to_clear) * 0.5  # 30 seconds per app
        }

    def _generate_file_optimization(self, large_files: List[LargeFile]) -> Optional[Dict[str, Any]]:
        """Generate large file optimization suggestions"""
        if not large_files:
            return None
        
        # Categorize files by type and safety
        temp_files = [f for f in large_files if f.is_temp]
        cache_files = [f for f in large_files if f.is_cache]
        old_media = [f for f in large_files if f.category in ['video', 'image'] and f.size_mb > 100]
        
        suggestions = []
        total_savings = 0
        
        if temp_files:
            temp_savings = sum(f.size_mb for f in temp_files)
            total_savings += temp_savings
            suggestions.append({
                "action": "delete_temp_files",
                "description": f"Delete temporary files ({len(temp_files)} files, {temp_savings:.0f}MB)",
                "files": [{"path": f.path, "size_mb": f.size_mb} for f in temp_files[:5]],
                "risk": "low"
            })
        
        if cache_files:
            cache_savings = sum(f.size_mb for f in cache_files)
            total_savings += cache_savings
            suggestions.append({
                "action": "delete_cache_files",
                "description": f"Delete cache files ({len(cache_files)} files, {cache_savings:.0f}MB)",
                "files": [{"path": f.path, "size_mb": f.size_mb} for f in cache_files[:5]],
                "risk": "low"
            })
        
        if old_media:
            suggestions.append({
                "action": "review_media",
                "description": f"Review large media files ({len(old_media)} files)",
                "files": [{"path": f.path, "size_mb": f.size_mb, "category": f.category} for f in old_media[:5]],
                "risk": "medium"
            })
        
        if not suggestions:
            return None
        
        return {
            "type": "file_cleanup",
            "title": "Large File Optimization",
            "description": f"Optimize large files to free up space",
            "potential_savings_mb": int(total_savings),
            "confidence": 0.75,
            "risk_level": "medium",
            "actions": suggestions,
            "estimated_time_minutes": len(suggestions) * 2
        }

    def _generate_trend_optimization(self, trends: List[Dict], analysis: StorageAnalysis) -> Optional[Dict[str, Any]]:
        """Generate trend-based optimization suggestions"""
        if not trends:
            return None
        
        # Analyze growth trends
        recent_trends = trends[-7:]  # Last week
        if len(recent_trends) < 3:
            return None
        
        growth_rates = [t.get("growth_rate", 0) for t in recent_trends if t.get("growth_rate")]
        if not growth_rates:
            return None
        
        avg_growth_rate = statistics.mean(growth_rates)
        
        if avg_growth_rate > 2:  # Growing > 2% per day
            days_until_full = (100 - analysis.usage_percentage) / avg_growth_rate
            
            return {
                "type": "trend_prediction",
                "title": "Storage Growth Alert",
                "description": f"Storage is growing at {avg_growth_rate:.1f}% per day",
                "confidence": 0.6,
                "risk_level": "medium",
                "predictions": {
                    "days_until_full": int(days_until_full),
                    "recommended_action": "proactive_cleanup" if days_until_full < 30 else "monitor",
                    "growth_rate_daily": avg_growth_rate
                },
                "estimated_time_minutes": 0  # No immediate action required
            }
        
        return None

    def _generate_category_optimization(self, categories: List[StorageCategory]) -> Optional[Dict[str, Any]]:
        """Generate category-specific optimization suggestions"""
        if not categories:
            return None
        
        suggestions = []
        total_savings = 0
        
        for category in categories:
            if category.name == "logs" and category.size_mb > 100:
                total_savings += category.size_mb * 0.8  # Can safely clear 80% of logs
                suggestions.append({
                    "category": category.name,
                    "action": "clear_logs",
                    "potential_savings": int(category.size_mb * 0.8),
                    "description": f"Clear system logs ({category.size_mb}MB total)"
                })
            
            elif category.name == "cache" and category.size_mb > 200:
                total_savings += category.size_mb * 0.9  # Can safely clear 90% of cache
                suggestions.append({
                    "category": category.name,
                    "action": "clear_system_cache",
                    "potential_savings": int(category.size_mb * 0.9),
                    "description": f"Clear system cache ({category.size_mb}MB total)"
                })
        
        if not suggestions:
            return None
        
        return {
            "type": "category_optimization",
            "title": "System Cleanup",
            "description": "Optimize system categories for better storage efficiency",
            "potential_savings_mb": int(total_savings),
            "confidence": 0.8,
            "risk_level": "low",
            "actions": suggestions,
            "estimated_time_minutes": len(suggestions) * 1
        }

    def _calculate_risk_level(self, suggestions: List[Dict], analysis: StorageAnalysis) -> str:
        """Calculate overall risk level for optimization suggestions"""
        risk_scores = []
        
        for suggestion in suggestions:
            if suggestion.get("risk_level") == "low":
                risk_scores.append(1)
            elif suggestion.get("risk_level") == "medium":
                risk_scores.append(2)
            elif suggestion.get("risk_level") == "high":
                risk_scores.append(3)
        
        if not risk_scores:
            return "unknown"
        
        avg_risk = statistics.mean(risk_scores)
        
        if avg_risk <= 1.5:
            return "low"
        elif avg_risk <= 2.5:
            return "medium"
        else:
            return "high"

    def _estimate_execution_time(self, suggestions: List[Dict]) -> int:
        """Estimate total execution time for all suggestions"""
        total_time = 0
        
        for suggestion in suggestions:
            total_time += suggestion.get("estimated_time_minutes", 5)
        
        return total_time

    async def _get_storage_trends(self, device_id: str, db: Session, days: int = 30) -> List[Dict]:
        """Get storage trends from database"""
        try:
            # Get device from database
            device = db.query(Device).filter(Device.device_id == device_id).first()
            if not device:
                return []
            
            # Get trends from last N days
            start_date = datetime.utcnow() - timedelta(days=days)
            
            trends = (db.query(StorageTrend)
                     .filter(StorageTrend.device_id == device.id)
                     .filter(StorageTrend.period_start >= start_date)
                     .order_by(StorageTrend.period_start)
                     .all())
            
            return [trend.to_dict() for trend in trends]
            
        except Exception as e:
            self.logger.error(f"Error getting storage trends: {e}")
            return []

    async def clear_cache(self, device_id: str, package_names: List[str] = None, 
                         cache_types: List[str] = None) -> Dict[str, Any]:
        """
        Clear cache for specified packages or types
        
        Args:
            device_id: Target device ID
            package_names: List of package names to clear cache for
            cache_types: Types of cache to clear ('app', 'system', 'all')
            
        Returns:
            Dictionary with cleanup results
        """
        results = {
            "success": True,
            "cleared_packages": [],
            "space_freed_mb": 0,
            "errors": []
        }
        
        try:
            if package_names:
                # Clear cache for specific packages
                for package in package_names:
                    try:
                        # Clear app cache
                        result = await self.adb_manager.execute_command(
                            device_id, f"pm clear {package}"
                        )
                        
                        if result.success:
                            results["cleared_packages"].append(package)
                        else:
                            results["errors"].append(f"Failed to clear cache for {package}: {result.error}")
                    
                    except Exception as e:
                        results["errors"].append(f"Error clearing cache for {package}: {e}")
            
            if cache_types:
                # Clear system cache types
                for cache_type in cache_types:
                    if cache_type == "system" or cache_type == "all":
                        # Clear system cache
                        try:
                            system_result = await self.adb_manager.execute_command(
                                device_id, "rm -rf /cache/* 2>/dev/null; rm -rf /data/cache/* 2>/dev/null"
                            )
                            results["space_freed_mb"] += 50  # Estimate
                        except Exception as e:
                            results["errors"].append(f"Error clearing system cache: {e}")
            
            return results
            
        except Exception as e:
            self.logger.error(f"Cache clearing failed: {e}")
            results["success"] = False
            results["errors"].append(str(e))
            return results

    async def get_storage_breakdown(self, device_id: str) -> Dict[str, Any]:
        """Get visual storage breakdown data for API endpoints"""
        try:
            analysis = await self.analyze_storage(device_id, detailed=False)
            
            # Prepare data for visualization
            breakdown = {
                "total_storage_mb": analysis.total_storage_mb,
                "used_storage_mb": analysis.used_storage_mb,
                "available_storage_mb": analysis.available_storage_mb,
                "usage_percentage": analysis.usage_percentage,
                "categories": [
                    {
                        "name": cat.name,
                        "size_mb": cat.size_mb,
                        "percentage": cat.percentage,
                        "file_count": cat.file_count
                    }
                    for cat in analysis.categories
                ],
                "optimization_potential_mb": analysis.optimization_potential_mb,
                "recommendations": analysis.recommendations[:5],  # Top 5 recommendations
                "last_updated": datetime.utcnow().isoformat()
            }
            
            return breakdown
            
        except Exception as e:
            self.logger.error(f"Error getting storage breakdown: {e}")
            raise

    async def save_storage_analysis(self, device_id: str, analysis: StorageAnalysis, db: Session):
        """Save storage analysis results to database"""
        try:
            # Get device from database
            device = db.query(Device).filter(Device.device_id == device_id).first()
            if not device:
                raise Exception(f"Device {device_id} not found in database")
            
            # Create analytics record
            analytics = Analytics(
                device_id=device.id,
                metric_type="storage",
                storage_total=analysis.total_storage_mb,
                storage_used=analysis.used_storage_mb,
                storage_available=analysis.available_storage_mb,
                storage_usage_percentage=analysis.usage_percentage,
                additional_metrics={
                    "categories": [
                        {
                            "name": cat.name,
                            "size_mb": cat.size_mb,
                            "percentage": cat.percentage,
                            "file_count": cat.file_count
                        }
                        for cat in analysis.categories
                    ],
                    "large_files_count": len(analysis.large_files),
                    "cache_apps_count": len(analysis.cache_info),
                    "optimization_potential_mb": analysis.optimization_potential_mb,
                    "recommendations": analysis.recommendations
                },
                collection_method="adb",
                data_source="storage_service"
            )
            
            db.add(analytics)
            db.commit()
            db.refresh(analytics)
            
            self.logger.info(f"Saved storage analysis for device {device_id}")
            return analytics.id
            
        except Exception as e:
            self.logger.error(f"Error saving storage analysis: {e}")
            db.rollback()
            raise

