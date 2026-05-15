import os
import uuid
import json
import asyncio
from datetime import datetime
from typing import Optional, Dict, List, Any
from dataclasses import dataclass, field, asdict
from pathlib import Path
from langfuse import Langfuse
from config import SystemConfig, validate_config
from product_catalog_processor import TracedProductCatalogProcessor
from semantic_search_engine import SemanticSearchEngine
from agents.beacon import Beacon
from agents.nexus import Nexus
from agents.verse import Verse
from orchestrators.multi_agent_orchestrator import MultiAgentOrchestrator
from knowledge_graph_builder import ProductKnowledgeGraph

@dataclass
class HealthCheckResult:
    timestamp: str
    overall_healthy: bool
    components: Dict[str, bool] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)
    details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return asdict(self)

@dataclass
class CompetitiveReport:
    analysis_id: str
    timestamp: str
    session_id: str
    products_analyzed: int
    price_analysis: Dict[str, Any]
    feature_analysis: Dict[str, Any]
    marketing_insights: Dict[str, Any]
    overall_recommendation: str
    confidence_score: float
    execution_time_ms: int
    errors: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)

    def save(self, output_path: str) -> None:
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w') as f:
            json.dump(self.to_dict(), f, indent=2)

class CompetitiveIntelligenceSystem:

    def __init__(self, config: SystemConfig):
        self.config = config
        self.session_id = str(uuid.uuid4())
        self.langfuse: Optional[Langfuse] = None
        if config.enable_tracing:
            self.langfuse = Langfuse(public_key=config.langfuse_public_key, secret_key=config.langfuse_secret_key, host=config.langfuse_host)
        self.processor: Optional[TracedProductCatalogProcessor] = None
        self.search_engine: Optional[SemanticSearchEngine] = None
        self.beacon: Optional[Beacon] = None
        self.nexus: Optional[Nexus] = None
        self.verse: Optional[Verse] = None
        self.orchestrator: Optional[MultiAgentOrchestrator] = None
        self.knowledge_graph: Optional[ProductKnowledgeGraph] = None
        self.normalized_products: List[Dict[str, Any]] = []
        self.company_x_catalog: Dict[str, Any] = {}
        self.company_y_catalog: Dict[str, Any] = {}

    def initialize(self) -> tuple[bool, List[str]]:
        errors = []
        if self.langfuse:
            trace = self.langfuse.trace(name='system_initialization', session_id=self.session_id)
            trace.input = {'config': self.config.model_dump()}
        try:
            is_valid, config_errors = validate_config(self.config)
            if not is_valid:
                errors.extend(config_errors)
                return (False, errors)
            print(f'[INFO] Initializing system (Session: {self.session_id})')
            print('[INFO] Initializing product processor...')
            self.processor = TracedProductCatalogProcessor()
            print('[INFO] Loading product catalogs...')
            try:
                with open(f'{self.config.data_dir}company_x.json') as f:
                    self.company_x_catalog = json.load(f)
                with open(f'{self.config.data_dir}company_y.json') as f:
                    self.company_y_catalog = json.load(f)
            except FileNotFoundError as e:
                errors.append(f'Dataset not found: {e}')
                return (False, errors)
            print('[INFO] Processing catalogs...')
            company_x_products = self.processor.process_catalog_with_tracing(self.company_x_catalog)
            company_y_products = self.processor.process_catalog_with_tracing(self.company_y_catalog)
            self.normalized_products = company_x_products + company_y_products
            print(f'[INFO] Processed {len(self.normalized_products)} products')
            print('[INFO] Initializing semantic search engine...')
            self.search_engine = SemanticSearchEngine(db_path=self.config.chroma_db_path, collection_name=self.config.chroma_collection)
            print('[INFO] Embedding products...')
            self.search_engine.embed_products(self.normalized_products)
            print('[INFO] Products embedded successfully')
            print('[INFO] Initializing agents with LLM models...')
            self.beacon = Beacon(self.search_engine, self.langfuse, self.session_id, self.config.openrouter_api_key, self.config.llm_beacon_model)
            self.nexus = Nexus(self.search_engine, self.langfuse, self.session_id, self.config.openrouter_api_key, self.config.llm_nexus_model)
            self.verse = Verse(self.search_engine, self.langfuse, self.session_id, self.config.openrouter_api_key, self.config.llm_verse_model)
            print('[INFO] Initializing orchestrator...')
            self.orchestrator = MultiAgentOrchestrator(timeout=self.config.timeout, max_retries=self.config.max_retries)
            self.orchestrator.search_engine = self.search_engine
            self.orchestrator.beacon = self.beacon
            self.orchestrator.nexus = self.nexus
            self.orchestrator.verse = self.verse
            print('[INFO] Building knowledge graph...')
            self.knowledge_graph = ProductKnowledgeGraph()
            self.knowledge_graph.add_products(self.normalized_products)
            print('[INFO] Knowledge graph ready')
            print('[INFO] System initialized successfully')
            if self.langfuse:
                trace.output = {'status': 'success', 'products_loaded': len(self.normalized_products)}
                self.langfuse.flush()
            return (True, [])
        except Exception as e:
            error_msg = f'Initialization failed: {str(e)}'
            errors.append(error_msg)
            print(f'[ERROR] {error_msg}')
            if self.langfuse:
                trace = self.langfuse.trace(name='initialization_error', session_id=self.session_id)
                trace.output = {'error': str(e)}
                self.langfuse.flush()
            return (False, errors)

    async def analyze_competitors(self, products: Optional[List[Dict]]=None) -> CompetitiveReport:
        analysis_id = str(uuid.uuid4())
        start_time = datetime.now()
        if products is None:
            products = self.normalized_products
        if not products:
            raise ValueError('No products available for analysis')
        if self.langfuse:
            trace = self.langfuse.trace(name='competitive_analysis', session_id=self.session_id)
            trace.input = {'products_count': len(products)}
        errors = []
        try:
            print(f'[INFO] Starting competitive analysis (ID: {analysis_id})')
            if not self.orchestrator:
                raise ValueError('System not initialized. Call initialize() first.')
            print('[INFO] Running agents in parallel...')
            await self.orchestrator.run_async(products)
            results = self.orchestrator.aggregate_results()
            price_analysis = results.get('beacon', {})
            feature_analysis = results.get('nexus', {})
            marketing_insights = results.get('verse', {})
            overall_recommendation = self._generate_recommendation(price_analysis, feature_analysis, marketing_insights)
            confidence_score = self._calculate_confidence(price_analysis, feature_analysis, marketing_insights)
            execution_time = int((datetime.now() - start_time).total_seconds() * 1000)
            report = CompetitiveReport(analysis_id=analysis_id, timestamp=datetime.now().isoformat(), session_id=self.session_id, products_analyzed=len(products), price_analysis=price_analysis, feature_analysis=feature_analysis, marketing_insights=marketing_insights, overall_recommendation=overall_recommendation, confidence_score=confidence_score, execution_time_ms=execution_time, errors=errors)
            print(f'[INFO] Analysis complete (Time: {execution_time}ms, Confidence: {confidence_score:.2f})')
            if self.langfuse:
                trace.output = {'analysis_id': analysis_id, 'confidence': confidence_score, 'execution_time_ms': execution_time}
                self.langfuse.flush()
            return report
        except Exception as e:
            error_msg = f'Analysis failed: {str(e)}'
            errors.append(error_msg)
            print(f'[ERROR] {error_msg}')
            if self.langfuse:
                trace = self.langfuse.trace(name='analysis_error', session_id=self.session_id)
                trace.output = {'error': str(e)}
                self.langfuse.flush()
            execution_time = int((datetime.now() - start_time).total_seconds() * 1000)
            return CompetitiveReport(analysis_id=analysis_id, timestamp=datetime.now().isoformat(), session_id=self.session_id, products_analyzed=len(products), price_analysis={}, feature_analysis={}, marketing_insights={}, overall_recommendation='Analysis failed', confidence_score=0.0, execution_time_ms=execution_time, errors=errors)

    def health_check(self) -> HealthCheckResult:
        if self.langfuse:
            trace = self.langfuse.trace(name='health_check', session_id=self.session_id)
        timestamp = datetime.now().isoformat()
        components = {}
        errors = []
        details = {}
        components['processor'] = self.processor is not None
        if not components['processor']:
            errors.append('Processor not initialized')
        components['search_engine'] = self.search_engine is not None
        if components['search_engine']:
            try:
                stats = self.search_engine.get_stats()
                details['search_engine_products'] = stats.get('total_products', 0)
            except Exception as e:
                errors.append(f'Search engine error: {str(e)}')
                components['search_engine'] = False
        components['beacon'] = self.beacon is not None
        components['nexus'] = self.nexus is not None
        components['verse'] = self.verse is not None
        if not all([components['beacon'], components['nexus'], components['verse']]):
            errors.append('Not all agents initialized')
        components['orchestrator'] = self.orchestrator is not None
        if not components['orchestrator']:
            errors.append('Orchestrator not initialized')
        components['knowledge_graph'] = self.knowledge_graph is not None
        if components['knowledge_graph']:
            kg_stats = self.knowledge_graph.get_graph_stats()
            details['kg_nodes'] = kg_stats.get('total_nodes', 0)
            details['kg_edges'] = kg_stats.get('total_edges', 0)
        else:
            errors.append('Knowledge graph not initialized')
        components['data_loaded'] = len(self.normalized_products) > 0
        if components['data_loaded']:
            details['products_loaded'] = len(self.normalized_products)
        overall_healthy = all(components.values()) and len(errors) == 0 and (len(self.normalized_products) > 0)
        result = HealthCheckResult(timestamp=timestamp, overall_healthy=overall_healthy, components=components, errors=errors, details=details)
        if self.langfuse:
            trace.output = result.to_dict()
            self.langfuse.flush()
        return result

    def cleanup(self) -> None:
        if self.langfuse:
            trace = self.langfuse.trace(name='system_cleanup', session_id=self.session_id)
        print('[INFO] Cleaning up resources...')
        try:
            if self.search_engine:
                print('[INFO] Closing search engine...')
                self.search_engine = None
            if self.langfuse:
                print('[INFO] Flushing Langfuse traces...')
                self.langfuse.flush()
                trace.output = {'status': 'cleanup_complete'}
            print('[INFO] Cleanup complete')
        except Exception as e:
            print(f'[ERROR] Cleanup error: {str(e)}')

    def _generate_recommendation(self, price_analysis: Dict, feature_analysis: Dict, marketing_insights: Dict) -> str:
        try:
            if not any([price_analysis, feature_analysis, marketing_insights]):
                return 'Insufficient data for recommendation'
            parts = []
            beacon_status = price_analysis.get('status', 'unknown')
            if beacon_status == 'success':
                parts.append('Pricing analysis complete')
            nexus_status = feature_analysis.get('status', 'unknown')
            if nexus_status == 'success':
                parts.append('Feature analysis complete')
            verse_status = marketing_insights.get('status', 'unknown')
            if verse_status == 'success':
                parts.append('Marketing content generated')
            return ' | '.join(parts) if parts else 'Maintain current positioning'
        except Exception as e:
            print(f'[WARN] Recommendation generation failed: {str(e)}')
            return 'Unable to generate recommendation'

    def _calculate_confidence(self, price_analysis: Dict, feature_analysis: Dict, marketing_insights: Dict) -> float:
        scores = []
        if price_analysis.get('status') == 'success':
            scores.append(0.85)
        elif price_analysis.get('status') == 'failed':
            scores.append(0.3)
        if feature_analysis.get('status') == 'success':
            scores.append(0.85)
        elif feature_analysis.get('status') == 'failed':
            scores.append(0.3)
        if marketing_insights.get('status') == 'success':
            scores.append(0.85)
        elif marketing_insights.get('status') == 'failed':
            scores.append(0.3)
        return sum(scores) / len(scores) if scores else 0.0

async def main() -> None:
    config = SystemConfig()
    system = CompetitiveIntelligenceSystem(config)
    success, errors = system.initialize()
    if not success:
        print(f'[ERROR] Initialization failed: {errors}')
        return
    health = system.health_check()
    print(f'[INFO] Health check: {health.overall_healthy}')
    if health.errors:
        for error in health.errors:
            print(f'  - {error}')
    try:
        report = await system.analyze_competitors()
        print(f'[INFO] Analysis complete: {report.analysis_id}')
        print(f'  - Confidence: {report.confidence_score:.2f}')
        print(f'  - Time: {report.execution_time_ms}ms')
        output_path = f'./outputs/analysis_{report.analysis_id}.json'
        report.save(output_path)
        print(f'[INFO] Report saved: {output_path}')
    finally:
        system.cleanup()
if __name__ == '__main__':
    asyncio.run(main())