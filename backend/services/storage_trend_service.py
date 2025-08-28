"""
Storage Trend Analysis Service for AndroidZen Pro

This service handles:
- Historical storage data processing
- Trend calculation and analysis
- Growth rate predictions
- Storage forecasting
- Anomaly detection in storage patterns
"""

import asyncio
import logging
import statistics
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
import math

from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_, desc, asc

from .models.device import Device
from .models.analytics import Analytics, StorageTrend
from .core.database import get_db


@dataclass
class TrendAnalysis:
    """Storage trend analysis result"""
    device_id: str
    period_type: str
    trend_direction: str  # "increasing", "decreasing", "stable"
    growth_rate: float  # Percentage change per period
    confidence_level: float  # 0-1
    predicted_full_date: Optional[datetime]
    anomalies: List[Dict[str, Any]]
    recommendations: List[str]


class StorageTrendService:
    """
    Service for analyzing storage trends and generating predictions
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # Trend analysis parameters
        self.min_data_points = 3
        self.anomaly_threshold = 2.0  # Standard deviations
        self.stable_threshold = 0.5  # % per period
        
    async def calculate_storage_trends(self, device_id: str, db: Session, 
                                     period_type: str = "daily", 
                                     days_back: int = 30) -> Optional[TrendAnalysis]:
        """
        Calculate storage trends for a device over a specified period
        
        Args:
            device_id: Target device ID
            db: Database session
            period_type: Type of period ("hourly", "daily", "weekly", "monthly")
            days_back: Number of days to analyze
            
        Returns:
            TrendAnalysis object or None if insufficient data
        """
        try:
            # Get device from database
            device = db.query(Device).filter(Device.device_id == device_id).first()
            if not device:
                self.logger.error(f"Device {device_id} not found")
                return None
            
            # Get historical storage data
            storage_data = await self._get_historical_storage_data(
                device.id, db, period_type, days_back
            )
            
            if len(storage_data) < self.min_data_points:
                self.logger.warning(f"Insufficient data points for trend analysis: {len(storage_data)}")
                return None
            
            # Calculate trend metrics
            trend_direction, growth_rate, confidence = self._calculate_trend_metrics(storage_data)
            
            # Predict when storage might be full
            predicted_full_date = self._predict_full_date(storage_data, growth_rate)
            
            # Detect anomalies
            anomalies = self._detect_anomalies(storage_data)
            
            # Generate recommendations
            recommendations = self._generate_trend_recommendations(
                growth_rate, predicted_full_date, anomalies
            )
            
            return TrendAnalysis(
                device_id=device_id,
                period_type=period_type,
                trend_direction=trend_direction,
                growth_rate=growth_rate,
                confidence_level=confidence,
                predicted_full_date=predicted_full_date,
                anomalies=anomalies,
                recommendations=recommendations
            )
            
        except Exception as e:
            self.logger.error(f"Error calculating storage trends for device {device_id}: {e}")
            return None

    async def _get_historical_storage_data(self, device_db_id: int, db: Session,
                                         period_type: str, days_back: int) -> List[Dict[str, Any]]:
        """Get historical storage data from analytics table"""
        try:
            end_date = datetime.utcnow()
            start_date = end_date - timedelta(days=days_back)
            
            # Query analytics data
            analytics_query = (
                db.query(Analytics)
                .filter(Analytics.device_id == device_db_id)
                .filter(Analytics.metric_type == "storage")
                .filter(Analytics.storage_usage_percentage.is_not(None))
                .filter(Analytics.recorded_at >= start_date)
                .order_by(Analytics.recorded_at.asc())
            )
            
            raw_data = analytics_query.all()
            
            if not raw_data:
                return []
            
            # Group data by period
            grouped_data = self._group_data_by_period(raw_data, period_type)
            
            return grouped_data
            
        except Exception as e:
            self.logger.error(f"Error getting historical storage data: {e}")
            return []

    def _group_data_by_period(self, raw_data: List[Analytics], 
                            period_type: str) -> List[Dict[str, Any]]:
        """Group raw analytics data by time periods"""
        grouped = {}
        
        for record in raw_data:
            # Determine period key based on period_type
            if period_type == "hourly":
                period_key = record.recorded_at.replace(minute=0, second=0, microsecond=0)
            elif period_type == "daily":
                period_key = record.recorded_at.replace(hour=0, minute=0, second=0, microsecond=0)
            elif period_type == "weekly":
                # Group by week (Monday as start)
                days_since_monday = record.recorded_at.weekday()
                week_start = record.recorded_at - timedelta(days=days_since_monday)
                period_key = week_start.replace(hour=0, minute=0, second=0, microsecond=0)
            elif period_type == "monthly":
                period_key = record.recorded_at.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            else:
                period_key = record.recorded_at.replace(hour=0, minute=0, second=0, microsecond=0)
            
            if period_key not in grouped:
                grouped[period_key] = []
            
            grouped[period_key].append({
                'usage_percentage': record.storage_usage_percentage,
                'used_mb': record.storage_used,
                'total_mb': record.storage_total,
                'timestamp': record.recorded_at
            })
        
        # Calculate aggregates for each period
        result = []
        for period_start, records in sorted(grouped.items()):
            usage_values = [r['usage_percentage'] for r in records if r['usage_percentage'] is not None]
            used_values = [r['used_mb'] for r in records if r['used_mb'] is not None]
            
            if not usage_values:
                continue
            
            result.append({
                'period_start': period_start,
                'avg_usage_percentage': statistics.mean(usage_values),
                'max_usage_percentage': max(usage_values),
                'min_usage_percentage': min(usage_values),
                'avg_used_mb': statistics.mean(used_values) if used_values else None,
                'data_points': len(records),
                'raw_records': records
            })
        
        return result

    def _calculate_trend_metrics(self, storage_data: List[Dict[str, Any]]) -> Tuple[str, float, float]:
        """Calculate trend direction, growth rate, and confidence level"""
        try:
            if len(storage_data) < 2:
                return "stable", 0.0, 0.0
            
            # Extract usage percentages over time
            usage_values = [d['avg_usage_percentage'] for d in storage_data]
            
            # Calculate linear regression for trend
            n = len(usage_values)
            x_values = list(range(n))
            
            # Linear regression: y = mx + b
            x_mean = statistics.mean(x_values)
            y_mean = statistics.mean(usage_values)
            
            numerator = sum((x - x_mean) * (y - y_mean) for x, y in zip(x_values, usage_values))
            denominator = sum((x - x_mean) ** 2 for x in x_values)
            
            if denominator == 0:
                slope = 0
            else:
                slope = numerator / denominator
            
            # Calculate correlation coefficient for confidence
            if len(usage_values) > 1:
                try:
                    correlation = statistics.correlation(x_values, usage_values)
                    confidence = abs(correlation)
                except:
                    confidence = 0.5
            else:
                confidence = 0.5
            
            # Convert slope to growth rate percentage per period
            growth_rate = slope
            
            # Determine trend direction
            if abs(growth_rate) <= self.stable_threshold:
                trend_direction = "stable"
            elif growth_rate > 0:
                trend_direction = "increasing"
            else:
                trend_direction = "decreasing"
            
            return trend_direction, growth_rate, min(1.0, confidence)
            
        except Exception as e:
            self.logger.error(f"Error calculating trend metrics: {e}")
            return "stable", 0.0, 0.0

    def _predict_full_date(self, storage_data: List[Dict[str, Any]], 
                         growth_rate: float) -> Optional[datetime]:
        """Predict when storage might be full based on current trend"""
        try:
            if not storage_data or growth_rate <= 0:
                return None
            
            # Get the latest usage percentage
            latest_data = storage_data[-1]
            current_usage = latest_data['avg_usage_percentage']
            current_date = latest_data['period_start']
            
            if current_usage >= 100:
                return current_date
            
            # Calculate periods until full (assuming linear growth)
            remaining_percentage = 100 - current_usage
            periods_until_full = remaining_percentage / growth_rate
            
            if periods_until_full <= 0:
                return None
            
            # Convert periods to actual date based on period type
            # Assuming daily periods for simplicity - could be enhanced
            days_until_full = periods_until_full
            predicted_date = current_date + timedelta(days=days_until_full)
            
            # Don't predict too far in the future (max 1 year)
            max_future_date = datetime.utcnow() + timedelta(days=365)
            if predicted_date > max_future_date:
                return None
            
            return predicted_date
            
        except Exception as e:
            self.logger.error(f"Error predicting full date: {e}")
            return None

    def _detect_anomalies(self, storage_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Detect anomalies in storage usage patterns"""
        anomalies = []
        
        try:
            if len(storage_data) < 5:  # Need sufficient data for anomaly detection
                return anomalies
            
            usage_values = [d['avg_usage_percentage'] for d in storage_data]
            
            # Calculate moving average and standard deviation
            window_size = min(7, len(usage_values) // 2)
            
            for i in range(window_size, len(storage_data)):
                window_data = usage_values[i-window_size:i]
                window_mean = statistics.mean(window_data)
                
                if len(window_data) > 1:
                    window_std = statistics.stdev(window_data)
                else:
                    window_std = 0
                
                current_value = usage_values[i]
                
                # Check if current value is anomalous
                if window_std > 0:
                    z_score = abs(current_value - window_mean) / window_std
                    
                    if z_score > self.anomaly_threshold:
                        anomaly_type = "spike" if current_value > window_mean else "drop"
                        
                        anomalies.append({
                            'timestamp': storage_data[i]['period_start'],
                            'type': anomaly_type,
                            'value': current_value,
                            'expected_value': window_mean,
                            'severity': min(3, int(z_score)),
                            'z_score': z_score
                        })
            
            return anomalies
            
        except Exception as e:
            self.logger.error(f"Error detecting anomalies: {e}")
            return []

    def _generate_trend_recommendations(self, growth_rate: float, 
                                      predicted_full_date: Optional[datetime],
                                      anomalies: List[Dict[str, Any]]) -> List[str]:
        """Generate recommendations based on trend analysis"""
        recommendations = []
        
        try:
            # Growth rate recommendations
            if growth_rate > 5:  # >5% per period
                recommendations.append("🚨 Storage is growing rapidly (>5% per period) - consider immediate cleanup")
            elif growth_rate > 2:
                recommendations.append("⚠️ Storage growth is accelerating - monitor closely and schedule cleanup")
            elif growth_rate > 1:
                recommendations.append("📈 Moderate storage growth detected - periodic cleanup recommended")
            elif growth_rate < -2:
                recommendations.append("📉 Storage usage is decreasing significantly - cleanup efforts are working")
            else:
                recommendations.append("✅ Storage growth is stable")
            
            # Predicted full date recommendations
            if predicted_full_date:
                days_until_full = (predicted_full_date - datetime.utcnow()).days
                
                if days_until_full <= 7:
                    recommendations.append("🚨 URGENT: Storage predicted to be full within a week!")
                elif days_until_full <= 30:
                    recommendations.append("⏰ Storage predicted to be full within a month - plan cleanup")
                elif days_until_full <= 90:
                    recommendations.append("📅 Storage predicted to be full within 3 months")
            
            # Anomaly recommendations
            recent_anomalies = [a for a in anomalies 
                              if (datetime.utcnow() - a['timestamp']).days <= 7]
            
            if recent_anomalies:
                spike_count = len([a for a in recent_anomalies if a['type'] == 'spike'])
                if spike_count > 0:
                    recommendations.append(f"📊 {spike_count} recent storage spikes detected - investigate cause")
            
            # General recommendations
            if not recommendations:
                recommendations.append("✅ Storage trends look normal")
            
            return recommendations
            
        except Exception as e:
            self.logger.error(f"Error generating trend recommendations: {e}")
            return ["Unable to generate trend recommendations"]

    async def update_storage_trends(self, db: Session, max_devices: int = 100):
        """
        Batch update storage trends for all active devices
        
        Args:
            db: Database session
            max_devices: Maximum number of devices to process in one batch
        """
        try:
            self.logger.info("Starting batch storage trend update")
            
            # Get active devices
            devices = (db.query(Device)
                      .filter(Device.is_active == True)
                      .limit(max_devices)
                      .all())
            
            updated_count = 0
            
            for device in devices:
                try:
                    # Calculate trends for different periods
                    for period_type in ["daily", "weekly"]:
                        trend_analysis = await self.calculate_storage_trends(
                            device.device_id, db, period_type
                        )
                        
                        if trend_analysis:
                            # Save or update trend in database
                            await self._save_trend_to_database(device.id, trend_analysis, db)
                            updated_count += 1
                
                except Exception as e:
                    self.logger.error(f"Error updating trends for device {device.device_id}: {e}")
                    continue
            
            self.logger.info(f"Completed batch storage trend update: {updated_count} trends updated")
            
        except Exception as e:
            self.logger.error(f"Error in batch storage trend update: {e}")

    async def _save_trend_to_database(self, device_db_id: int, trend_analysis: TrendAnalysis, 
                                    db: Session):
        """Save trend analysis results to StorageTrend table"""
        try:
            # Check if trend already exists for this period
            period_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
            
            if trend_analysis.period_type == "weekly":
                days_since_monday = period_start.weekday()
                period_start = period_start - timedelta(days=days_since_monday)
            elif trend_analysis.period_type == "monthly":
                period_start = period_start.replace(day=1)
            
            period_end = period_start + timedelta(days=1)
            
            existing_trend = (db.query(StorageTrend)
                            .filter(StorageTrend.device_id == device_db_id)
                            .filter(StorageTrend.period_type == trend_analysis.period_type)
                            .filter(StorageTrend.period_start == period_start)
                            .first())
            
            if existing_trend:
                # Update existing trend
                existing_trend.trend_direction = trend_analysis.trend_direction
                existing_trend.growth_rate = trend_analysis.growth_rate
                existing_trend.predicted_full_date = trend_analysis.predicted_full_date
                existing_trend.confidence_level = trend_analysis.confidence_level
                existing_trend.updated_at = func.now()
            else:
                # Create new trend record
                new_trend = StorageTrend(
                    device_id=device_db_id,
                    period_type=trend_analysis.period_type,
                    period_start=period_start,
                    period_end=period_end,
                    trend_direction=trend_analysis.trend_direction,
                    growth_rate=trend_analysis.growth_rate,
                    predicted_full_date=trend_analysis.predicted_full_date,
                    confidence_level=trend_analysis.confidence_level
                )
                db.add(new_trend)
            
            db.commit()
            
        except Exception as e:
            self.logger.error(f"Error saving trend to database: {e}")
            db.rollback()

    async def get_trend_insights(self, device_id: str, db: Session, 
                               days_back: int = 30) -> Dict[str, Any]:
        """
        Get comprehensive trend insights for a device
        
        Args:
            device_id: Target device ID
            db: Database session
            days_back: Number of days to analyze
            
        Returns:
            Dictionary with trend insights
        """
        try:
            # Get device from database
            device = db.query(Device).filter(Device.device_id == device_id).first()
            if not device:
                return {"error": "Device not found"}
            
            insights = {
                "device_id": device_id,
                "analysis_date": datetime.utcnow().isoformat(),
                "daily_trends": None,
                "weekly_trends": None,
                "summary": {
                    "overall_trend": "stable",
                    "risk_level": "low",
                    "action_required": False
                },
                "forecasts": [],
                "anomaly_summary": {
                    "recent_anomalies": 0,
                    "anomaly_types": []
                }
            }
            
            # Get daily trends
            daily_analysis = await self.calculate_storage_trends(
                device_id, db, "daily", days_back
            )
            
            if daily_analysis:
                insights["daily_trends"] = {
                    "trend_direction": daily_analysis.trend_direction,
                    "growth_rate": daily_analysis.growth_rate,
                    "confidence": daily_analysis.confidence_level,
                    "predicted_full_date": daily_analysis.predicted_full_date.isoformat() if daily_analysis.predicted_full_date else None,
                    "recommendations": daily_analysis.recommendations
                }
                
                # Update summary based on daily trends
                if daily_analysis.growth_rate > 5:
                    insights["summary"]["overall_trend"] = "rapidly_increasing"
                    insights["summary"]["risk_level"] = "high"
                    insights["summary"]["action_required"] = True
                elif daily_analysis.growth_rate > 2:
                    insights["summary"]["overall_trend"] = "increasing"
                    insights["summary"]["risk_level"] = "medium"
                elif daily_analysis.growth_rate < -2:
                    insights["summary"]["overall_trend"] = "decreasing"
                    insights["summary"]["risk_level"] = "low"
            
            # Get weekly trends
            weekly_analysis = await self.calculate_storage_trends(
                device_id, db, "weekly", days_back * 2  # More data for weekly analysis
            )
            
            if weekly_analysis:
                insights["weekly_trends"] = {
                    "trend_direction": weekly_analysis.trend_direction,
                    "growth_rate": weekly_analysis.growth_rate,
                    "confidence": weekly_analysis.confidence_level,
                    "predicted_full_date": weekly_analysis.predicted_full_date.isoformat() if weekly_analysis.predicted_full_date else None
                }
            
            # Generate forecasts
            if daily_analysis:
                current_date = datetime.utcnow()
                for days_ahead in [7, 30, 90]:
                    if daily_analysis.growth_rate > 0:
                        # Simple linear projection
                        projected_growth = daily_analysis.growth_rate * days_ahead
                        # We'd need current usage to make accurate prediction
                        # This is a simplified version
                        insights["forecasts"].append({
                            "date": (current_date + timedelta(days=days_ahead)).isoformat(),
                            "days_ahead": days_ahead,
                            "projected_growth_percentage": projected_growth,
                            "confidence": daily_analysis.confidence_level * 0.9 ** (days_ahead / 30)  # Confidence decreases over time
                        })
                
                # Anomaly summary
                recent_anomalies = [a for a in daily_analysis.anomalies 
                                  if (datetime.utcnow() - a['timestamp']).days <= 7]
                insights["anomaly_summary"]["recent_anomalies"] = len(recent_anomalies)
                insights["anomaly_summary"]["anomaly_types"] = list(set(a['type'] for a in recent_anomalies))
            
            return insights
            
        except Exception as e:
            self.logger.error(f"Error getting trend insights for device {device_id}: {e}")
            return {"error": str(e)}

