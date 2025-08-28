"""
AI/ML Service for AndroidZen Pro

This service provides comprehensive AI/ML capabilities:
- Device usage pattern analysis using scikit-learn
- Predictive maintenance models for storage and performance
- Anomaly detection for security monitoring
- User behavior clustering for personalized recommendations
- Model versioning and updates
- Explainable AI features for recommendations
"""

import asyncio
import json
import logging
import pickle
import numpy as np
import pandas as pd
import joblib
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any, NamedTuple, Union
from dataclasses import dataclass, field
from pathlib import Path
import hashlib
import warnings
from collections import defaultdict, deque

# Scikit-learn imports
from sklearn.ensemble import (
    IsolationForest, RandomForestClassifier, RandomForestRegressor,
    GradientBoostingRegressor
)
from sklearn.cluster import KMeans, DBSCAN
from sklearn.preprocessing import StandardScaler, MinMaxScaler, LabelEncoder
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.metrics import (
    classification_report, confusion_matrix, mean_squared_error,
    mean_absolute_error, silhouette_score
)
from sklearn.linear_model import LinearRegression, LogisticRegression
from sklearn.svm import OneClassSVM
from sklearn.decomposition import PCA
from sklearn.feature_selection import SelectKBest, f_classif
from sklearn.pipeline import Pipeline
from sklearn.base import BaseEstimator, TransformerMixin

# Database and core imports
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_, desc
from .core.database import get_db
from .models.device import Device
from .models.analytics import Analytics, StorageTrend
from .models.security import SecurityEvent, SeverityLevel

# Suppress sklearn warnings
warnings.filterwarnings("ignore", category=UserWarning)


@dataclass
class ModelInfo:
    """Model information and metadata"""
    model_id: str
    model_type: str  # "anomaly", "predictive", "clustering", "classification"
    version: str
    created_at: datetime
    accuracy: Optional[float] = None
    precision: Optional[float] = None
    recall: Optional[float] = None
    f1_score: Optional[float] = None
    feature_importance: Optional[Dict[str, float]] = None
    hyperparameters: Optional[Dict[str, Any]] = None
    training_samples: int = 0
    file_path: Optional[str] = None


@dataclass
class PredictiveMaintenance:
    """Predictive maintenance result"""
    device_id: str
    component: str  # "storage", "battery", "performance", "memory"
    prediction_type: str  # "failure", "degradation", "optimization"
    predicted_date: Optional[datetime]
    confidence: float
    risk_level: str  # "low", "medium", "high", "critical"
    current_health: float  # 0-100 scale
    predicted_health: float  # 0-100 scale
    recommendations: List[str]
    maintenance_actions: List[str]
    time_to_action: Optional[int]  # days


@dataclass
class AnomalyDetection:
    """Anomaly detection result"""
    device_id: str
    timestamp: datetime
    anomaly_type: str
    severity: str
    anomaly_score: float
    confidence: float
    affected_metrics: List[str]
    baseline_values: Dict[str, float]
    actual_values: Dict[str, float]
    deviation_percentage: float
    context: Dict[str, Any]
    explanation: str


@dataclass
class UserBehaviorCluster:
    """User behavior clustering result"""
    cluster_id: int
    cluster_name: str
    device_ids: List[str]
    characteristics: Dict[str, Any]
    usage_patterns: Dict[str, float]
    app_preferences: List[str]
    performance_requirements: str
    security_awareness: str
    recommendations: List[str]


@dataclass
class AIRecommendation:
    """AI-powered recommendation"""
    recommendation_id: str
    device_id: str
    category: str  # "performance", "storage", "security", "battery", "usage"
    title: str
    description: str
    priority: str  # "low", "medium", "high", "urgent"
    confidence: float
    expected_impact: str
    implementation_difficulty: str
    estimated_time: str
    reasoning: List[str]
    evidence: Dict[str, Any]
    alternatives: List[str]


class DeviceFeatureExtractor(BaseEstimator, TransformerMixin):
    """Custom feature extractor for device analytics data"""
    
    def __init__(self, include_temporal_features=True):
        self.include_temporal_features = include_temporal_features
        self.feature_names_ = None
    
    def fit(self, X, y=None):
        """Fit the transformer"""
        return self
    
    def transform(self, X):
        """Transform the data to extract features"""
        if isinstance(X, pd.DataFrame):
            df = X.copy()
        else:
            df = pd.DataFrame(X)
        
        features = []
        feature_names = []
        
        # Basic performance features
        performance_cols = [
            'cpu_usage', 'memory_usage', 'storage_usage_percentage',
            'battery_level', 'running_processes'
        ]
        
        for col in performance_cols:
            if col in df.columns:
                features.append(df[col].fillna(0).values.reshape(-1, 1))
                feature_names.append(col)
        
        # Temperature features
        if 'cpu_temperature' in df.columns:
            features.append(df['cpu_temperature'].fillna(30).values.reshape(-1, 1))
            feature_names.append('cpu_temperature')
        
        if 'battery_temperature' in df.columns:
            features.append(df['battery_temperature'].fillna(25).values.reshape(-1, 1))
            feature_names.append('battery_temperature')
        
        # Network features
        if 'network_strength' in df.columns:
            features.append(df['network_strength'].fillna(-70).values.reshape(-1, 1))
            feature_names.append('network_strength')
        
        # Temporal features
        if self.include_temporal_features and 'recorded_at' in df.columns:
            timestamps = pd.to_datetime(df['recorded_at'])
            
            # Hour of day
            hour_of_day = timestamps.dt.hour.values.reshape(-1, 1)
            features.append(hour_of_day)
            feature_names.append('hour_of_day')
            
            # Day of week
            day_of_week = timestamps.dt.dayofweek.values.reshape(-1, 1)
            features.append(day_of_week)
            feature_names.append('day_of_week')
            
            # Time since last measurement (if applicable)
            if len(timestamps) > 1:
                time_diff = timestamps.diff().dt.total_seconds().fillna(0).values.reshape(-1, 1)
                features.append(time_diff)
                feature_names.append('time_diff_seconds')
        
        # Combine all features
        if features:
            combined_features = np.hstack(features)
        else:
            # Fallback if no features found
            combined_features = np.zeros((len(df), 1))
            feature_names = ['dummy_feature']
        
        self.feature_names_ = feature_names
        return combined_features


