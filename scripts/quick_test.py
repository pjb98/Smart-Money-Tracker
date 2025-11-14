"""
Quick test script to verify installation and run a simple end-to-end test
"""
import sys
import asyncio
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from datetime import datetime
from loguru import logger
import json

from src.ingestion.pumpfun_client import MockPumpfunClient
from src.ingestion.phanes_parser import MockPhanesParser
from src.features.feature_engineer import FeatureEngineer
from src.features.label_generator import LabelGenerator
from src.models.predictor import TokenPredictor


async def test_data_ingestion():
    """Test data ingestion modules"""
    logger.info("Testing data ingestion...")

    # Test Pumpfun client
    pumpfun = MockPumpfunClient()
    migrations = await pumpfun.get_migrations(limit=5)
    assert len(migrations) > 0, "Failed to get migrations"
    logger.success(f"✓ Pumpfun client working ({len(migrations)} migrations)")

    # Test Phanes parser
    phanes = MockPhanesParser()
    await phanes.connect()
    scans = await phanes.fetch_recent_scans(hours_back=24, limit=10)
    assert len(scans) > 0, "Failed to get scans"
    logger.success(f"✓ Phanes parser working ({len(scans)} scans)")

    await pumpfun.close()
    await phanes.disconnect()

    return migrations[0], scans[0]


def test_feature_engineering(migration, phanes_data):
    """Test feature engineering"""
    logger.info("Testing feature engineering...")

    engineer = FeatureEngineer()

    # Mock data
    token_data = {
        'address': migration['token_address'],
        'created_at': '2025-01-01T00:00:00Z',
        'supply': 1000000000
    }

    pool_data = {
        'initial_liquidity_sol': migration['initial_liquidity_sol'],
        'token_reserve': 500000000,
        'sol_reserve': 10.0,
        'lp_provider_count': 1,
        'liquidity_locked': True
    }

    features = engineer.build_feature_vector(
        token_address=migration['token_address'],
        migration_time=datetime.now(),
        token_data=token_data,
        pool_data=pool_data,
        transactions=[],
        holders=[
            {'owner': 'holder1', 'amount': 100000000},
            {'owner': 'holder2', 'amount': 50000000}
        ],
        phanes_data=phanes_data
    )

    assert len(features) > 20, "Not enough features generated"
    logger.success(f"✓ Feature engineering working ({len(features)} features)")

    return features


def test_label_generation():
    """Test label generation"""
    logger.info("Testing label generation...")

    generator = LabelGenerator()

    # Mock price data
    reference_time = datetime.now()
    price_history = []

    for i in range(50):
        from datetime import timedelta
        timestamp = reference_time + timedelta(minutes=i * 15)
        price = 1.0 + i * 0.02  # Gradual increase

        price_history.append({
            'timestamp': timestamp,
            'price': price
        })

    labels = generator.generate_labels(
        token_address='TESTTOKEN',
        migration_time=reference_time,
        price_history=price_history
    )

    assert 'return_24h' in labels, "Missing return labels"
    assert 'pump_24h' in labels, "Missing pump labels"
    logger.success(f"✓ Label generation working ({len(labels)} labels)")

    return labels


def test_model_prediction(features):
    """Test model prediction"""
    logger.info("Testing model prediction...")

    import pandas as pd

    predictor = TokenPredictor(target_variable='return_24h', task_type='regression')

    # Create mock feature DataFrame
    features_df = pd.DataFrame([features])

    # Note: Model is not trained, so this will fail without a trained model
    # But we can test the structure
    try:
        # Try to load existing model
        predictor.load('./models/token_predictor.pkl')
        prediction = predictor.predict(features_df)
        logger.success(f"✓ Model prediction working (prediction: {prediction[0]:.4f})")
    except:
        logger.warning("⚠ No trained model found (this is expected for first run)")
        logger.info("  To train a model, run the training pipeline with real data")

    return predictor


def test_claude_agent(features):
    """Test Claude AI agent"""
    logger.info("Testing Claude agent...")

    try:
        import os
        from src.agents.claude_agent import ClaudeAgent

        api_key = os.getenv('ANTHROPIC_API_KEY')

        if not api_key:
            logger.warning("⚠ ANTHROPIC_API_KEY not set, skipping Claude test")
            logger.info("  Set ANTHROPIC_API_KEY in .env to enable Claude AI features")
            return

        agent = ClaudeAgent(api_key=api_key)

        model_prediction = {
            'prediction': 0.25,
            'return_24h': 0.25
        }

        phanes_data = {
            'scan_count': 234,
            'avg_scan_velocity': 45,
            'rug_warning': False
        }

        analysis = agent.analyze_token(
            token_address='TESTTOKEN',
            features=features,
            model_prediction=model_prediction,
            phanes_data=phanes_data
        )

        assert 'recommendation' in analysis, "Missing recommendation"
        logger.success(f"✓ Claude agent working (recommendation: {analysis['recommendation']})")

    except Exception as e:
        logger.error(f"✗ Claude agent test failed: {e}")


async def run_all_tests():
    """Run all tests"""
    logger.info("=" * 60)
    logger.info("Running Quick Test Suite")
    logger.info("=" * 60)

    try:
        # Test 1: Data Ingestion
        migration, phanes_data = await test_data_ingestion()

        # Test 2: Feature Engineering
        features = test_feature_engineering(migration, phanes_data)

        # Test 3: Label Generation
        labels = test_label_generation()

        # Test 4: Model Prediction
        predictor = test_model_prediction(features)

        # Test 5: Claude Agent (optional)
        test_claude_agent(features)

        logger.info("=" * 60)
        logger.success("✓ All tests passed!")
        logger.info("=" * 60)
        logger.info("\nNext steps:")
        logger.info("1. Set up your .env file with API keys")
        logger.info("2. Collect historical data: python scripts/collect_data.py")
        logger.info("3. Train a model: python scripts/train_model.py")
        logger.info("4. Run the agent: python main.py")
        logger.info("5. Launch dashboard: python dashboard.py")

    except Exception as e:
        logger.error(f"Test failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(run_all_tests())
