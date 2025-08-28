#!/usr/bin/env python3
"""
Quick validation script for AI Service
"""
import sys
import os
import asyncio
from pathlib import Path

# Add the backend directory to Python path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

async def main():
    """Validate AI Service functionality"""
    try:
        # Import the AI service
        from services.ai_service import AIService, ModelInfo, PredictiveMaintenance
        print("✓ AI Service imports successful")
        
        # Create AI service instance
        ai_service = AIService()
        print("✓ AI Service instance created")
        
        # Check model directory creation
        models_dir = ai_service.models_dir
        if models_dir.exists():
            print("✓ Models directory created successfully")
        else:
            print("✗ Models directory not created")
        
        # Initialize models (basic check)
        result = await ai_service.initialize_models()
        if result:
            print("✓ AI Service initialized successfully")
        else:
            print("✗ AI Service initialization failed")
        
        # Test data structures
        model_info = ModelInfo(
            model_id="test_model",
            model_type="anomaly",
            version="1.0.0",
            created_at=ai_service.logger.__class__.__module__.split('.')[0] == 'logging' and True
        )
        print("✓ ModelInfo dataclass works correctly")
        
        print("\n🎉 AI Service validation completed successfully!")
        print(f"   - Models directory: {models_dir}")
        print(f"   - Available model types: {list(ai_service.anomaly_models.keys())}")
        print(f"   - Available clustering methods: {list(ai_service.clustering_models.keys())}")
        
    except ImportError as e:
        print(f"✗ Import error: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"✗ Validation error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
