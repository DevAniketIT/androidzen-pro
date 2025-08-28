"""
Unit tests for AI Service module.
"""

import pytest
import numpy as np
import pandas as pd
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta
from sklearn.ensemble import IsolationForest

from backend.services.intelligence_service import (
    AIService,
    ModelInfo,
    PredictiveMaintenance,
    AnomalyDetection,
    UserBehaviorCluster,
    AIRecommendation,
    DeviceFeatureExtractor
)


@pytest.mark.unit
class TestAIService:
    """Test cases for AI Service."""

    @pytest.fixture
    def ai_service(self):
        """Create AI service instance for testing."""
        return AIService()

    @pytest.fixture
    def sample_analytics_data(self):
        """Sample analytics data for testing."""
        data = []
        for i in range(100):
            data.append({
                'device_id': f'device_{i % 3}',
                'cpu_usage': np.random.normal(50, 15),
                'memory_usage': np.random.normal(60, 10),
                'storage_usage_percentage': np.random.normal(70, 20),
                'battery_level': np.random.randint(20, 100),
                'battery_temperature': np.random.normal(30, 5),
                'cpu_temperature': np.random.normal(40, 8),
                'network_strength': np.random.randint(-80, -30),
                'running_processes': np.random.randint(80, 150),
                'recorded_at': datetime.now() - timedelta(days=np.random.randint(0, 30))
            })
        return pd.DataFrame(data)

    async def test_initialize_models(self, ai_service):
        """Test AI service model initialization."""
        with patch.object(ai_service, '_load_existing_models'), \
             patch.object(ai_service, '_create_default_models'):
            
            await ai_service.initialize_models()
            
            assert ai_service.is_initialized
            assert len(ai_service.models) > 0

    async def test_detect_anomalies_success(self, ai_service, sample_analytics_data):
        """Test successful anomaly detection."""
        device_id = "device_0"
        
        # Mock database queries
        with patch.object(ai_service, '_get_device_analytics') as mock_get_analytics, \
             patch.object(ai_service, '_get_device_baseline') as mock_get_baseline:
            
            mock_get_analytics.return_value = sample_analytics_data[
                sample_analytics_data['device_id'] == device_id
            ]
            mock_get_baseline.return_value = {
                'cpu_usage': 45.0,
                'memory_usage': 60.0,
                'battery_temperature': 30.0
            }
            
            # Initialize models
            await ai_service.initialize_models()
            
            anomalies = await ai_service.detect_anomalies(device_id)
            
            assert isinstance(anomalies, list)
            # Check that all returned items are AnomalyDetection objects
            for anomaly in anomalies:
                assert isinstance(anomaly, AnomalyDetection)
                assert anomaly.device_id == device_id
                assert hasattr(anomaly, 'anomaly_score')
                assert hasattr(anomaly, 'severity')

    async def test_detect_anomalies_no_data(self, ai_service):
        """Test anomaly detection with no data."""
        device_id = "nonexistent_device"
        
        with patch.object(ai_service, '_get_device_analytics') as mock_get_analytics:
            mock_get_analytics.return_value = pd.DataFrame()
            
            anomalies = await ai_service.detect_anomalies(device_id)
            
            assert anomalies == []

    async def test_predict_maintenance(self, ai_service, sample_analytics_data):
        """Test predictive maintenance functionality."""
        device_id = "device_0"
        
        with patch.object(ai_service, '_get_device_analytics') as mock_get_analytics, \
             patch.object(ai_service, '_get_storage_trends') as mock_get_trends:
            
            mock_get_analytics.return_value = sample_analytics_data[
                sample_analytics_data['device_id'] == device_id
            ]
            mock_get_trends.return_value = [
                {'timestamp': datetime.now(), 'used_space': 70000},
                {'timestamp': datetime.now() - timedelta(days=1), 'used_space': 69000},
            ]
            
            await ai_service.initialize_models()
            
            predictions = await ai_service.predict_maintenance(device_id)
            
            assert isinstance(predictions, list)
            for prediction in predictions:
                assert isinstance(prediction, PredictiveMaintenance)
                assert prediction.device_id == device_id
                assert prediction.component in ['storage', 'battery', 'performance', 'memory']
                assert 0 <= prediction.confidence <= 1
                assert 0 <= prediction.current_health <= 100

    async def test_analyze_user_behavior(self, ai_service, sample_analytics_data):
        """Test user behavior analysis."""
        with patch.object(ai_service, '_get_all_device_analytics') as mock_get_analytics:
            mock_get_analytics.return_value = sample_analytics_data
            
            await ai_service.initialize_models()
            
            clusters = await ai_service.analyze_user_behavior()
            
            assert isinstance(clusters, list)
            for cluster in clusters:
                assert isinstance(cluster, UserBehaviorCluster)
                assert isinstance(cluster.device_ids, list)
                assert isinstance(cluster.characteristics, dict)
                assert len(cluster.device_ids) > 0

    async def test_generate_recommendations(self, ai_service, sample_analytics_data):
        """Test AI recommendation generation."""
        device_id = "device_0"
        
        with patch.object(ai_service, '_get_device_analytics') as mock_get_analytics, \
             patch.object(ai_service, 'detect_anomalies') as mock_detect_anomalies, \
             patch.object(ai_service, 'predict_maintenance') as mock_predict_maintenance:
            
            mock_get_analytics.return_value = sample_analytics_data[
                sample_analytics_data['device_id'] == device_id
            ]
            
            mock_detect_anomalies.return_value = [
                AnomalyDetection(
                    device_id=device_id,
                    timestamp=datetime.now(),
                    anomaly_type="high_cpu",
                    severity="medium",
                    anomaly_score=0.8,
                    confidence=0.9,
                    affected_metrics=['cpu_usage'],
                    baseline_values={'cpu_usage': 45.0},
                    actual_values={'cpu_usage': 85.0},
                    deviation_percentage=88.9,
                    context={},
                    explanation="CPU usage significantly above normal"
                )
            ]
            
            mock_predict_maintenance.return_value = [
                PredictiveMaintenance(
                    device_id=device_id,
                    component="storage",
                    prediction_type="optimization",
                    predicted_date=datetime.now() + timedelta(days=30),
                    confidence=0.8,
                    risk_level="medium",
                    current_health=75.0,
                    predicted_health=65.0,
                    recommendations=["Clear cache", "Uninstall unused apps"],
                    maintenance_actions=["storage_cleanup"],
                    time_to_action=30
                )
            ]
            
            await ai_service.initialize_models()
            
            recommendations = await ai_service.generate_recommendations(device_id)
            
            assert isinstance(recommendations, list)
            for recommendation in recommendations:
                assert isinstance(recommendation, AIRecommendation)
                assert recommendation.device_id == device_id
                assert recommendation.category in [
                    'performance', 'storage', 'security', 'battery', 'usage'
                ]
                assert 0 <= recommendation.confidence <= 1

    def test_feature_extractor(self, sample_analytics_data):
        """Test device feature extractor."""
        extractor = DeviceFeatureExtractor()
        
        features = extractor.fit_transform(sample_analytics_data)
        
        assert isinstance(features, np.ndarray)
        assert features.shape[0] == len(sample_analytics_data)
        assert features.shape[1] > 0

    def test_feature_extractor_without_temporal(self, sample_analytics_data):
        """Test feature extractor without temporal features."""
        extractor = DeviceFeatureExtractor(include_temporal_features=False)
        
        features = extractor.fit_transform(sample_analytics_data)
        
        assert isinstance(features, np.ndarray)
        assert features.shape[0] == len(sample_analytics_data)

    async def test_train_anomaly_model(self, ai_service, sample_analytics_data):
        """Test anomaly model training."""
        with patch.object(ai_service, '_get_all_device_analytics') as mock_get_analytics:
            mock_get_analytics.return_value = sample_analytics_data
            
            model_info = await ai_service.train_anomaly_model()
            
            assert isinstance(model_info, ModelInfo)
            assert model_info.model_type == "anomaly"
            assert model_info.training_samples > 0

    async def test_train_predictive_model(self, ai_service, sample_analytics_data):
        """Test predictive model training."""
        with patch.object(ai_service, '_get_all_device_analytics') as mock_get_analytics, \
             patch.object(ai_service, '_get_maintenance_history') as mock_get_history:
            
            mock_get_analytics.return_value = sample_analytics_data
            mock_get_history.return_value = [
                {'device_id': 'device_0', 'component': 'storage', 'days_until_maintenance': 30},
                {'device_id': 'device_1', 'component': 'battery', 'days_until_maintenance': 45},
            ]
            
            model_info = await ai_service.train_predictive_model()
            
            assert isinstance(model_info, ModelInfo)
            assert model_info.model_type == "predictive"
            assert model_info.training_samples > 0

    async def test_update_models_automatic(self, ai_service, sample_analytics_data):
        """Test automatic model updates."""
        with patch.object(ai_service, '_should_update_models') as mock_should_update, \
             patch.object(ai_service, '_get_all_device_analytics') as mock_get_analytics, \
             patch.object(ai_service, 'train_anomaly_model') as mock_train_anomaly, \
             patch.object(ai_service, 'train_predictive_model') as mock_train_predictive:
            
            mock_should_update.return_value = True
            mock_get_analytics.return_value = sample_analytics_data
            mock_train_anomaly.return_value = ModelInfo(
                model_id="test_anomaly", model_type="anomaly", version="1.0",
                created_at=datetime.now()
            )
            mock_train_predictive.return_value = ModelInfo(
                model_id="test_predictive", model_type="predictive", version="1.0",
                created_at=datetime.now()
            )
            
            updated_models = await ai_service.update_models()
            
            assert isinstance(updated_models, list)
            assert len(updated_models) > 0
            mock_train_anomaly.assert_called_once()
            mock_train_predictive.assert_called_once()

    def test_model_info_creation(self):
        """Test ModelInfo dataclass creation."""
        model_info = ModelInfo(
            model_id="test_model",
            model_type="anomaly",
            version="1.0",
            created_at=datetime.now(),
            accuracy=0.85,
            precision=0.80,
            recall=0.90,
            f1_score=0.85
        )
        
        assert model_info.model_id == "test_model"
        assert model_info.model_type == "anomaly"
        assert model_info.version == "1.0"
        assert model_info.accuracy == 0.85

    def test_anomaly_detection_creation(self):
        """Test AnomalyDetection dataclass creation."""
        anomaly = AnomalyDetection(
            device_id="test_device",
            timestamp=datetime.now(),
            anomaly_type="high_cpu",
            severity="high",
            anomaly_score=0.9,
            confidence=0.85,
            affected_metrics=["cpu_usage"],
            baseline_values={"cpu_usage": 45.0},
            actual_values={"cpu_usage": 90.0},
            deviation_percentage=100.0,
            context={"time_of_day": "peak_hours"},
            explanation="CPU usage is significantly above normal baseline"
        )
        
        assert anomaly.device_id == "test_device"
        assert anomaly.anomaly_type == "high_cpu"
        assert anomaly.severity == "high"
        assert anomaly.anomaly_score == 0.9

    def test_predictive_maintenance_creation(self):
        """Test PredictiveMaintenance dataclass creation."""
        prediction = PredictiveMaintenance(
            device_id="test_device",
            component="storage",
            prediction_type="optimization",
            predicted_date=datetime.now() + timedelta(days=30),
            confidence=0.8,
            risk_level="medium",
            current_health=70.0,
            predicted_health=60.0,
            recommendations=["Clear cache", "Remove unused apps"],
            maintenance_actions=["storage_cleanup"],
            time_to_action=30
        )
        
        assert prediction.device_id == "test_device"
        assert prediction.component == "storage"
        assert prediction.risk_level == "medium"
        assert len(prediction.recommendations) == 2

    def test_ai_recommendation_creation(self):
        """Test AIRecommendation dataclass creation."""
        recommendation = AIRecommendation(
            recommendation_id="rec_001",
            device_id="test_device",
            category="performance",
            title="Optimize CPU Usage",
            description="Your device's CPU usage is higher than normal",
            priority="high",
            confidence=0.85,
            expected_impact="Improve performance by 20%",
            implementation_difficulty="easy",
            estimated_time="5 minutes",
            reasoning=["High CPU usage detected", "Background apps consuming resources"],
            evidence={"cpu_usage": 85.0, "baseline": 45.0},
            alternatives=["Restart device", "Update apps"]
        )
        
        assert recommendation.recommendation_id == "rec_001"
        assert recommendation.category == "performance"
        assert recommendation.priority == "high"
        assert len(recommendation.reasoning) == 2

    async def test_cleanup_old_models(self, ai_service):
        """Test cleanup of old models."""
        # Mock old models
        old_model = ModelInfo(
            model_id="old_model",
            model_type="anomaly",
            version="0.1",
            created_at=datetime.now() - timedelta(days=60)
        )
        ai_service.models["old_model"] = old_model
        
        with patch.object(ai_service, '_remove_model_files'):
            await ai_service.cleanup_old_models(max_age_days=30)
            
            assert "old_model" not in ai_service.models

    def test_model_versioning(self, ai_service):
        """Test model versioning functionality."""
        version = ai_service._generate_model_version()
        
        assert isinstance(version, str)
        assert "." in version  # Should contain version separator

    async def test_error_handling_no_data(self, ai_service):
        """Test error handling when no data is available."""
        device_id = "empty_device"
        
        with patch.object(ai_service, '_get_device_analytics') as mock_get_analytics:
            mock_get_analytics.return_value = pd.DataFrame()
            
            # Should not raise exception, should return empty list
            result = await ai_service.detect_anomalies(device_id)
            assert result == []

    async def test_concurrent_predictions(self, ai_service, sample_analytics_data):
        """Test concurrent anomaly detection calls."""
        device_ids = ["device_0", "device_1", "device_2"]
        
        with patch.object(ai_service, '_get_device_analytics') as mock_get_analytics, \
             patch.object(ai_service, '_get_device_baseline') as mock_get_baseline:
            
            mock_get_analytics.return_value = sample_analytics_data
            mock_get_baseline.return_value = {'cpu_usage': 50.0}
            
            await ai_service.initialize_models()
            
            # Run concurrent predictions
            import asyncio
            tasks = [ai_service.detect_anomalies(device_id) for device_id in device_ids]
            results = await asyncio.gather(*tasks)
            
            assert len(results) == len(device_ids)
            for result in results:
                assert isinstance(result, list)
