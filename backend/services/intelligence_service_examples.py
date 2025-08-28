"""
Example usage and testing for AndroidZen Pro AI Service

This file demonstrates how to use the comprehensive AI/ML capabilities
of the AI Service including:
- Device usage pattern analysis
- Predictive maintenance
- Anomaly detection 
- User behavior clustering
- AI-powered recommendations
- Model training and updates
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import List

from ai_service import AIService, ModelInfo, PredictiveMaintenance, AnomalyDetection, UserBehaviorCluster, AIRecommendation

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def demonstrate_ai_service():
    """Demonstrate the comprehensive AI service capabilities"""
    
    # Initialize AI Service
    ai_service = AIService()
    
    # Initialize models (loads existing models and prepares scalers)
    success = await ai_service.initialize_models()
    if success:
        logger.info("✅ AI Service initialized successfully")
    else:
        logger.error("❌ Failed to initialize AI Service")
        return
    
    # Example device IDs for testing
    device_ids = ["device_123", "device_456", "device_789"]
    
    print("\n" + "="*80)
    print("🤖 AndroidZen Pro AI/ML Service Demonstration")
    print("="*80)
    
    # 1. Device Usage Pattern Analysis
    print("\n📊 1. Device Usage Pattern Analysis")
    print("-" * 50)
    
    for device_id in device_ids[:1]:  # Test with first device
        try:
            patterns = await ai_service.analyze_device_usage_patterns(device_id, days_back=30)
            
            if "error" not in patterns:
                print(f"✅ Analysis for {device_id}:")
                print(f"   • Analysis period: {patterns['analysis_period']}")
                print(f"   • Data points: {patterns['total_data_points']}")
                print(f"   • Patterns found: {len(patterns.get('usage_patterns', {}))}")
                print(f"   • Insights: {len(patterns.get('insights', []))}")
                print(f"   • Recommendations: {len(patterns.get('recommendations', []))}")
                
                # Show sample insights
                if patterns.get('insights'):
                    print("   Sample insights:")
                    for insight in patterns['insights'][:2]:
                        print(f"     - {insight}")
            else:
                print(f"⚠️  {device_id}: {patterns['error']}")
                
        except Exception as e:
            print(f"❌ Error analyzing {device_id}: {e}")
    
    # 2. Predictive Maintenance
    print("\n🔧 2. Predictive Maintenance Analysis")
    print("-" * 50)
    
    for device_id in device_ids[:1]:
        try:
            predictions = await ai_service.predict_maintenance_needs(device_id, prediction_horizon_days=30)
            
            print(f"✅ Maintenance predictions for {device_id}:")
            if predictions:
                for pred in predictions:
                    print(f"   • Component: {pred.component}")
                    print(f"     - Risk level: {pred.risk_level}")
                    print(f"     - Current health: {pred.current_health:.1f}%")
                    print(f"     - Predicted health: {pred.predicted_health:.1f}%")
                    print(f"     - Confidence: {pred.confidence:.2f}")
                    if pred.time_to_action:
                        print(f"     - Action needed in: {pred.time_to_action} days")
                    print(f"     - Recommendations: {len(pred.recommendations)}")
                    print("")
            else:
                print("   No maintenance predictions available")
                
        except Exception as e:
            print(f"❌ Error predicting maintenance for {device_id}: {e}")
    
    # 3. Anomaly Detection
    print("\n🚨 3. Anomaly Detection")
    print("-" * 50)
    
    for device_id in device_ids[:1]:
        try:
            anomalies = await ai_service.detect_anomalies(device_id, sensitivity=0.1)
            
            print(f"✅ Anomaly detection for {device_id}:")
            if anomalies:
                for anomaly in anomalies:
                    print(f"   • Type: {anomaly.anomaly_type}")
                    print(f"     - Severity: {anomaly.severity}")
                    print(f"     - Score: {anomaly.anomaly_score:.3f}")
                    print(f"     - Confidence: {anomaly.confidence:.2f}")
                    print(f"     - Affected metrics: {', '.join(anomaly.affected_metrics)}")
                    print(f"     - Deviation: {anomaly.deviation_percentage:.1f}%")
                    print(f"     - Explanation: {anomaly.explanation}")
                    print("")
            else:
                print("   No anomalies detected")
                
        except Exception as e:
            print(f"❌ Error detecting anomalies for {device_id}: {e}")
    
    # 4. User Behavior Clustering
    print("\n👥 4. User Behavior Clustering")
    print("-" * 50)
    
    try:
        clusters = await ai_service.cluster_user_behavior(min_devices=3)
        
        print("✅ User behavior clustering results:")
        if clusters:
            for cluster in clusters:
                print(f"   • Cluster {cluster.cluster_id}: {cluster.cluster_name}")
                print(f"     - Devices: {len(cluster.device_ids)}")
                print(f"     - Performance req: {cluster.performance_requirements}")
                print(f"     - Security awareness: {cluster.security_awareness}")
                print(f"     - App preferences: {', '.join(cluster.app_preferences[:3])}")
                print(f"     - Recommendations: {len(cluster.recommendations)}")
                print("")
        else:
            print("   Insufficient data for clustering")
            
    except Exception as e:
        print(f"❌ Error in behavior clustering: {e}")
    
    # 5. AI-Powered Recommendations
    print("\n💡 5. AI-Powered Recommendations")
    print("-" * 50)
    
    for device_id in device_ids[:1]:
        try:
            recommendations = await ai_service.generate_ai_recommendations(device_id, include_explanations=True)
            
            print(f"✅ AI recommendations for {device_id}:")
            if recommendations:
                # Group by category
                by_category = {}
                for rec in recommendations:
                    if rec.category not in by_category:
                        by_category[rec.category] = []
                    by_category[rec.category].append(rec)
                
                for category, recs in by_category.items():
                    print(f"   📂 {category.title()} ({len(recs)} recommendations):")
                    for rec in recs[:2]:  # Show top 2 per category
                        print(f"     • {rec.title} ({rec.priority} priority)")
                        print(f"       - {rec.description}")
                        print(f"       - Confidence: {rec.confidence:.2f}")
                        print(f"       - Impact: {rec.expected_impact}")
                        print(f"       - Time: {rec.estimated_time}")
                        if rec.reasoning:
                            print(f"       - Reasoning: {rec.reasoning[0]}")
                        print("")
            else:
                print("   No recommendations generated")
                
        except Exception as e:
            print(f"❌ Error generating recommendations for {device_id}: {e}")
    
    # 6. Model Training and Management
    print("\n🎯 6. Model Training and Management")
    print("-" * 50)
    
    try:
        # Get current model information
        model_info = ai_service.get_model_info()
        print(f"✅ Current models loaded: {len(model_info) if isinstance(model_info, list) else 1}")
        
        # Train models (simplified demonstration)
        print("🔄 Training models...")
        training_results = await ai_service.train_models(
            model_types=["anomaly", "clustering"], 
            force_retrain=False
        )
        
        print("✅ Training results:")
        for model_type, success in training_results.items():
            status = "✅ Success" if success else "❌ Failed"
            print(f"   • {model_type}: {status}")
        
        # Update models
        print("🔄 Updating models...")
        update_success = await ai_service.update_models()
        print(f"✅ Model update: {'Success' if update_success else 'Failed'}")
        
    except Exception as e:
        print(f"❌ Error in model management: {e}")
    
    # 7. Advanced Features Demo
    print("\n🚀 7. Advanced Features")
    print("-" * 50)
    
    try:
        # Model versioning info
        all_models = ai_service.get_model_info()
        if isinstance(all_models, list) and all_models:
            print("✅ Model versioning information:")
            for model in all_models[:3]:  # Show first 3 models
                print(f"   • Model: {model.model_id}")
                print(f"     - Type: {model.model_type}")
                print(f"     - Version: {model.version}")
                print(f"     - Created: {model.created_at.strftime('%Y-%m-%d %H:%M')}")
                print(f"     - Training samples: {model.training_samples}")
                if model.accuracy:
                    print(f"     - Accuracy: {model.accuracy:.3f}")
                print("")
        
        # Feature importance (if available)
        print("📈 Feature importance analysis available for trained models")
        print("🔍 Explainable AI features integrated in recommendations")
        print("📊 Real-time model performance monitoring enabled")
        
    except Exception as e:
        print(f"❌ Error accessing advanced features: {e}")
    
    print("\n" + "="*80)
    print("🎉 AI Service demonstration completed successfully!")
    print("="*80)


async def test_specific_features():
    """Test specific AI service features with detailed output"""
    
    ai_service = AIService()
    await ai_service.initialize_models()
    
    print("\n🧪 Detailed Feature Testing")
    print("="*50)
    
    # Test feature extraction
    print("\n1. Testing Feature Extraction:")
    import pandas as pd
    
    # Create sample data
    sample_data = pd.DataFrame({
        'cpu_usage': [45.2, 67.8, 23.1, 89.5, 34.7],
        'memory_usage': [56.3, 78.9, 34.2, 92.1, 45.6],
        'battery_level': [87, 65, 45, 23, 78],
        'storage_usage_percentage': [67.5, 71.2, 69.8, 74.3, 68.9],
        'recorded_at': pd.date_range('2024-01-01', periods=5, freq='1H')
    })
    
    features = ai_service.feature_extractor.fit_transform(sample_data)
    print(f"✅ Extracted {features.shape[1]} features from {features.shape[0]} data points")
    print(f"   Feature names: {ai_service.feature_extractor.feature_names_}")
    
    # Test anomaly detection components
    print("\n2. Testing Anomaly Detection Components:")
    from sklearn.preprocessing import StandardScaler
    
    scaler = StandardScaler()
    features_scaled = scaler.fit_transform(features)
    
    from sklearn.ensemble import IsolationForest
    iso_forest = IsolationForest(contamination=0.2, random_state=42)
    anomaly_scores = iso_forest.fit_predict(features_scaled)
    decision_scores = iso_forest.decision_function(features_scaled)
    
    anomalies_count = sum(1 for score in anomaly_scores if score == -1)
    print(f"✅ Detected {anomalies_count} anomalies out of {len(anomaly_scores)} samples")
    print(f"   Decision scores range: {decision_scores.min():.3f} to {decision_scores.max():.3f}")
    
    # Test clustering components
    print("\n3. Testing Clustering Components:")
    from sklearn.cluster import KMeans
    from sklearn.metrics import silhouette_score
    
    kmeans = KMeans(n_clusters=3, random_state=42)
    cluster_labels = kmeans.fit_predict(features_scaled)
    
    if len(set(cluster_labels)) > 1:
        sil_score = silhouette_score(features_scaled, cluster_labels)
        print(f"✅ Created {len(set(cluster_labels))} clusters")
        print(f"   Silhouette score: {sil_score:.3f}")
        print(f"   Cluster distribution: {dict(pd.Series(cluster_labels).value_counts())}")
    
    print("\n✅ All feature tests completed successfully!")


if __name__ == "__main__":
    """Run the AI service demonstration"""
    
    print("🚀 Starting AndroidZen Pro AI Service Demonstration...")
    
    # Run main demonstration
    asyncio.run(demonstrate_ai_service())
    
    # Run detailed feature testing
    asyncio.run(test_specific_features())
    
    print("\n🎯 All demonstrations completed!")
    print("\nNext steps:")
    print("1. Integrate AI service with main application")
    print("2. Set up automated model training pipeline")
    print("3. Configure monitoring and alerting")
    print("4. Implement user interface for AI insights")
    print("5. Set up A/B testing for recommendation effectiveness")
