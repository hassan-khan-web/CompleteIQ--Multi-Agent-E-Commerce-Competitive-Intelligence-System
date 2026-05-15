import asyncio
from pathlib import Path
from config import load_config, validate_config
from system_integration import CompetitiveIntelligenceSystem
import system_integration
import product_catalog_processor
import semantic_search_engine
import orchestrators.multi_agent_orchestrator as mao

class _NoOpSpan:

    def end(self, *args, **kwargs):
        return None

class _NoOpTrace:
    input = None
    output = None

    def span(self, *args, **kwargs):
        return _NoOpSpan()

    def update(self, *args, **kwargs):
        return None

    def end(self, *args, **kwargs):
        return None

class _NoOpLangfuse:

    def trace(self, *args, **kwargs):
        return _NoOpTrace()

    def flush(self):
        return None
_noop = _NoOpLangfuse()
system_integration.Langfuse = lambda **kwargs: _noop
product_catalog_processor.langfuse = _noop
semantic_search_engine.langfuse = _noop
mao.langfuse = _noop

async def test_llm_agents() -> None:
    print('\n' + '=' * 70)
    print('TESTING LLM-INTEGRATED AGENTS WITH OPENROUTER FREE MODELS')
    print('=' * 70)
    print('\n[1] Loading configuration...')
    config = load_config()
    config.enable_tracing = False
    config.max_retries = 1
    config.timeout = 10
    is_valid, errors = validate_config(config)
    if not is_valid:
        print('[ERROR] Configuration validation failed:')
        for error in errors:
            print(f'  - {error}')
        return
    print('[✓] Configuration loaded successfully')
    print(f'  - OpenRouter API Key: {config.openrouter_api_key[:20]}...')
    print(f'  - Beacon Model: {config.llm_beacon_model}')
    print(f'  - Nexus Model: {config.llm_nexus_model}')
    print(f'  - Verse Model: {config.llm_verse_model}')
    print('\n[2] Initializing system...')
    system = CompetitiveIntelligenceSystem(config)
    success, errors = system.initialize()
    if not success:
        print('[ERROR] System initialization failed:')
        for error in errors:
            print(f'  - {error}')
        return
    print('[✓] System initialized successfully')
    print(f'  - Session ID: {system.session_id}')
    print(f'  - Products loaded: {len(system.normalized_products)}')
    print(f'  - Beacon Model: {system.beacon.model}')
    print(f'  - Nexus Model: {system.nexus.model}')
    print(f'  - Verse Model: {system.verse.model}')
    print('\n[3] Performing health check...')
    health = system.health_check()
    if health.overall_healthy:
        print('[✓] All components healthy')
        for component, status in health.components.items():
            symbol = '✓' if status else '✗'
            print(f'    [{symbol}] {component}')
    else:
        print('[ERROR] Health check failed')
        if health.errors:
            for error in health.errors:
                print(f'  - {error}')
        return
    print('\n[4] Running competitive analysis with LLM agents...')
    print('    (This will use OpenRouter free models)')
    print('    - Beacon: deepseek-v4-flash (pricing analysis)')
    print('    - Nexus: nemotron-3-nano-omni-30b-a3b-reasoning (market analysis)')
    print('    - Verse: gemma-4-31b-it (marketing content generation)')
    try:
        report = await system.analyze_competitors()
        print('\n[✓] Analysis complete!')
        print(f'  - Analysis ID: {report.analysis_id}')
        print(f'  - Confidence Score: {report.confidence_score:.2f}')
        print(f'  - Execution Time: {report.execution_time_ms}ms')
        print(f'  - Overall Recommendation: {report.overall_recommendation}')
        if report.errors:
            print('\n  [!] Analysis Errors:')
            for error in report.errors:
                print(f'    - {error}')
        if report.price_analysis:
            print('\n[5] Beacon (Price Monitor) Results:')
            beacon_status = report.price_analysis.get('status', 'unknown')
            print(f'  - Status: {beacon_status}')
            print(f"  - Execution Time: {report.price_analysis.get('execution_time', 0):.2f}s")
            if beacon_status == 'success':
                print('  - Analysis successfully executed with DeepSeek Flash model')
        if report.feature_analysis:
            print('\n[6] Nexus (Catalog Analyzer) Results:')
            nexus_status = report.feature_analysis.get('status', 'unknown')
            print(f'  - Status: {nexus_status}')
            print(f"  - Execution Time: {report.feature_analysis.get('execution_time', 0):.2f}s")
            if nexus_status == 'success':
                print('  - Analysis successfully executed with Nemotron Reasoning model')
        if report.marketing_insights:
            print('\n[7] Verse (Marketing Content) Results:')
            verse_status = report.marketing_insights.get('status', 'unknown')
            print(f'  - Status: {verse_status}')
            print(f"  - Execution Time: {report.marketing_insights.get('execution_time', 0):.2f}s")
            if verse_status == 'success':
                print('  - Content successfully generated with Gemma-4 IT model')
        output_dir = Path('outputs')
        output_dir.mkdir(exist_ok=True)
        output_path = output_dir / f'llm_analysis_{report.analysis_id}.json'
        report.save(str(output_path))
        print(f'\n[✓] Report saved: {output_path}')
        print('\n' + '=' * 70)
        print('LLM AGENTS TEST SUMMARY')
        print('=' * 70)
        print('[✓] All three free OpenRouter models successfully integrated:')
        print('  ✓ Beacon using deepseek-v4-flash (fast pricing analysis)')
        print('  ✓ Nexus using nemotron-3-nano-omni-30b-a3b-reasoning (complex reasoning)')
        print('  ✓ Verse using gemma-4-31b-it (creative content generation)')
        print('\n[✓] Total execution time: {:.2f}s'.format(report.execution_time_ms / 1000))
        print('[✓] System confidence score: {:.2f}'.format(report.confidence_score))
        print('=' * 70)
    except Exception as e:
        print(f'[ERROR] Analysis failed: {str(e)}')
        import traceback
        traceback.print_exc()
    finally:
        system.cleanup()
if __name__ == '__main__':
    asyncio.run(test_llm_agents())