"""Week 7 System Integration Test & Validation."""

import asyncio
import json
from pathlib import Path

from config import SystemConfig, load_config, validate_config
from system_integration import CompetitiveIntelligenceSystem


async def test_configuration() -> tuple[bool, str]:
    """Test configuration loading and validation.

    Returns:
        Tuple of (success, message)
    """
    print("\n" + "="*60)
    print("TEST 1: Configuration Loading & Validation")
    print("="*60)

    try:
        config = load_config()
        print("[✓] Configuration loaded successfully")

        is_valid, errors = validate_config(config)

        if not is_valid:
            print(f"[✗] Configuration validation failed:")
            for error in errors:
                print(f"    - {error}")
            return False, "Configuration validation failed"

        print("[✓] Configuration validation passed")
        print(f"  - Model: {config.openai_model}")
        print(f"  - Batch Size: {config.batch_size}")
        print(f"  - Timeout: {config.timeout}s")
        print(f"  - Tracing: {'Enabled' if config.enable_tracing else 'Disabled'}")

        return True, "Configuration test passed"

    except Exception as e:
        print(f"[✗] Configuration test failed: {str(e)}")
        return False, f"Configuration error: {str(e)}"


async def test_system_initialization() -> tuple[bool, str]:
    """Test system initialization.

    Returns:
        Tuple of (success, message)
    """
    print("\n" + "="*60)
    print("TEST 2: System Initialization")
    print("="*60)

    try:
        config = load_config()
        system = CompetitiveIntelligenceSystem(config)

        print(f"[✓] System created (Session: {system.session_id})")

        success, errors = system.initialize()

        if not success:
            print("[✗] System initialization failed:")
            for error in errors:
                print(f"    - {error}")
            return False, "System initialization failed"

        print("[✓] System initialized successfully")
        print(f"  - Products loaded: {len(system.normalized_products)}")
        print(f"  - Processor: {'✓' if system.processor else '✗'}")
        print(f"  - Search Engine: {'✓' if system.search_engine else '✗'}")
        print(f"  - Agents: {'✓' if system.beacon and system.nexus and system.verse else '✗'}")
        print(f"  - Orchestrator: {'✓' if system.orchestrator else '✗'}")

        system.cleanup()
        return True, "System initialization test passed"

    except Exception as e:
        print(f"[✗] System initialization test failed: {str(e)}")
        return False, f"Initialization error: {str(e)}"


async def test_health_check() -> tuple[bool, str]:
    """Test health check functionality.

    Returns:
        Tuple of (success, message)
    """
    print("\n" + "="*60)
    print("TEST 3: Health Check")
    print("="*60)

    try:
        config = load_config()
        system = CompetitiveIntelligenceSystem(config)

        success, errors = system.initialize()
        if not success:
            return False, "Failed to initialize system for health check"

        health = system.health_check()

        print(f"[{'✓' if health.overall_healthy else '✗'}] Overall Health: {health.overall_healthy}")
        print("\nComponent Status:")
        for component, status in health.components.items():
            symbol = "✓" if status else "✗"
            print(f"  [{symbol}] {component}")

        if health.errors:
            print("\nErrors:")
            for error in health.errors:
                print(f"  - {error}")

        if health.details:
            print("\nDetails:")
            for key, value in health.details.items():
                print(f"  - {key}: {value}")

        system.cleanup()
        return health.overall_healthy, "Health check test passed"

    except Exception as e:
        print(f"[✗] Health check test failed: {str(e)}")
        return False, f"Health check error: {str(e)}"


async def test_competitive_analysis() -> tuple[bool, str]:
    """Test competitive analysis end-to-end.

    Returns:
        Tuple of (success, message)
    """
    print("\n" + "="*60)
    print("TEST 4: Competitive Analysis (End-to-End)")
    print("="*60)

    try:
        config = load_config()
        system = CompetitiveIntelligenceSystem(config)

        success, errors = system.initialize()
        if not success:
            return False, "Failed to initialize system for analysis"

        print("[✓] System ready")
        print(f"[INFO] Running competitive analysis with {len(system.normalized_products)} products...")

        report = await system.analyze_competitors()

        print(f"[{'✓' if not report.errors else '✗'}] Analysis Complete")
        print(f"  - ID: {report.analysis_id}")
        print(f"  - Timestamp: {report.timestamp}")
        print(f"  - Products Analyzed: {report.products_analyzed}")
        print(f"  - Confidence Score: {report.confidence_score:.2f}")
        print(f"  - Execution Time: {report.execution_time_ms}ms")
        print(f"  - Overall Recommendation: {report.overall_recommendation}")

        if report.errors:
            print("\nAnalysis Errors:")
            for error in report.errors:
                print(f"  - {error}")

        # Save report
        output_dir = Path("outputs")
        output_dir.mkdir(exist_ok=True)
        output_path = output_dir / f"analysis_test_{report.analysis_id}.json"
        report.save(str(output_path))
        print(f"\n[✓] Report saved: {output_path}")

        system.cleanup()
        return not report.errors, "Analysis test passed"

    except Exception as e:
        print(f"[✗] Analysis test failed: {str(e)}")
        return False, f"Analysis error: {str(e)}"


async def run_all_tests() -> None:
    """Run all validation tests."""
    print("\n" + "="*60)
    print("WEEK 7: SYSTEM INTEGRATION VALIDATION")
    print("="*60)

    results = {}

    # Run tests
    results["Configuration"], config_msg = await test_configuration()
    results["Initialization"], init_msg = await test_system_initialization()
    results["Health Check"], health_msg = await test_health_check()
    results["Analysis"], analysis_msg = await test_competitive_analysis()

    # Summary
    print("\n" + "="*60)
    print("VALIDATION SUMMARY")
    print("="*60)

    passed = sum(1 for v in results.values() if v)
    total = len(results)

    for test_name, success in results.items():
        symbol = "✓" if success else "✗"
        print(f"[{symbol}] {test_name}")

    print(f"\nResult: {passed}/{total} tests passed")

    if passed == total:
        print("\n🎉 All validation tests passed! Week 7 implementation complete.")
    else:
        print(f"\n⚠️  {total - passed} test(s) failed. Review errors above.")


if __name__ == "__main__":
    asyncio.run(run_all_tests())