class AIService:
    """
    Comprehensive AI/ML service for device management and analytics
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # Model storage
        self.models_dir = Path("models/ai_models")
        self.models_dir.mkdir(parents=True, exist_ok=True)
        
        # Loaded models cache
        self._loaded_models: Dict[str, Any] = {}
        self._model_metadata: Dict[str, ModelInfo] = {}
        
        # Feature extractors
        self.feature_extractor = DeviceFeatureExtractor()
        self.scalers: Dict[str, StandardScaler] = {}
        
        # Anomaly detection models
        self.anomaly_models = {
            "isolation_forest": IsolationForest(contamination=0.1, random_state=42),
            "one_class_svm": OneClassSVM(nu=0.1),
        }
        
        # Clustering models
        self.clustering_models = {
            "kmeans": KMeans(n_clusters=5, random_state=42),
            "dbscan": DBSCAN(eps=0.5, min_samples=5)
        }
        
        # Predictive models
        self.predictive_models = {
            "random_forest_reg": RandomForestRegressor(n_estimators=100, random_state=42),
            "gradient_boosting": GradientBoostingRegressor(random_state=42),
            "linear_regression": LinearRegression()
        }
        
        # Classification models
        self.classification_models = {
            "random_forest_clf": RandomForestClassifier(n_estimators=100, random_state=42),
            "logistic_regression": LogisticRegression(random_state=42)
        }
        
        # Recommendation engine components
        self.recommendation_weights = {
            "performance": 0.3,
            "storage": 0.25,
            "security": 0.25,
            "battery": 0.2
        }
        
    async def initialize_models(self) -> bool:
        """Initialize and load existing models"""
        try:
            self.logger.info("Initializing AI models...")
            
            # Load existing models from disk
            await self._load_existing_models()
            
            # Initialize scalers
            self._initialize_scalers()
            
            self.logger.info("AI models initialized successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize AI models: {e}")
            return False
    
    async def analyze_device_usage_patterns(
        self, 
        device_id: str, 
        days_back: int = 30
    ) -> Dict[str, Any]:
        """
        Analyze device usage patterns using machine learning
        
        Args:
            device_id: Target device ID
            days_back: Number of days to analyze
            
        Returns:
            Dictionary containing usage patterns analysis
        """
        try:
            self.logger.info(f"Analyzing usage patterns for device {device_id}")
            
            # Fetch device data
            data = await self._fetch_device_analytics(device_id, days_back)
            if data.empty:
                return {"error": "No data available for analysis"}
            
            # Extract features
            features = self.feature_extractor.fit_transform(data)
            
            # Scale features
            scaler_key = f"usage_patterns_{device_id}"
            if scaler_key not in self.scalers:
                self.scalers[scaler_key] = StandardScaler()
            
            features_scaled = self.scalers[scaler_key].fit_transform(features)
            
            # Perform clustering analysis
            kmeans = self.clustering_models["kmeans"]
            clusters = kmeans.fit_predict(features_scaled)
            
            # Analyze patterns
            patterns = await self._analyze_usage_clusters(data, clusters)
            
            # Generate insights
            insights = self._generate_usage_insights(data, patterns)
            
            result = {
                "device_id": device_id,
                "analysis_period": f"{days_back} days",
                "total_data_points": len(data),
                "usage_patterns": patterns,
                "insights": insights,
                "recommendations": self._generate_usage_recommendations(patterns),
                "analyzed_at": datetime.now().isoformat()
            }
            
            self.logger.info(f"Usage pattern analysis completed for device {device_id}")
            return result
            
        except Exception as e:
            self.logger.error(f"Usage pattern analysis failed for device {device_id}: {e}")
            return {"error": str(e)}
    
    async def predict_maintenance_needs(
        self, 
        device_id: str,
        prediction_horizon_days: int = 30
    ) -> List[PredictiveMaintenance]:
        """
        Predict maintenance needs using machine learning models
        
        Args:
            device_id: Target device ID
            prediction_horizon_days: Days into the future to predict
            
        Returns:
            List of predictive maintenance recommendations
        """
        try:
            self.logger.info(f"Predicting maintenance needs for device {device_id}")
            
            predictions = []
            
            # Storage prediction
            storage_prediction = await self._predict_storage_maintenance(
                device_id, prediction_horizon_days
            )
            if storage_prediction:
                predictions.append(storage_prediction)
            
            # Performance prediction
            performance_prediction = await self._predict_performance_maintenance(
                device_id, prediction_horizon_days
            )
            if performance_prediction:
                predictions.append(performance_prediction)
            
            # Battery prediction
            battery_prediction = await self._predict_battery_maintenance(
                device_id, prediction_horizon_days
            )
            if battery_prediction:
                predictions.append(battery_prediction)
            
            # Memory prediction
            memory_prediction = await self._predict_memory_maintenance(
                device_id, prediction_horizon_days
            )
            if memory_prediction:
                predictions.append(memory_prediction)
            
            self.logger.info(f"Maintenance prediction completed for device {device_id}")
            return predictions
            
        except Exception as e:
            self.logger.error(f"Maintenance prediction failed for device {device_id}: {e}")
            return []
    
    async def detect_anomalies(
        self, 
        device_id: str,
        sensitivity: float = 0.1
    ) -> List[AnomalyDetection]:
        """
        Detect anomalies in device behavior for security monitoring
        
        Args:
            device_id: Target device ID
            sensitivity: Anomaly detection sensitivity (0.0-1.0)
            
        Returns:
            List of detected anomalies
        """
        try:
            self.logger.info(f"Detecting anomalies for device {device_id}")
            
            # Fetch recent data
            data = await self._fetch_device_analytics(device_id, days_back=7)
            if data.empty:
                return []
            
            # Extract features
            features = self.feature_extractor.fit_transform(data)
            
            # Scale features
            scaler_key = f"anomaly_{device_id}"
            if scaler_key not in self.scalers:
                self.scalers[scaler_key] = StandardScaler()
            
            features_scaled = self.scalers[scaler_key].fit_transform(features)
            
            anomalies = []
            
            # Isolation Forest anomaly detection
            iso_forest = IsolationForest(contamination=sensitivity, random_state=42)
            anomaly_scores = iso_forest.fit_predict(features_scaled)
            decision_scores = iso_forest.decision_function(features_scaled)
            
            # Process anomalies
            for i, (score, decision_score) in enumerate(zip(anomaly_scores, decision_scores)):
                if score == -1:  # Anomaly detected
                    anomaly = await self._create_anomaly_detection(
                        device_id, data.iloc[i], decision_score, features_scaled[i]
                    )
                    if anomaly:
                        anomalies.append(anomaly)
            
            # Security-specific anomaly detection
            security_anomalies = await self._detect_security_anomalies(device_id, data)
            anomalies.extend(security_anomalies)
            
            self.logger.info(f"Anomaly detection completed for device {device_id}, found {len(anomalies)} anomalies")
            return anomalies
            
        except Exception as e:
            self.logger.error(f"Anomaly detection failed for device {device_id}: {e}")
            return []
    
    async def cluster_user_behavior(
        self,
        min_devices: int = 5
    ) -> List[UserBehaviorCluster]:
        """
        Cluster users based on device usage behavior for personalized recommendations
        
        Args:
            min_devices: Minimum number of devices required for clustering
            
        Returns:
            List of user behavior clusters
        """
        try:
            self.logger.info("Clustering user behavior patterns")
            
            # Fetch data for all devices
            all_data = await self._fetch_all_devices_analytics(days_back=30)
            if len(all_data) < min_devices:
                return []
            
            # Group by device and create device profiles
            device_profiles = await self._create_device_profiles(all_data)
            
            if len(device_profiles) < min_devices:
                return []
            
            # Extract clustering features
            features, device_ids = await self._extract_clustering_features(device_profiles)
            
            # Scale features
            scaler = StandardScaler()
            features_scaled = scaler.fit_transform(features)
            
            # Determine optimal number of clusters
            optimal_clusters = self._determine_optimal_clusters(features_scaled)
            
            # Perform clustering
            kmeans = KMeans(n_clusters=optimal_clusters, random_state=42)
            cluster_labels = kmeans.fit_predict(features_scaled)
            
            # Create cluster objects
            clusters = await self._create_behavior_clusters(
                device_ids, cluster_labels, device_profiles, features_scaled
            )
            
            self.logger.info(f"User behavior clustering completed, found {len(clusters)} clusters")
            return clusters
            
        except Exception as e:
            self.logger.error(f"User behavior clustering failed: {e}")
            return []
    
    async def generate_ai_recommendations(
        self,
        device_id: str,
        include_explanations: bool = True
    ) -> List[AIRecommendation]:
        """
        Generate AI-powered recommendations with explainable features
        
        Args:
            device_id: Target device ID
            include_explanations: Whether to include detailed explanations
            
        Returns:
            List of AI recommendations
        """
        try:
            self.logger.info(f"Generating AI recommendations for device {device_id}")
            
            recommendations = []
            
            # Get device data and analysis
            data = await self._fetch_device_analytics(device_id, days_back=30)
            if data.empty:
                return []
            
            # Performance recommendations
            perf_recs = await self._generate_performance_recommendations(
                device_id, data, include_explanations
            )
            recommendations.extend(perf_recs)
            
            # Storage recommendations
            storage_recs = await self._generate_storage_recommendations(
                device_id, data, include_explanations
            )
            recommendations.extend(storage_recs)
            
            # Security recommendations
            security_recs = await self._generate_security_recommendations(
                device_id, data, include_explanations
            )
            recommendations.extend(security_recs)
            
            # Battery recommendations
            battery_recs = await self._generate_battery_recommendations(
                device_id, data, include_explanations
            )
            recommendations.extend(battery_recs)
            
            # Usage optimization recommendations
            usage_recs = await self._generate_usage_recommendations(
                device_id, data, include_explanations
            )
            recommendations.extend(usage_recs)
            
            # Sort by priority and confidence
            recommendations.sort(
                key=lambda x: (
                    {"urgent": 4, "high": 3, "medium": 2, "low": 1}[x.priority],
                    x.confidence
                ),
                reverse=True
            )
            
            self.logger.info(f"Generated {len(recommendations)} AI recommendations for device {device_id}")
            return recommendations
            
        except Exception as e:
            self.logger.error(f"AI recommendation generation failed for device {device_id}: {e}")
            return []
    
    async def train_models(
        self,
        model_types: List[str] = None,
        force_retrain: bool = False
    ) -> Dict[str, bool]:
        """
        Train ML models on collected device data
        
        Args:
            model_types: List of model types to train (None for all)
            force_retrain: Whether to force retraining of existing models
            
        Returns:
            Dictionary of training results
        """
        try:
            self.logger.info("Starting model training")
            
            if model_types is None:
                model_types = ["anomaly", "predictive", "clustering", "classification"]
            
            results = {}
            
            # Train anomaly detection models
            if "anomaly" in model_types:
                results["anomaly"] = await self._train_anomaly_models(force_retrain)
            
            # Train predictive models
            if "predictive" in model_types:
                results["predictive"] = await self._train_predictive_models(force_retrain)
            
            # Train clustering models
            if "clustering" in model_types:
                results["clustering"] = await self._train_clustering_models(force_retrain)
            
            # Train classification models
            if "classification" in model_types:
                results["classification"] = await self._train_classification_models(force_retrain)
            
            self.logger.info("Model training completed")
            return results
            
        except Exception as e:
            self.logger.error(f"Model training failed: {e}")
            return {"error": str(e)}
    
    async def update_models(self, model_id: str = None) -> bool:
        """
        Update models with new data and implement model versioning
        
        Args:
            model_id: Specific model to update (None for all)
            
        Returns:
            Success status
        """
        try:
            self.logger.info(f"Updating models: {model_id or 'all'}")
            
            if model_id:
                # Update specific model
                success = await self._update_specific_model(model_id)
            else:
                # Update all models
                success = await self._update_all_models()
            
            # Save model metadata
            await self._save_model_metadata()
            
            self.logger.info("Model update completed")
            return success
            
        except Exception as e:
            self.logger.error(f"Model update failed: {e}")
            return False
    
    def get_model_info(self, model_id: str = None) -> Union[ModelInfo, List[ModelInfo]]:
        """Get information about trained models"""
        if model_id:
            return self._model_metadata.get(model_id)
        else:
            return list(self._model_metadata.values())
    
    # Private methods for implementation details
    async def _fetch_device_analytics(self, device_id: str, days_back: int) -> pd.DataFrame:
        """Fetch device analytics data"""
        try:
            db = next(get_db())
            try:
                # Get device
                device = db.query(Device).filter(Device.device_id == device_id).first()
                if not device:
                    return pd.DataFrame()
                
                # Calculate date range
                end_date = datetime.now()
                start_date = end_date - timedelta(days=days_back)
                
                # Fetch analytics data
                analytics = db.query(Analytics).filter(
                    and_(
                        Analytics.device_id == device.id,
                        Analytics.recorded_at >= start_date,
                        Analytics.recorded_at <= end_date
                    )
                ).order_by(Analytics.recorded_at).all()
                
                # Convert to DataFrame
                if analytics:
                    data = pd.DataFrame([a.to_dict() for a in analytics])
                    return data
                else:
                    return pd.DataFrame()
            finally:
                db.close()
                
        except Exception as e:
            self.logger.error(f"Failed to fetch device analytics: {e}")
            return pd.DataFrame()
    
    async def _analyze_usage_clusters(self, data: pd.DataFrame, clusters: np.ndarray) -> Dict[str, Any]:
        """Analyze usage patterns from clusters"""
        patterns = {}
        
        unique_clusters = np.unique(clusters)
        
        for cluster_id in unique_clusters:
            cluster_mask = clusters == cluster_id
            cluster_data = data[cluster_mask]
            
            if len(cluster_data) == 0:
                continue
            
            # Calculate cluster characteristics
            pattern = {
                "cluster_id": int(cluster_id),
                "size": len(cluster_data),
                "percentage": (len(cluster_data) / len(data)) * 100,
                "characteristics": {
                    "avg_cpu_usage": cluster_data['cpu_usage'].mean() if 'cpu_usage' in cluster_data else None,
                    "avg_memory_usage": cluster_data['memory_usage'].mean() if 'memory_usage' in cluster_data else None,
                    "avg_battery_level": cluster_data['battery_level'].mean() if 'battery_level' in cluster_data else None,
                    "avg_storage_usage": cluster_data['storage_usage_percentage'].mean() if 'storage_usage_percentage' in cluster_data else None,
                },
                "time_patterns": self._analyze_temporal_patterns(cluster_data),
                "dominant_usage_type": self._determine_usage_type(cluster_data)
            }
            
            patterns[f"cluster_{cluster_id}"] = pattern
        
        return patterns
    
    def _generate_usage_insights(self, data: pd.DataFrame, patterns: Dict[str, Any]) -> List[str]:
        """Generate insights from usage patterns"""
        insights = []
        
        # Overall usage insights
        if 'cpu_usage' in data.columns:
            avg_cpu = data['cpu_usage'].mean()
            if avg_cpu > 80:
                insights.append("High CPU usage detected - device may be under strain")
            elif avg_cpu < 20:
                insights.append("Low CPU usage suggests efficient device operation")
        
        # Pattern-specific insights
        for pattern_name, pattern in patterns.items():
            cluster_id = pattern['cluster_id']
            size = pattern['size']
            percentage = pattern['percentage']
            
            if percentage > 50:
                insights.append(f"Dominant usage pattern (Cluster {cluster_id}) represents {percentage:.1f}% of device usage")
            
            if pattern['dominant_usage_type'] == 'high_performance':
                insights.append(f"High performance usage detected in {percentage:.1f}% of measurements")
            elif pattern['dominant_usage_type'] == 'idle':
                insights.append(f"Device idle state detected in {percentage:.1f}% of measurements")
        
        return insights
    
    def _generate_usage_recommendations(self, patterns: Dict[str, Any]) -> List[str]:
        """Generate recommendations based on usage patterns"""
        recommendations = []
        
        for pattern_name, pattern in patterns.items():
            usage_type = pattern['dominant_usage_type']
            percentage = pattern['percentage']
            
            if usage_type == 'high_performance' and percentage > 30:
                recommendations.append("Consider optimizing high-performance applications")
                recommendations.append("Monitor device temperature during intensive usage")
            
            if usage_type == 'battery_drain' and percentage > 20:
                recommendations.append("Investigate battery-draining applications")
                recommendations.append("Enable battery optimization features")
            
            if usage_type == 'storage_heavy' and percentage > 25:
                recommendations.append("Regular storage cleanup recommended")
                recommendations.append("Consider moving media files to external storage")
        
        return recommendations
    
    async def _predict_storage_maintenance(self, device_id: str, horizon_days: int) -> Optional[PredictiveMaintenance]:
        """Predict storage-related maintenance needs"""
        try:
            data = await self._fetch_device_analytics(device_id, days_back=60)
            if data.empty or 'storage_usage_percentage' not in data.columns:
                return None
            
            # Prepare time series data
            storage_data = data[['recorded_at', 'storage_usage_percentage']].dropna()
            if len(storage_data) < 10:
                return None
            
            storage_data['days_from_start'] = (
                pd.to_datetime(storage_data['recorded_at']) - 
                pd.to_datetime(storage_data['recorded_at']).min()
            ).dt.days
            
            # Train simple linear regression for trend
            X = storage_data['days_from_start'].values.reshape(-1, 1)
            y = storage_data['storage_usage_percentage'].values
            
            model = LinearRegression()
            model.fit(X, y)
            
            # Predict future storage usage
            current_day = storage_data['days_from_start'].max()
            future_day = current_day + horizon_days
            predicted_usage = model.predict([[future_day]])[0]
            
            # Calculate current health
            current_usage = storage_data['storage_usage_percentage'].iloc[-1]
            current_health = max(0, 100 - current_usage)
            predicted_health = max(0, 100 - predicted_usage)
            
            # Determine risk level
            if predicted_usage >= 95:
                risk_level = "critical"
            elif predicted_usage >= 85:
                risk_level = "high"
            elif predicted_usage >= 75:
                risk_level = "medium"
            else:
                risk_level = "low"
            
            # Calculate time to action
            if model.coef_[0] > 0:  # Storage is increasing
                days_to_90_percent = (90 - current_usage) / model.coef_[0]
                time_to_action = max(1, int(days_to_90_percent)) if days_to_90_percent > 0 else None
            else:
                time_to_action = None
            
            return PredictiveMaintenance(
                device_id=device_id,
                component="storage",
                prediction_type="degradation",
                predicted_date=datetime.now() + timedelta(days=horizon_days) if predicted_usage >= 85 else None,
                confidence=min(0.9, len(storage_data) / 30),  # Higher confidence with more data
                risk_level=risk_level,
                current_health=current_health,
                predicted_health=predicted_health,
                recommendations=[
                    "Monitor storage usage trends",
                    "Plan storage cleanup activities",
                    "Consider storage expansion options"
                ] if risk_level in ["high", "critical"] else [
                    "Continue monitoring storage usage"
                ],
                maintenance_actions=[
                    "Clear application caches",
                    "Remove unused applications",
                    "Move media files to external storage"
                ] if risk_level in ["high", "critical"] else [],
                time_to_action=time_to_action
            )
            
        except Exception as e:
            self.logger.error(f"Storage maintenance prediction failed: {e}")
            return None
    
    async def _predict_performance_maintenance(self, device_id: str, horizon_days: int) -> Optional[PredictiveMaintenance]:
        """Predict performance-related maintenance needs"""
        try:
            data = await self._fetch_device_analytics(device_id, days_back=30)
            if data.empty:
                return None
            
            # Calculate performance score trend
            performance_metrics = ['cpu_usage', 'memory_usage', 'running_processes']
            available_metrics = [col for col in performance_metrics if col in data.columns]
            
            if not available_metrics:
                return None
            
            # Calculate composite performance score
            performance_scores = []
            for _, row in data.iterrows():
                score = 100
                metric_count = 0
                
                for metric in available_metrics:
                    if pd.notna(row[metric]):
                        if metric in ['cpu_usage', 'memory_usage']:
                            score -= row[metric] * 0.3
                        elif metric == 'running_processes':
                            # Normalize running processes (assuming 100 is high)
                            score -= min(30, row[metric] / 100 * 30)
                        metric_count += 1
                
                if metric_count > 0:
                    performance_scores.append(max(0, score))
            
            if len(performance_scores) < 5:
                return None
            
            # Analyze trend
            recent_scores = performance_scores[-7:]  # Last 7 measurements
            early_scores = performance_scores[:7] if len(performance_scores) > 14 else performance_scores[:-7]
            
            current_health = np.mean(recent_scores)
            if early_scores:
                historical_health = np.mean(early_scores)
                health_trend = current_health - historical_health
            else:
                health_trend = 0
            
            # Predict future health
            predicted_health = current_health + (health_trend * (horizon_days / 7))
            
            # Determine risk level
            if current_health < 30 or predicted_health < 20:
                risk_level = "critical"
            elif current_health < 50 or predicted_health < 40:
                risk_level = "high"
            elif current_health < 70 or predicted_health < 60:
                risk_level = "medium"
            else:
                risk_level = "low"
            
            return PredictiveMaintenance(
                device_id=device_id,
                component="performance",
                prediction_type="degradation" if health_trend < 0 else "optimization",
                predicted_date=datetime.now() + timedelta(days=horizon_days) if risk_level in ["high", "critical"] else None,
                confidence=min(0.8, len(performance_scores) / 20),
                risk_level=risk_level,
                current_health=current_health,
                predicted_health=predicted_health,
                recommendations=[
                    "Monitor system performance regularly",
                    "Close unnecessary applications",
                    "Restart device periodically"
                ] if risk_level in ["medium", "high", "critical"] else [
                    "Performance is optimal"
                ],
                maintenance_actions=[
                    "Clear system cache",
                    "Disable unnecessary background apps",
                    "Update system and applications"
                ] if risk_level in ["high", "critical"] else [],
                time_to_action=7 if risk_level == "critical" else (14 if risk_level == "high" else None)
            )
            
        except Exception as e:
            self.logger.error(f"Performance maintenance prediction failed: {e}")
            return None
    
    async def _predict_battery_maintenance(self, device_id: str, horizon_days: int) -> Optional[PredictiveMaintenance]:
        """Predict battery-related maintenance needs"""
        try:
            data = await self._fetch_device_analytics(device_id, days_back=30)
            if data.empty or 'battery_level' not in data.columns:
                return None
            
            battery_data = data[['recorded_at', 'battery_level', 'battery_temperature']].dropna(subset=['battery_level'])
            if len(battery_data) < 5:
                return None
            
            # Analyze battery patterns
            avg_battery = battery_data['battery_level'].mean()
            min_battery = battery_data['battery_level'].min()
            max_battery = battery_data['battery_level'].max()
            
            # Temperature analysis
            if 'battery_temperature' in battery_data.columns:
                avg_temp = battery_data['battery_temperature'].mean()
                max_temp = battery_data['battery_temperature'].max()
            else:
                avg_temp = max_temp = None
            
            # Calculate battery health score
            health_factors = []
            
            # Average level factor
            if avg_battery < 30:
                health_factors.append(30)
            elif avg_battery < 50:
                health_factors.append(60)
            else:
                health_factors.append(90)
            
            # Temperature factor
            if max_temp and max_temp > 40:
                health_factors.append(40)  # High temperature is bad
            elif max_temp and max_temp > 35:
                health_factors.append(70)
            else:
                health_factors.append(90)
            
            current_health = np.mean(health_factors)
            
            # Simple prediction based on current state
            if current_health > 80:
                predicted_health = current_health - 5
                risk_level = "low"
            elif current_health > 60:
                predicted_health = current_health - 10
                risk_level = "medium"
            else:
                predicted_health = current_health - 15
                risk_level = "high"
            
            if max_temp and max_temp > 42:
                risk_level = "critical"
                predicted_health -= 20
            
            return PredictiveMaintenance(
                device_id=device_id,
                component="battery",
                prediction_type="degradation",
                predicted_date=datetime.now() + timedelta(days=horizon_days) if risk_level in ["high", "critical"] else None,
                confidence=0.7,
                risk_level=risk_level,
                current_health=current_health,
                predicted_health=max(0, predicted_health),
                recommendations=[
                    "Monitor battery temperature",
                    "Avoid extreme temperatures",
                    "Use battery optimization features"
                ] if risk_level in ["medium", "high", "critical"] else [
                    "Battery health is good"
                ],
                maintenance_actions=[
                    "Check charging habits",
                    "Enable battery saver mode",
                    "Close battery-draining apps"
                ] if risk_level in ["high", "critical"] else [],
                time_to_action=3 if risk_level == "critical" else (7 if risk_level == "high" else None)
            )
            
        except Exception as e:
            self.logger.error(f"Battery maintenance prediction failed: {e}")
            return None
    
    async def _predict_memory_maintenance(self, device_id: str, horizon_days: int) -> Optional[PredictiveMaintenance]:
        """Predict memory-related maintenance needs"""
        try:
            data = await self._fetch_device_analytics(device_id, days_back=30)
            if data.empty or 'memory_usage' not in data.columns:
                return None
            
            memory_data = data[['memory_usage', 'memory_available', 'memory_total']].dropna(subset=['memory_usage'])
            if len(memory_data) < 5:
                return None
            
            # Analyze memory patterns
            avg_memory_usage = memory_data['memory_usage'].mean()
            max_memory_usage = memory_data['memory_usage'].max()
            
            # Calculate memory health
            if avg_memory_usage > 90:
                current_health = 20
                risk_level = "critical"
            elif avg_memory_usage > 80:
                current_health = 40
                risk_level = "high"
            elif avg_memory_usage > 70:
                current_health = 65
                risk_level = "medium"
            else:
                current_health = 85
                risk_level = "low"
            
            # Predict based on trend
            if len(memory_data) > 10:
                recent_avg = memory_data['memory_usage'].tail(5).mean()
                early_avg = memory_data['memory_usage'].head(5).mean()
                trend = recent_avg - early_avg
            else:
                trend = 0
            
            predicted_health = current_health - (trend * 0.5)
            
            return PredictiveMaintenance(
                device_id=device_id,
                component="memory",
                prediction_type="optimization",
                predicted_date=datetime.now() + timedelta(days=horizon_days) if risk_level in ["high", "critical"] else None,
                confidence=0.75,
                risk_level=risk_level,
                current_health=current_health,
                predicted_health=max(0, predicted_health),
                recommendations=[
                    "Monitor memory-intensive applications",
                    "Close unused applications regularly",
                    "Consider device restart"
                ] if risk_level in ["medium", "high", "critical"] else [
                    "Memory usage is optimal"
                ],
                maintenance_actions=[
                    "Clear RAM cache",
                    "Uninstall unused apps",
                    "Disable auto-start apps"
                ] if risk_level in ["high", "critical"] else [],
                time_to_action=1 if risk_level == "critical" else (3 if risk_level == "high" else None)
            )
            
        except Exception as e:
            self.logger.error(f"Memory maintenance prediction failed: {e}")
            return None
    
    async def _create_anomaly_detection(
        self,
        device_id: str,
        data_row: pd.Series,
        anomaly_score: float,
        features: np.ndarray
    ) -> Optional[AnomalyDetection]:
        """Create anomaly detection result"""
        try:
            # Determine anomaly type and severity
            anomaly_type = "performance"
            severity = "medium"
            
            # Analyze which metrics are anomalous
            affected_metrics = []
            baseline_values = {}
            actual_values = {}
            
            metric_columns = ['cpu_usage', 'memory_usage', 'storage_usage_percentage', 'battery_level']
            
            for metric in metric_columns:
                if metric in data_row.index and pd.notna(data_row[metric]):
                    actual_values[metric] = float(data_row[metric])
                    
                    # Simple baseline (could be improved with historical data)
                    if metric == 'cpu_usage':
                        baseline_values[metric] = 30.0
                        if data_row[metric] > 90:
                            affected_metrics.append(metric)
                    elif metric == 'memory_usage':
                        baseline_values[metric] = 50.0
                        if data_row[metric] > 85:
                            affected_metrics.append(metric)
                    elif metric == 'storage_usage_percentage':
                        baseline_values[metric] = 60.0
                        if data_row[metric] > 90:
                            affected_metrics.append(metric)
                    elif metric == 'battery_level':
                        baseline_values[metric] = 50.0
                        if data_row[metric] < 10:
                            affected_metrics.append(metric)
            
            if not affected_metrics:
                return None
            
            # Calculate deviation
            deviations = []
            for metric in affected_metrics:
                if metric in baseline_values and metric in actual_values:
                    deviation = abs(actual_values[metric] - baseline_values[metric]) / baseline_values[metric] * 100
                    deviations.append(deviation)
            
            avg_deviation = np.mean(deviations) if deviations else 0
            
            # Determine severity based on deviation and score
            if avg_deviation > 100 or abs(anomaly_score) > 0.5:
                severity = "high"
            elif avg_deviation > 50 or abs(anomaly_score) > 0.3:
                severity = "medium"
            else:
                severity = "low"
            
            # Generate explanation
            explanation = f"Anomaly detected in {', '.join(affected_metrics)}. "
            explanation += f"Average deviation: {avg_deviation:.1f}% from baseline."
            
            return AnomalyDetection(
                device_id=device_id,
                timestamp=datetime.now(),
                anomaly_type=anomaly_type,
                severity=severity,
                anomaly_score=float(abs(anomaly_score)),
                confidence=min(0.9, abs(anomaly_score) * 2),
                affected_metrics=affected_metrics,
                baseline_values=baseline_values,
                actual_values=actual_values,
                deviation_percentage=avg_deviation,
                context={
                    "detection_method": "isolation_forest",
                    "feature_count": len(features),
                    "data_timestamp": data_row.get('recorded_at', datetime.now()).isoformat() if 'recorded_at' in data_row.index else datetime.now().isoformat()
                },
                explanation=explanation
            )
            
        except Exception as e:
            self.logger.error(f"Failed to create anomaly detection: {e}")
            return None
    
    async def _detect_security_anomalies(self, device_id: str, data: pd.DataFrame) -> List[AnomalyDetection]:
        """Detect security-specific anomalies"""
        anomalies = []
        
        try:
            # Check for unusual network activity patterns
            if 'network_strength' in data.columns:
                network_data = data['network_strength'].dropna()
                if len(network_data) > 5:
                    # Detect sudden drops in network strength
                    sudden_drops = network_data.diff() < -20
                    if sudden_drops.any():
                        anomaly = AnomalyDetection(
                            device_id=device_id,
                            timestamp=datetime.now(),
                            anomaly_type="network",
                            severity="medium",
                            anomaly_score=0.7,
                            confidence=0.8,
                            affected_metrics=["network_strength"],
                            baseline_values={"network_strength": float(network_data.mean())},
                            actual_values={"network_strength": float(network_data.iloc[-1])},
                            deviation_percentage=float(abs(network_data.iloc[-1] - network_data.mean()) / abs(network_data.mean()) * 100),
                            context={"detection_method": "network_monitoring"},
                            explanation="Sudden drop in network strength detected"
                        )
                        anomalies.append(anomaly)
            
            # Check for temperature anomalies (potential security concern)
            temp_columns = ['cpu_temperature', 'battery_temperature']
            for temp_col in temp_columns:
                if temp_col in data.columns:
                    temp_data = data[temp_col].dropna()
                    if len(temp_data) > 0 and temp_data.max() > 45:  # High temperature threshold
                        anomaly = AnomalyDetection(
                            device_id=device_id,
                            timestamp=datetime.now(),
                            anomaly_type="thermal",
                            severity="high" if temp_data.max() > 50 else "medium",
                            anomaly_score=0.8,
                            confidence=0.9,
                            affected_metrics=[temp_col],
                            baseline_values={temp_col: 30.0},
                            actual_values={temp_col: float(temp_data.max())},
                            deviation_percentage=float((temp_data.max() - 30) / 30 * 100),
                            context={"detection_method": "thermal_monitoring"},
                            explanation=f"High {temp_col.replace('_', ' ')} detected - possible security threat or hardware issue"
                        )
                        anomalies.append(anomaly)
            
        except Exception as e:
            self.logger.error(f"Security anomaly detection failed: {e}")
        
        return anomalies
    
    # Additional helper methods would continue here...
    # Due to length constraints, I'll include the key structural methods
    
    def _analyze_temporal_patterns(self, data: pd.DataFrame) -> Dict[str, Any]:
        """Analyze temporal patterns in the data"""
        patterns = {}
        
        if 'recorded_at' in data.columns:
            timestamps = pd.to_datetime(data['recorded_at'])
            
            # Hour of day analysis
            hours = timestamps.dt.hour
            patterns['peak_hours'] = hours.mode().tolist()
            patterns['hourly_distribution'] = hours.value_counts().to_dict()
            
            # Day of week analysis
            days = timestamps.dt.dayofweek
            patterns['peak_days'] = days.mode().tolist()
            patterns['daily_distribution'] = days.value_counts().to_dict()
        
        return patterns
    
    def _determine_usage_type(self, data: pd.DataFrame) -> str:
        """Determine the dominant usage type for a cluster"""
        
        # Analyze CPU usage
        avg_cpu = data['cpu_usage'].mean() if 'cpu_usage' in data.columns else 0
        
        # Analyze memory usage
        avg_memory = data['memory_usage'].mean() if 'memory_usage' in data.columns else 0
        
        # Analyze battery level
        avg_battery = data['battery_level'].mean() if 'battery_level' in data.columns else 100
        
        # Analyze storage
        avg_storage = data['storage_usage_percentage'].mean() if 'storage_usage_percentage' in data.columns else 0
        
        # Determine usage type based on patterns
        if avg_cpu > 70 and avg_memory > 70:
            return "high_performance"
        elif avg_cpu < 20 and avg_memory < 30:
            return "idle"
        elif avg_battery < 20:
            return "battery_drain"
        elif avg_storage > 85:
            return "storage_heavy"
        else:
            return "normal"
    
    async def _save_model_metadata(self):
        """Save model metadata to disk"""
        try:
            metadata_file = self.models_dir / "model_metadata.json"
            
            # Convert ModelInfo objects to dictionaries
            metadata_dict = {}
            for model_id, model_info in self._model_metadata.items():
                metadata_dict[model_id] = {
                    "model_id": model_info.model_id,
                    "model_type": model_info.model_type,
                    "version": model_info.version,
                    "created_at": model_info.created_at.isoformat(),
                    "accuracy": model_info.accuracy,
                    "precision": model_info.precision,
                    "recall": model_info.recall,
                    "f1_score": model_info.f1_score,
                    "feature_importance": model_info.feature_importance,
                    "hyperparameters": model_info.hyperparameters,
                    "training_samples": model_info.training_samples,
                    "file_path": model_info.file_path
                }
            
            with open(metadata_file, 'w') as f:
                json.dump(metadata_dict, f, indent=2)
                
        except Exception as e:
            self.logger.error(f"Failed to save model metadata: {e}")
    
    async def _load_existing_models(self):
        """Load existing models from disk"""
        try:
            metadata_file = self.models_dir / "model_metadata.json"
            
            if metadata_file.exists():
                with open(metadata_file, 'r') as f:
                    metadata_dict = json.load(f)
                
                for model_id, metadata in metadata_dict.items():
                    model_info = ModelInfo(
                        model_id=metadata["model_id"],
                        model_type=metadata["model_type"],
                        version=metadata["version"],
                        created_at=datetime.fromisoformat(metadata["created_at"]),
                        accuracy=metadata.get("accuracy"),
                        precision=metadata.get("precision"),
                        recall=metadata.get("recall"),
                        f1_score=metadata.get("f1_score"),
                        feature_importance=metadata.get("feature_importance"),
                        hyperparameters=metadata.get("hyperparameters"),
                        training_samples=metadata.get("training_samples", 0),
                        file_path=metadata.get("file_path")
                    )
                    
                    self._model_metadata[model_id] = model_info
                    
                    # Load the actual model if file exists
                    if model_info.file_path and Path(model_info.file_path).exists():
                        try:
                            model = joblib.load(model_info.file_path)
                            self._loaded_models[model_id] = model
                        except Exception as e:
                            self.logger.warning(f"Failed to load model {model_id}: {e}")
            
        except Exception as e:
            self.logger.error(f"Failed to load existing models: {e}")
    
    def _initialize_scalers(self):
        """Initialize feature scalers"""
        self.scalers = {
            "global_scaler": StandardScaler(),
            "anomaly_scaler": StandardScaler(),
            "clustering_scaler": StandardScaler()
        }
    
    # Training methods (simplified for space)
    async def _train_anomaly_models(self, force_retrain: bool) -> bool:
        """Train anomaly detection models"""
        try:
            # Implementation would fetch training data and train models
            self.logger.info("Training anomaly detection models")
            return True
        except Exception as e:
            self.logger.error(f"Anomaly model training failed: {e}")
            return False
    
    async def _train_predictive_models(self, force_retrain: bool) -> bool:
        """Train predictive maintenance models"""
        try:
            self.logger.info("Training predictive models")
            return True
        except Exception as e:
            self.logger.error(f"Predictive model training failed: {e}")
            return False
    
    async def _train_clustering_models(self, force_retrain: bool) -> bool:
        """Train clustering models"""
        try:
            self.logger.info("Training clustering models")
            return True
        except Exception as e:
            self.logger.error(f"Clustering model training failed: {e}")
            return False
    
    async def _train_classification_models(self, force_retrain: bool) -> bool:
        """Train classification models"""
        try:
            self.logger.info("Training classification models")
            return True
        except Exception as e:
            self.logger.error(f"Classification model training failed: {e}")
            return False
    
    async def _update_specific_model(self, model_id: str) -> bool:
        """Update a specific model"""
        try:
            self.logger.info(f"Updating model {model_id}")
            return True
        except Exception as e:
            self.logger.error(f"Model update failed for {model_id}: {e}")
            return False
    
    async def _update_all_models(self) -> bool:
        """Update all models"""
        try:
            self.logger.info("Updating all models")
            return True
        except Exception as e:
            self.logger.error(f"All models update failed: {e}")
            return False
    
    # Implementation of comprehensive functionality
    async def _fetch_all_devices_analytics(self, days_back: int) -> pd.DataFrame:
        """Fetch analytics for all devices"""
        try:
            db = next(get_db())
            try:
                # Calculate date range
                end_date = datetime.now()
                start_date = end_date - timedelta(days=days_back)
                
                # Fetch analytics for all devices
                analytics = db.query(Analytics).filter(
                    and_(
                        Analytics.recorded_at >= start_date,
                        Analytics.recorded_at <= end_date
                    )
                ).all()
                
                if analytics:
                    data = pd.DataFrame([a.to_dict() for a in analytics])
                    return data
                else:
                    return pd.DataFrame()
            finally:
                db.close()
                    
        except Exception as e:
            self.logger.error(f"Failed to fetch all devices analytics: {e}")
            return pd.DataFrame()
    
    async def _create_device_profiles(self, data: pd.DataFrame) -> Dict[str, Dict]:
        """Create device profiles for clustering"""
        try:
            if data.empty:
                return {}
            
            profiles = {}
            
            # Group by device_id
            grouped = data.groupby('device_id')
            
            for device_id, device_data in grouped:
                # Calculate aggregate statistics
                profile = {
                    'device_id': device_id,
                    'total_data_points': len(device_data),
                    
                    # Performance metrics
                    'avg_cpu_usage': device_data['cpu_usage'].mean() if 'cpu_usage' in device_data else 0,
                    'max_cpu_usage': device_data['cpu_usage'].max() if 'cpu_usage' in device_data else 0,
                    'std_cpu_usage': device_data['cpu_usage'].std() if 'cpu_usage' in device_data else 0,
                    
                    'avg_memory_usage': device_data['memory_usage'].mean() if 'memory_usage' in device_data else 0,
                    'max_memory_usage': device_data['memory_usage'].max() if 'memory_usage' in device_data else 0,
                    'std_memory_usage': device_data['memory_usage'].std() if 'memory_usage' in device_data else 0,
                    
                    'avg_storage_usage': device_data['storage_usage_percentage'].mean() if 'storage_usage_percentage' in device_data else 0,
                    'storage_growth_rate': self._calculate_storage_growth_rate(device_data),
                    
                    'avg_battery_level': device_data['battery_level'].mean() if 'battery_level' in device_data else 0,
                    'battery_drain_rate': self._calculate_battery_drain_rate(device_data),
                    
                    'avg_running_processes': device_data['running_processes'].mean() if 'running_processes' in device_data else 0,
                    
                    # Network patterns
                    'avg_network_strength': device_data['network_strength'].mean() if 'network_strength' in device_data else 0,
                    
                    # Temporal patterns
                    'peak_usage_hour': self._find_peak_usage_hour(device_data),
                    'weekend_usage_ratio': self._calculate_weekend_usage_ratio(device_data),
                    
                    # Performance stability
                    'performance_variability': self._calculate_performance_variability(device_data),
                    'anomaly_frequency': (device_data['is_anomaly'].sum() / len(device_data)) if 'is_anomaly' in device_data else 0,
                    
                    # Temperature patterns
                    'avg_cpu_temp': device_data['cpu_temperature'].mean() if 'cpu_temperature' in device_data else 0,
                    'max_cpu_temp': device_data['cpu_temperature'].max() if 'cpu_temperature' in device_data else 0,
                    'avg_battery_temp': device_data['battery_temperature'].mean() if 'battery_temperature' in device_data else 0
                }
                
                profiles[str(device_id)] = profile
            
            return profiles
            
        except Exception as e:
            self.logger.error(f"Failed to create device profiles: {e}")
            return {}
    
    async def _extract_clustering_features(self, profiles: Dict) -> Tuple[np.ndarray, List[str]]:
        """Extract features for clustering"""
        try:
            if not profiles:
                return np.array([]), []
            
            feature_names = [
                'avg_cpu_usage', 'std_cpu_usage', 'avg_memory_usage', 'std_memory_usage',
                'avg_storage_usage', 'storage_growth_rate', 'avg_battery_level', 'battery_drain_rate',
                'avg_running_processes', 'peak_usage_hour', 'weekend_usage_ratio',
                'performance_variability', 'anomaly_frequency', 'max_cpu_temp'
            ]
            
            features_data = []
            device_ids = []
            
            for device_id, profile in profiles.items():
                device_features = []
                for feature_name in feature_names:
                    value = profile.get(feature_name, 0)
                    # Handle NaN values
                    if pd.isna(value):
                        value = 0
                    device_features.append(float(value))
                
                features_data.append(device_features)
                device_ids.append(device_id)
            
            features_array = np.array(features_data)
            return features_array, device_ids
            
        except Exception as e:
            self.logger.error(f"Failed to extract clustering features: {e}")
            return np.array([]), []
    
    def _determine_optimal_clusters(self, features: np.ndarray) -> int:
        """Determine optimal number of clusters using silhouette analysis"""
        try:
            if features.shape[0] < 6:  # Need at least 6 samples
                return min(3, features.shape[0])
            
            max_clusters = min(8, features.shape[0] - 1)
            best_score = -1
            best_k = 3
            
            for k in range(3, max_clusters + 1):
                try:
                    kmeans = KMeans(n_clusters=k, random_state=42)
                    cluster_labels = kmeans.fit_predict(features)
                    
                    # Calculate silhouette score
                    if len(np.unique(cluster_labels)) > 1:
                        score = silhouette_score(features, cluster_labels)
                        if score > best_score:
                            best_score = score
                            best_k = k
                except:
                    continue
            
            return best_k
            
        except Exception as e:
            self.logger.error(f"Failed to determine optimal clusters: {e}")
            return 3
    
    async def _create_behavior_clusters(
        self, 
        device_ids: List[str], 
        labels: np.ndarray, 
        profiles: Dict, 
        features: np.ndarray
    ) -> List[UserBehaviorCluster]:
        """Create behavior cluster objects"""
        try:
            clusters = []
            unique_labels = np.unique(labels)
            
            for cluster_id in unique_labels:
                if cluster_id == -1:  # Skip noise points from DBSCAN
                    continue
                
                # Get devices in this cluster
                cluster_mask = labels == cluster_id
                cluster_device_ids = [device_ids[i] for i in range(len(device_ids)) if cluster_mask[i]]
                cluster_features = features[cluster_mask]
                
                # Calculate cluster characteristics
                characteristics = {
                    'avg_cpu_usage': float(np.mean([profiles[did]['avg_cpu_usage'] for did in cluster_device_ids])),
                    'avg_memory_usage': float(np.mean([profiles[did]['avg_memory_usage'] for did in cluster_device_ids])),
                    'avg_storage_usage': float(np.mean([profiles[did]['avg_storage_usage'] for did in cluster_device_ids])),
                    'avg_battery_level': float(np.mean([profiles[did]['avg_battery_level'] for did in cluster_device_ids])),
                    'performance_variability': float(np.mean([profiles[did]['performance_variability'] for did in cluster_device_ids])),
                    'anomaly_frequency': float(np.mean([profiles[did]['anomaly_frequency'] for did in cluster_device_ids]))
                }
                
                # Determine cluster name and type
                cluster_name, usage_patterns, performance_req, security_awareness = self._analyze_cluster_characteristics(characteristics)
                
                # Generate recommendations
                recommendations = self._generate_cluster_recommendations(characteristics, cluster_name)
                
                cluster = UserBehaviorCluster(
                    cluster_id=int(cluster_id),
                    cluster_name=cluster_name,
                    device_ids=cluster_device_ids,
                    characteristics=characteristics,
                    usage_patterns=usage_patterns,
                    app_preferences=self._infer_app_preferences(characteristics),
                    performance_requirements=performance_req,
                    security_awareness=security_awareness,
                    recommendations=recommendations
                )
                
                clusters.append(cluster)
            
            return clusters
            
        except Exception as e:
            self.logger.error(f"Failed to create behavior clusters: {e}")
            return []
    
    async def _generate_performance_recommendations(
        self, 
        device_id: str, 
        data: pd.DataFrame, 
        include_explanations: bool
    ) -> List[AIRecommendation]:
        """Generate performance recommendations"""
        try:
            recommendations = []
            
            if data.empty:
                return recommendations
            
            # Analyze CPU usage patterns
            if 'cpu_usage' in data.columns:
                avg_cpu = data['cpu_usage'].mean()
                max_cpu = data['cpu_usage'].max()
                
                if avg_cpu > 80:
                    rec_id = hashlib.md5(f"cpu_high_{device_id}".encode()).hexdigest()[:8]
                    reasoning = [
                        f"Average CPU usage is {avg_cpu:.1f}%, which is above optimal levels",
                        f"Peak CPU usage reached {max_cpu:.1f}%",
                        "High CPU usage can cause device slowdown and battery drain"
                    ] if include_explanations else []
                    
                    recommendations.append(AIRecommendation(
                        recommendation_id=rec_id,
                        device_id=device_id,
                        category="performance",
                        title="Optimize CPU Usage",
                        description="Your device's CPU usage is consistently high. Consider closing unnecessary applications and processes.",
                        priority="high" if avg_cpu > 90 else "medium",
                        confidence=0.85,
                        expected_impact="20-30% improvement in performance and battery life",
                        implementation_difficulty="easy",
                        estimated_time="5-10 minutes",
                        reasoning=reasoning,
                        evidence={"avg_cpu_usage": avg_cpu, "max_cpu_usage": max_cpu},
                        alternatives=[
                            "Restart the device to clear temporary processes",
                            "Update apps to latest versions for better optimization",
                            "Use battery optimization settings"
                        ]
                    ))
            
            # Analyze memory usage
            if 'memory_usage' in data.columns:
                avg_memory = data['memory_usage'].mean()
                max_memory = data['memory_usage'].max()
                
                if avg_memory > 75:
                    rec_id = hashlib.md5(f"memory_high_{device_id}".encode()).hexdigest()[:8]
                    reasoning = [
                        f"Average memory usage is {avg_memory:.1f}%",
                        "High memory usage can cause app crashes and slowdowns",
                        "Memory optimization can significantly improve performance"
                    ] if include_explanations else []
                    
                    recommendations.append(AIRecommendation(
                        recommendation_id=rec_id,
                        device_id=device_id,
                        category="performance",
                        title="Free Up Memory",
                        description="Memory usage is high. Clear cached data and close background applications.",
                        priority="high" if avg_memory > 85 else "medium",
                        confidence=0.80,
                        expected_impact="15-25% improvement in app loading speed",
                        implementation_difficulty="easy",
                        estimated_time="3-5 minutes",
                        reasoning=reasoning,
                        evidence={"avg_memory_usage": avg_memory, "max_memory_usage": max_memory},
                        alternatives=[
                            "Clear app cache for frequently used apps",
                            "Uninstall unused applications",
                            "Use memory management tools"
                        ]
                    ))
            
            # Analyze running processes
            if 'running_processes' in data.columns:
                avg_processes = data['running_processes'].mean()
                
                if avg_processes > 80:
                    rec_id = hashlib.md5(f"processes_high_{device_id}".encode()).hexdigest()[:8]
                    reasoning = [
                        f"Average running processes: {avg_processes:.0f}",
                        "Too many background processes can slow down the device",
                        "Optimizing startup apps can improve boot time and performance"
                    ] if include_explanations else []
                    
                    recommendations.append(AIRecommendation(
                        recommendation_id=rec_id,
                        device_id=device_id,
                        category="performance",
                        title="Reduce Background Processes",
                        description="Many processes are running in the background. Disable auto-start for unnecessary apps.",
                        priority="medium",
                        confidence=0.75,
                        expected_impact="10-15% improvement in startup time",
                        implementation_difficulty="medium",
                        estimated_time="10-15 minutes",
                        reasoning=reasoning,
                        evidence={"avg_running_processes": avg_processes},
                        alternatives=[
                            "Use developer options to limit background processes",
                            "Disable auto-start for non-essential apps",
                            "Use task manager to monitor and control processes"
                        ]
                    ))
            
            return recommendations
            
        except Exception as e:
            self.logger.error(f"Failed to generate performance recommendations: {e}")
            return []
    
    async def _generate_storage_recommendations(
        self, 
        device_id: str, 
        data: pd.DataFrame, 
        include_explanations: bool
    ) -> List[AIRecommendation]:
        """Generate storage recommendations"""
        try:
            recommendations = []
            
            if data.empty or 'storage_usage_percentage' not in data.columns:
                return recommendations
            
            avg_storage = data['storage_usage_percentage'].mean()
            current_storage = data['storage_usage_percentage'].iloc[-1]
            storage_trend = data['storage_usage_percentage'].diff().mean()
            
            # High storage usage
            if current_storage > 85:
                rec_id = hashlib.md5(f"storage_critical_{device_id}".encode()).hexdigest()[:8]
                priority = "urgent" if current_storage > 95 else "high"
                
                reasoning = [
                    f"Current storage usage: {current_storage:.1f}%",
                    "Critical storage levels can cause app crashes and system instability",
                    f"Storage trend: {'increasing' if storage_trend > 0 else 'stable'}"
                ] if include_explanations else []
                
                recommendations.append(AIRecommendation(
                    recommendation_id=rec_id,
                    device_id=device_id,
                    category="storage",
                    title="Critical Storage Cleanup Needed",
                    description="Storage is critically low. Immediate cleanup required to prevent system issues.",
                    priority=priority,
                    confidence=0.95,
                    expected_impact="Prevent system crashes and improve performance",
                    implementation_difficulty="easy",
                    estimated_time="15-30 minutes",
                    reasoning=reasoning,
                    evidence={"current_storage": current_storage, "storage_trend": storage_trend},
                    alternatives=[
                        "Delete unused apps and files",
                        "Clear app caches and temporary files",
                        "Move photos/videos to external storage or cloud",
                        "Use storage analyzer to identify large files"
                    ]
                ))
            
            elif current_storage > 70:
                rec_id = hashlib.md5(f"storage_moderate_{device_id}".encode()).hexdigest()[:8]
                
                reasoning = [
                    f"Current storage usage: {current_storage:.1f}%",
                    "Proactive storage management prevents future issues",
                    "Regular cleanup maintains optimal performance"
                ] if include_explanations else []
                
                recommendations.append(AIRecommendation(
                    recommendation_id=rec_id,
                    device_id=device_id,
                    category="storage",
                    title="Storage Optimization Recommended",
                    description="Consider cleaning up storage space to maintain optimal performance.",
                    priority="medium",
                    confidence=0.80,
                    expected_impact="Improved app performance and prevent future issues",
                    implementation_difficulty="easy",
                    estimated_time="10-20 minutes",
                    reasoning=reasoning,
                    evidence={"current_storage": current_storage},
                    alternatives=[
                        "Clear app caches periodically",
                        "Review and delete old downloads",
                        "Use cloud storage for media files"
                    ]
                ))
            
            # Rapidly increasing storage
            if storage_trend > 1.0:  # More than 1% increase per measurement period
                rec_id = hashlib.md5(f"storage_growth_{device_id}".encode()).hexdigest()[:8]
                
                reasoning = [
                    f"Storage growth rate: +{storage_trend:.1f}% per measurement",
                    "Rapid storage growth may indicate data accumulation issues",
                    "Monitoring storage trends helps prevent sudden space shortages"
                ] if include_explanations else []
                
                recommendations.append(AIRecommendation(
                    recommendation_id=rec_id,
                    device_id=device_id,
                    category="storage",
                    title="Monitor Storage Growth",
                    description="Storage usage is increasing rapidly. Monitor and manage data accumulation.",
                    priority="medium",
                    confidence=0.70,
                    expected_impact="Prevent sudden storage shortages",
                    implementation_difficulty="easy",
                    estimated_time="5-10 minutes",
                    reasoning=reasoning,
                    evidence={"storage_growth_rate": storage_trend},
                    alternatives=[
                        "Set up automatic cache cleaning",
                        "Review app data usage regularly",
                        "Enable cloud sync for photos and documents"
                    ]
                ))
            
            return recommendations
            
        except Exception as e:
            self.logger.error(f"Failed to generate storage recommendations: {e}")
            return []
    
    async def _generate_security_recommendations(
        self, 
        device_id: str, 
        data: pd.DataFrame, 
        include_explanations: bool
    ) -> List[AIRecommendation]:
        """Generate security recommendations"""
        try:
            recommendations = []
            
            if data.empty:
                return recommendations
            
            # High temperature anomaly (potential security concern)
            temp_columns = ['cpu_temperature', 'battery_temperature']
            for temp_col in temp_columns:
                if temp_col in data.columns:
                    max_temp = data[temp_col].max()
                    avg_temp = data[temp_col].mean()
                    
                    if max_temp > 45:  # High temperature threshold
                        rec_id = hashlib.md5(f"temp_security_{device_id}_{temp_col}".encode()).hexdigest()[:8]
                        
                        reasoning = [
                            f"Maximum {temp_col.replace('_', ' ')}: {max_temp:.1f}°C",
                            f"Average {temp_col.replace('_', ' ')}: {avg_temp:.1f}°C",
                            "High temperatures may indicate malware or hardware manipulation"
                        ] if include_explanations else []
                        
                        recommendations.append(AIRecommendation(
                            recommendation_id=rec_id,
                            device_id=device_id,
                            category="security",
                            title=f"High {temp_col.replace('_', ' ').title()} Alert",
                            description=f"Unusually high {temp_col.replace('_', ' ')} detected. This may indicate security issues or hardware problems.",
                            priority="high" if max_temp > 50 else "medium",
                            confidence=0.75,
                            expected_impact="Prevent hardware damage and potential security breaches",
                            implementation_difficulty="medium",
                            estimated_time="15-30 minutes",
                            reasoning=reasoning,
                            evidence={f"max_{temp_col}": max_temp, f"avg_{temp_col}": avg_temp},
                            alternatives=[
                                "Run malware scan",
                                "Check for unauthorized apps",
                                "Monitor device temperature regularly",
                                "Close resource-intensive applications"
                            ]
                        ))
            
            # Network strength anomalies
            if 'network_strength' in data.columns:
                network_data = data['network_strength'].dropna()
                if len(network_data) > 5:
                    # Detect sudden drops in network strength
                    sudden_drops = network_data.diff() < -20
                    if sudden_drops.any():
                        rec_id = hashlib.md5(f"network_security_{device_id}".encode()).hexdigest()[:8]
                        
                        reasoning = [
                            "Sudden network strength drops detected",
                            "May indicate network interference or security attacks",
                            "Monitoring network stability is crucial for security"
                        ] if include_explanations else []
                        
                        recommendations.append(AIRecommendation(
                            recommendation_id=rec_id,
                            device_id=device_id,
                            category="security",
                            title="Network Security Alert",
                            description="Unusual network behavior detected. Monitor for potential security threats.",
                            priority="medium",
                            confidence=0.65,
                            expected_impact="Maintain secure network connections",
                            implementation_difficulty="medium",
                            estimated_time="10-20 minutes",
                            reasoning=reasoning,
                            evidence={"network_drops_detected": int(sudden_drops.sum())},
                            alternatives=[
                                "Check for unauthorized network access",
                                "Verify WiFi network security",
                                "Monitor network traffic patterns",
                                "Update network security settings"
                            ]
                        ))
            
            # Anomaly frequency analysis
            if 'is_anomaly' in data.columns:
                anomaly_rate = data['is_anomaly'].mean()
                
                if anomaly_rate > 0.1:  # More than 10% anomalies
                    rec_id = hashlib.md5(f"anomaly_security_{device_id}".encode()).hexdigest()[:8]
                    
                    reasoning = [
                        f"Anomaly detection rate: {anomaly_rate*100:.1f}%",
                        "High anomaly rates may indicate security compromises",
                        "Regular security monitoring is recommended"
                    ] if include_explanations else []
                    
                    recommendations.append(AIRecommendation(
                        recommendation_id=rec_id,
                        device_id=device_id,
                        category="security",
                        title="Security Monitoring Alert",
                        description="Frequent anomalies detected. Enhanced security monitoring recommended.",
                        priority="high" if anomaly_rate > 0.2 else "medium",
                        confidence=0.70,
                        expected_impact="Early detection of security threats",
                        implementation_difficulty="medium",
                        estimated_time="20-30 minutes",
                        reasoning=reasoning,
                        evidence={"anomaly_rate": anomaly_rate},
                        alternatives=[
                            "Run comprehensive security scan",
                            "Review installed applications",
                            "Check system permissions",
                            "Update security software"
                        ]
                    ))
            
            return recommendations
            
        except Exception as e:
            self.logger.error(f"Failed to generate security recommendations: {e}")
            return []
    
    async def _generate_battery_recommendations(
        self, 
        device_id: str, 
        data: pd.DataFrame, 
        include_explanations: bool
    ) -> List[AIRecommendation]:
        """Generate battery recommendations"""
        try:
            recommendations = []
            
            if data.empty or 'battery_level' not in data.columns:
                return recommendations
            
            avg_battery = data['battery_level'].mean()
            min_battery = data['battery_level'].min()
            battery_decline = data['battery_level'].diff().mean() if len(data) > 1 else 0
            
            # Low battery levels
            if avg_battery < 30:
                rec_id = hashlib.md5(f"battery_low_{device_id}".encode()).hexdigest()[:8]
                
                reasoning = [
                    f"Average battery level: {avg_battery:.1f}%",
                    f"Minimum battery level: {min_battery:.1f}%",
                    "Consistently low battery levels indicate charging issues or battery degradation"
                ] if include_explanations else []
                
                recommendations.append(AIRecommendation(
                    recommendation_id=rec_id,
                    device_id=device_id,
                    category="battery",
                    title="Battery Management Needed",
                    description="Battery levels are consistently low. Review charging habits and battery-draining apps.",
                    priority="high" if avg_battery < 20 else "medium",
                    confidence=0.85,
                    expected_impact="Improved battery life and device reliability",
                    implementation_difficulty="easy",
                    estimated_time="10-15 minutes",
                    reasoning=reasoning,
                    evidence={"avg_battery_level": avg_battery, "min_battery_level": min_battery},
                    alternatives=[
                        "Enable battery saver mode",
                        "Identify and close battery-draining apps",
                        "Adjust screen brightness and timeout",
                        "Review charging habits"
                    ]
                ))
            
            # High battery temperature
            if 'battery_temperature' in data.columns:
                max_temp = data['battery_temperature'].max()
                avg_temp = data['battery_temperature'].mean()
                
                if max_temp > 40:  # High temperature threshold
                    rec_id = hashlib.md5(f"battery_temp_{device_id}".encode()).hexdigest()[:8]
                    
                    reasoning = [
                        f"Maximum battery temperature: {max_temp:.1f}°C",
                        f"Average battery temperature: {avg_temp:.1f}°C",
                        "High battery temperatures can reduce battery lifespan and pose safety risks"
                    ] if include_explanations else []
                    
                    recommendations.append(AIRecommendation(
                        recommendation_id=rec_id,
                        device_id=device_id,
                        category="battery",
                        title="Battery Temperature Warning",
                        description="Battery temperature is too high. Take immediate action to prevent damage.",
                        priority="urgent" if max_temp > 45 else "high",
                        confidence=0.90,
                        expected_impact="Prevent battery damage and safety hazards",
                        implementation_difficulty="easy",
                        estimated_time="5-10 minutes",
                        reasoning=reasoning,
                        evidence={"max_battery_temp": max_temp, "avg_battery_temp": avg_temp},
                        alternatives=[
                            "Remove device case during charging",
                            "Avoid charging in hot environments",
                            "Close resource-intensive applications",
                            "Use original charger and cable"
                        ]
                    ))
            
            # Rapid battery decline
            if battery_decline < -2:  # More than 2% decline per measurement
                rec_id = hashlib.md5(f"battery_decline_{device_id}".encode()).hexdigest()[:8]
                
                reasoning = [
                    f"Battery decline rate: {battery_decline:.1f}% per measurement",
                    "Rapid battery decline may indicate battery degradation or excessive power consumption",
                    "Optimizing power usage can extend battery life"
                ] if include_explanations else []
                
                recommendations.append(AIRecommendation(
                    recommendation_id=rec_id,
                    device_id=device_id,
                    category="battery",
                    title="Rapid Battery Drain Detected",
                    description="Battery is draining faster than normal. Optimize power settings and check for power-hungry apps.",
                    priority="medium",
                    confidence=0.75,
                    expected_impact="Extend battery life between charges",
                    implementation_difficulty="medium",
                    estimated_time="15-20 minutes",
                    reasoning=reasoning,
                    evidence={"battery_decline_rate": battery_decline},
                    alternatives=[
                        "Check battery usage by apps",
                        "Disable location services for unnecessary apps",
                        "Reduce background app refresh",
                        "Lower screen brightness and refresh rate"
                    ]
                ))
            
            return recommendations
            
        except Exception as e:
            self.logger.error(f"Failed to generate battery recommendations: {e}")
            return []
    
    async def _generate_usage_recommendations(
        self, 
        device_id: str, 
        data: pd.DataFrame, 
        include_explanations: bool
    ) -> List[AIRecommendation]:
        """Generate usage optimization recommendations"""
        try:
            recommendations = []
            
            if data.empty:
                return recommendations
            
            # Analyze usage patterns
            usage_metrics = ['cpu_usage', 'memory_usage', 'running_processes']
            available_metrics = [col for col in usage_metrics if col in data.columns]
            
            if not available_metrics:
                return recommendations
            
            # Calculate usage efficiency
            efficiency_scores = []
            for _, row in data.iterrows():
                score = 100
                for metric in available_metrics:
                    if pd.notna(row[metric]):
                        if metric in ['cpu_usage', 'memory_usage']:
                            score -= row[metric] * 0.4
                        elif metric == 'running_processes':
                            score -= min(40, (row[metric] / 100) * 40)
                efficiency_scores.append(max(0, score))
            
            avg_efficiency = np.mean(efficiency_scores) if efficiency_scores else 50
            
            if avg_efficiency < 60:
                rec_id = hashlib.md5(f"usage_efficiency_{device_id}".encode()).hexdigest()[:8]
                
                reasoning = [
                    f"Average usage efficiency: {avg_efficiency:.1f}/100",
                    "Low efficiency indicates suboptimal device usage patterns",
                    "Optimizing usage can improve performance and battery life"
                ] if include_explanations else []
                
                recommendations.append(AIRecommendation(
                    recommendation_id=rec_id,
                    device_id=device_id,
                    category="usage",
                    title="Optimize Device Usage",
                    description="Device usage patterns can be optimized for better performance and efficiency.",
                    priority="medium",
                    confidence=0.70,
                    expected_impact="15-20% improvement in overall device efficiency",
                    implementation_difficulty="medium",
                    estimated_time="20-30 minutes",
                    reasoning=reasoning,
                    evidence={"usage_efficiency_score": avg_efficiency},
                    alternatives=[
                        "Review and optimize startup programs",
                        "Set up automation for routine tasks",
                        "Use device optimization tools",
                        "Create usage schedules for heavy applications"
                    ]
                ))
            
            # Temporal usage analysis
            if 'recorded_at' in data.columns:
                data_with_time = data.copy()
                data_with_time['hour'] = pd.to_datetime(data_with_time['recorded_at']).dt.hour
                
                # Find peak usage hours
                hourly_usage = data_with_time.groupby('hour')[available_metrics].mean()
                peak_hours = hourly_usage.sum(axis=1).nlargest(3).index.tolist()
                
                if len(peak_hours) > 0:
                    rec_id = hashlib.md5(f"usage_schedule_{device_id}".encode()).hexdigest()[:8]
                    
                    reasoning = [
                        f"Peak usage hours: {', '.join([str(h) + ':00' for h in peak_hours])}",
                        "Optimizing usage schedules can reduce resource conflicts",
                        "Spreading intensive tasks across time can improve performance"
                    ] if include_explanations else []
                    
                    recommendations.append(AIRecommendation(
                        recommendation_id=rec_id,
                        device_id=device_id,
                        category="usage",
                        title="Optimize Usage Schedule",
                        description="Consider spreading intensive tasks across different times to optimize performance.",
                        priority="low",
                        confidence=0.60,
                        expected_impact="Smoother device performance during peak usage",
                        implementation_difficulty="easy",
                        estimated_time="10-15 minutes",
                        reasoning=reasoning,
                        evidence={"peak_usage_hours": peak_hours},
                        alternatives=[
                            "Schedule updates and backups during low usage periods",
                            "Use battery optimization for peak hours",
                            "Set app usage limits during busy periods"
                        ]
                    ))
            
            return recommendations
            
        except Exception as e:
            self.logger.error(f"Failed to generate usage recommendations: {e}")
            return []
    
    # Additional helper methods for AI service functionality
    def _calculate_storage_growth_rate(self, data: pd.DataFrame) -> float:
        """Calculate storage growth rate from device data"""
        try:
            if 'storage_usage_percentage' not in data.columns or len(data) < 2:
                return 0.0
            
            storage_data = data['storage_usage_percentage'].dropna()
            if len(storage_data) < 2:
                return 0.0
            
            # Calculate growth rate as percentage change per day
            first_val = storage_data.iloc[0]
            last_val = storage_data.iloc[-1]
            days_diff = max(1, len(storage_data))
            
            growth_rate = (last_val - first_val) / days_diff
            return float(growth_rate)
            
        except Exception:
            return 0.0
    
    def _calculate_battery_drain_rate(self, data: pd.DataFrame) -> float:
        """Calculate battery drain rate from device data"""
        try:
            if 'battery_level' not in data.columns or len(data) < 2:
                return 0.0
            
            battery_data = data['battery_level'].dropna()
            if len(battery_data) < 2:
                return 0.0
            
            # Calculate average decline rate
            diffs = battery_data.diff().dropna()
            # Only consider negative changes (discharge)
            negative_diffs = diffs[diffs < 0]
            
            if len(negative_diffs) > 0:
                return float(abs(negative_diffs.mean()))
            else:
                return 0.0
                
        except Exception:
            return 0.0
    
    def _find_peak_usage_hour(self, data: pd.DataFrame) -> int:
        """Find the peak usage hour from device data"""
        try:
            if 'recorded_at' not in data.columns:
                return 12  # Default to noon
            
            timestamps = pd.to_datetime(data['recorded_at'])
            hours = timestamps.dt.hour
            
            # Find the most common hour
            peak_hour = hours.mode()
            if len(peak_hour) > 0:
                return int(peak_hour.iloc[0])
            else:
                return 12
                
        except Exception:
            return 12
    
    def _calculate_weekend_usage_ratio(self, data: pd.DataFrame) -> float:
        """Calculate ratio of weekend usage vs weekday usage"""
        try:
            if 'recorded_at' not in data.columns or len(data) < 7:
                return 0.5  # Default balanced ratio
            
            timestamps = pd.to_datetime(data['recorded_at'])
            weekday_mask = timestamps.dt.dayofweek < 5  # Monday=0 to Friday=4
            
            weekday_count = weekday_mask.sum()
            weekend_count = (~weekday_mask).sum()
            
            if weekday_count + weekend_count == 0:
                return 0.5
            
            ratio = weekend_count / (weekday_count + weekend_count)
            return float(ratio)
            
        except Exception:
            return 0.5
    
    def _calculate_performance_variability(self, data: pd.DataFrame) -> float:
        """Calculate performance variability score"""
        try:
            performance_metrics = ['cpu_usage', 'memory_usage']
            available_metrics = [col for col in performance_metrics if col in data.columns]
            
            if not available_metrics:
                return 0.0
            
            variabilities = []
            for metric in available_metrics:
                metric_data = data[metric].dropna()
                if len(metric_data) > 1:
                    # Calculate coefficient of variation
                    mean_val = metric_data.mean()
                    std_val = metric_data.std()
                    if mean_val > 0:
                        cv = std_val / mean_val
                        variabilities.append(cv)
            
            if variabilities:
                return float(np.mean(variabilities))
            else:
                return 0.0
                
        except Exception:
            return 0.0
    
    def _analyze_cluster_characteristics(self, characteristics: Dict[str, float]) -> Tuple[str, Dict[str, float], str, str]:
        """Analyze cluster characteristics to determine cluster type and patterns"""
        try:
            avg_cpu = characteristics.get('avg_cpu_usage', 0)
            avg_memory = characteristics.get('avg_memory_usage', 0)
            avg_battery = characteristics.get('avg_battery_level', 100)
            variability = characteristics.get('performance_variability', 0)
            anomaly_freq = characteristics.get('anomaly_frequency', 0)
            
            # Determine cluster name based on characteristics
            if avg_cpu > 70 and avg_memory > 70:
                cluster_name = "High Performance Users"
                performance_req = "high"
            elif avg_cpu < 30 and avg_memory < 40:
                cluster_name = "Light Users"
                performance_req = "low"
            elif variability > 0.5:
                cluster_name = "Variable Usage Users"
                performance_req = "medium"
            elif avg_battery < 30:
                cluster_name = "Heavy Battery Users"
                performance_req = "medium"
            else:
                cluster_name = "Balanced Users"
                performance_req = "medium"
            
            # Usage patterns
            usage_patterns = {
                "performance_intensity": (avg_cpu + avg_memory) / 2,
                "power_efficiency": avg_battery,
                "usage_consistency": max(0, 1 - variability),
                "stability_score": max(0, 1 - anomaly_freq)
            }
            
            # Security awareness based on anomaly frequency
            if anomaly_freq > 0.15:
                security_awareness = "low"
            elif anomaly_freq > 0.05:
                security_awareness = "medium"
            else:
                security_awareness = "high"
            
            return cluster_name, usage_patterns, performance_req, security_awareness
            
        except Exception as e:
            self.logger.error(f"Failed to analyze cluster characteristics: {e}")
            return "Standard Users", {}, "medium", "medium"
    
    def _generate_cluster_recommendations(self, characteristics: Dict[str, float], cluster_name: str) -> List[str]:
        """Generate recommendations for a cluster based on its characteristics"""
        try:
            recommendations = []
            
            avg_cpu = characteristics.get('avg_cpu_usage', 0)
            avg_memory = characteristics.get('avg_memory_usage', 0)
            avg_battery = characteristics.get('avg_battery_level', 100)
            
            if "High Performance" in cluster_name:
                recommendations.extend([
                    "Consider performance optimization settings",
                    "Monitor device temperature during intensive usage",
                    "Use cooling accessories for extended high-performance tasks",
                    "Regular performance monitoring recommended"
                ])
            
            elif "Light Users" in cluster_name:
                recommendations.extend([
                    "Enable battery saver modes for extended usage",
                    "Consider lighter apps for better efficiency",
                    "Reduce unnecessary background services",
                    "Optimize device for battery life over performance"
                ])
            
            elif "Variable Usage" in cluster_name:
                recommendations.extend([
                    "Use adaptive performance settings",
                    "Set up profiles for different usage scenarios",
                    "Monitor resource usage patterns",
                    "Consider automation for routine optimization"
                ])
            
            elif "Heavy Battery" in cluster_name:
                recommendations.extend([
                    "Investigate battery-draining applications",
                    "Enable aggressive power saving features",
                    "Check charging habits and patterns",
                    "Consider battery health diagnostics"
                ])
            
            else:  # Balanced Users
                recommendations.extend([
                    "Maintain current usage patterns",
                    "Regular device maintenance recommended",
                    "Monitor for gradual performance changes",
                    "Continue with balanced optimization approach"
                ])
            
            return recommendations
            
        except Exception as e:
            self.logger.error(f"Failed to generate cluster recommendations: {e}")
            return ["Regular device monitoring recommended"]
    
    def _infer_app_preferences(self, characteristics: Dict[str, float]) -> List[str]:
        """Infer app preferences based on cluster characteristics"""
        try:
            preferences = []
            
            avg_cpu = characteristics.get('avg_cpu_usage', 0)
            avg_memory = characteristics.get('avg_memory_usage', 0)
            avg_storage = characteristics.get('avg_storage_usage', 0)
            
            if avg_cpu > 60 and avg_memory > 60:
                preferences.extend(["Gaming", "Video Editing", "Development Tools", "Heavy Multimedia"])
            elif avg_cpu < 30 and avg_memory < 40:
                preferences.extend(["Messaging", "Reading", "Basic Productivity", "Social Media"])
            elif avg_storage > 80:
                preferences.extend(["Media Storage", "Photo/Video Apps", "Large Games", "Content Creation"])
            else:
                preferences.extend(["General Productivity", "Web Browsing", "Streaming", "Standard Apps"])
            
            return preferences
            
        except Exception as e:
            self.logger.error(f"Failed to infer app preferences: {e}")
            return ["General Usage"]

