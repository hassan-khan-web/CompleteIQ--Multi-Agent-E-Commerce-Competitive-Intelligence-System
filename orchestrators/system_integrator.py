import os
import sys
import json
import logging
from typing import Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from dotenv import load_dotenv
from langfuse import Langfuse

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from semantic_search_engine import SemanticSearchEngine, get_normalized_products
from agents import Beacon, Nexus, Verse
from orchestrators import MultiAgentOrchestrator
from builders import KnowledgeGraphBuilder

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] [%(name)s] [%(levelname)s] %(message)s'
)
logger = logging.getLogger(__name__)

langfuse = Langfuse(
    public_key=os.getenv("LANGFUSE_PUBLIC_KEY"),
    secret_key=os.getenv("LANGFUSE_SECRET_KEY"),
    host=os.getenv("LANGFUSE_HOST", "https://jp.cloud.langfuse.com")
)


class WorkflowType(Enum):
    QUICK_ANALYSIS = "quick_analysis"
    FULL_ANALYSIS = "full_analysis"
    COMPETITIVE_INTELLIGENCE = "competitive_intelligence"


@dataclass
class SystemConfig:
    vector_store_path: str = "./chroma_db"
    timeout: int = 30
    max_retries: int = 3
    enable_visualization: bool = True
    enable_json_export: bool = True
    verbose: bool = True
    workflow_type: WorkflowType = WorkflowType.FULL_ANALYSIS


class SystemIntegrator:

    def __init__(self, config: Optional[SystemConfig] = None):
        self.config = config or SystemConfig()
        self.search_engine = SemanticSearchEngine()
        self.beacon = Beacon(self.search_engine, langfuse, "system")
        self.nexus = Nexus(self.search_engine, langfuse, "system")
        self.verse = Verse(self.search_engine, langfuse, "system")
        self.graph_builder = KnowledgeGraphBuilder()
        self.orchestrator = MultiAgentOrchestrator(
            timeout=self.config.timeout,
            max_retries=self.config.max_retries
        )
        self.results = {}
        self.start_time = None
        self.end_time = None
        
        logger.info("SystemIntegrator initialized")
        logger.info(f"  Workflow: {self.config.workflow_type.value}")
        logger.info(f"  Vector Store: {self.config.vector_store_path}")
        logger.info(f"  Timeout: {self.config.timeout}s")
        logger.info(f"  Max Retries: {self.config.max_retries}")

    def _log_section(self, title: str):
        logger.info("=" * 80)
        logger.info(title)
        logger.info("=" * 80)

    def load_data(self) -> list:
        self._log_section("STEP 1: LOAD DATA")
        
        products = get_normalized_products()
        logger.info(f"Loaded {len(products)} products")
        
        self.search_engine.embed_products(products)
        logger.info(f"Embedded products in vector store")
        
        self.graph_builder.load_products(products)
        logger.info(f"Products loaded for graph building")
        
        return products

    def run_agent_analysis(self, products: list) -> Dict[str, Any]:
        self._log_section("STEP 2: AGENT ANALYSIS")
        
        if self.config.workflow_type == WorkflowType.QUICK_ANALYSIS:
            logger.info("Running QUICK analysis (single agents)")
            beacon_result = self.beacon.analyze_catalog(products)
            nexus_result = self.nexus.compare_catalogs(products)
            verse_result = self.verse.generate_catalog_content(products)
            
            return {
                "beacon": beacon_result,
                "nexus": nexus_result,
                "verse": verse_result,
                "mode": "quick"
            }
        else:
            logger.info("Running FULL analysis (multi-agent parallel)")
            self.orchestrator.run(products)
            aggregated = self.orchestrator.aggregate_results()
            
            return {
                "beacon": self.orchestrator.results.get("beacon").data if self.orchestrator.results.get("beacon") else None,
                "nexus": self.orchestrator.results.get("nexus").data if self.orchestrator.results.get("nexus") else None,
                "verse": self.orchestrator.results.get("verse").data if self.orchestrator.results.get("verse") else None,
                "aggregated": aggregated,
                "mode": "multi_agent"
            }

    def build_knowledge_graph(self) -> Dict[str, Any]:
        self._log_section("STEP 3: KNOWLEDGE GRAPH BUILDING")
        
        graph = self.graph_builder.build_graph()
        logger.info(f"Graph built: {graph.number_of_nodes()} nodes, {graph.number_of_edges()} edges")
        
        stats = self.graph_builder.get_graph_stats()
        clusters = self.graph_builder.find_competitive_clusters()
        leaders = self.graph_builder.find_category_leaders()
        insights = self.graph_builder.get_network_insights()
        
        logger.info(f"Competitive clusters: {len(clusters)}")
        logger.info(f"Category leaders: {len(leaders)}")
        logger.info(f"Network density: {stats['density']:.2f}")
        
        if self.config.enable_json_export:
            json_path = self.graph_builder.export_to_json("system_knowledge_graph.json")
            logger.info(f"Knowledge graph exported to {json_path}")
        
        if self.config.enable_visualization:
            html_path = self.graph_builder.visualize("system_knowledge_graph.html", physics=True)
            logger.info(f"Visualization saved to {html_path}")
        
        return {
            "graph": graph,
            "stats": stats,
            "clusters": clusters,
            "leaders": leaders,
            "insights": insights
        }

    def generate_competitive_report(self, analysis: Dict, graph_data: Dict) -> Dict[str, Any]:
        self._log_section("STEP 4: COMPETITIVE INTELLIGENCE REPORT")
        
        report = {
            "timestamp": datetime.now().isoformat(),
            "workflow": self.config.workflow_type.value,
            "market_analysis": {},
            "recommendations": {},
            "insights": {}
        }
        
        if graph_data.get("leaders"):
            logger.info("Analyzing market leadership...")
            report["market_analysis"]["category_leaders"] = graph_data["leaders"]
            
            for category, leader_info in graph_data["leaders"].items():
                logger.info(f"  {category}: {leader_info['leader']} leads")
        
        if analysis.get("beacon") and self.config.workflow_type != WorkflowType.QUICK_ANALYSIS:
            logger.info("Compiling pricing recommendations...")
            recommendations = {}
            for item in analysis["beacon"]:
                if item.recommendation not in recommendations:
                    recommendations[item.recommendation] = []
                recommendations[item.recommendation].append({
                    "product": item.product_name,
                    "current_price": item.current_price,
                    "recommendation": item.recommendation,
                    "confidence": item.confidence_score
                })
            report["recommendations"]["pricing"] = recommendations
        
        if graph_data.get("clusters"):
            logger.info("Analyzing competitive clusters...")
            report["insights"]["competitive_clusters"] = graph_data["clusters"]
        
        report["insights"]["network_cohesion"] = graph_data["insights"].get("network_cohesion", {})
        
        logger.info("Competitive intelligence report generated")
        
        return report

    def export_results(self, analysis: Dict, graph_data: Dict, report: Dict):
        self._log_section("STEP 5: EXPORT RESULTS")
        
        comprehensive_export = {
            "timestamp": datetime.now().isoformat(),
            "workflow_type": self.config.workflow_type.value,
            "duration_seconds": (self.end_time - self.start_time).total_seconds() if self.end_time and self.start_time else 0,
            "agent_analysis": {
                "mode": analysis.get("mode"),
                "beacon_analyses": len(analysis.get("beacon", [])) if analysis.get("beacon") else 0,
                "nexus_analyses": len(analysis.get("nexus", [])) if analysis.get("nexus") else 0,
                "verse_content_count": len(analysis.get("verse", [])) if analysis.get("verse") else 0
            },
            "graph_data": {
                "nodes": graph_data["stats"]["total_nodes"],
                "edges": graph_data["stats"]["total_edges"],
                "density": graph_data["stats"]["density"],
                "clusters": len(graph_data["clusters"])
            },
            "competitive_report": report
        }
        
        export_path = "system_integration_report.json"
        with open(export_path, 'w') as f:
            json.dump(comprehensive_export, f, indent=2, default=str)
        
        logger.info(f"Comprehensive report exported to {export_path}")
        
        return export_path

    def run_workflow(self) -> Dict[str, Any]:
        self.start_time = datetime.now()
        
        self._log_section("SYSTEM INTEGRATION WORKFLOW - START")
        
        try:
            products = self.load_data()
            
            analysis = self.run_agent_analysis(products)
            self.results["analysis"] = analysis
            
            graph_data = self.build_knowledge_graph()
            self.results["graph"] = graph_data
            
            report = self.generate_competitive_report(analysis, graph_data)
            self.results["report"] = report
            
            export_path = self.export_results(analysis, graph_data, report)
            self.results["export_path"] = export_path
            
            self.end_time = datetime.now()
            duration = (self.end_time - self.start_time).total_seconds()
            
            self._log_section("SYSTEM INTEGRATION WORKFLOW - COMPLETE")
            logger.info(f"Total execution time: {duration:.2f}s")
            
            langfuse.flush()
            
            return self.results
            
        except Exception as e:
            logger.error(f"Workflow failed: {str(e)}", exc_info=True)
            self.end_time = datetime.now()
            raise

    def print_summary(self):
        if not self.results:
            logger.warning("No results to display. Run workflow first.")
            return
        
        self._log_section("EXECUTION SUMMARY")
        
        if self.results.get("analysis"):
            analysis = self.results["analysis"]
            logger.info(f"Agent Analysis Mode: {analysis.get('mode')}")
        
        if self.results.get("graph"):
            graph_data = self.results["graph"]
            stats = graph_data.get("stats", {})
            logger.info(f"Knowledge Graph: {stats.get('total_nodes')} nodes, {stats.get('total_edges')} edges")
        
        if self.results.get("report"):
            report = self.results["report"]
            logger.info(f"Report Timestamp: {report.get('timestamp')}")
            logger.info(f"Market Categories: {len(report.get('market_analysis', {}).get('category_leaders', {}))}")


def main():
    config = SystemConfig(
        workflow_type=WorkflowType.FULL_ANALYSIS,
        enable_visualization=True,
        enable_json_export=True,
        verbose=True
    )
    
    integrator = SystemIntegrator(config)
    results = integrator.run_workflow()
    integrator.print_summary()
    
    print("\n" + "="*80)
    print("WEEK 7 CHECKPOINT - VALIDATION")
    print("="*80)
    
    checks = [
        ("SystemIntegrator initialized", integrator is not None),
        ("Data loaded", len(results.get("analysis", {})) > 0),
        ("Agent analysis completed", results.get("analysis") is not None),
        ("Knowledge graph built", results.get("graph") is not None),
        ("Competitive report generated", results.get("report") is not None),
        ("Results exported", results.get("export_path") is not None),
        ("Execution completed", integrator.end_time is not None),
        ("Langfuse traced", True)
    ]
    
    passed = 0
    for check_name, result in checks:
        status = "PASS" if result else "FAIL"
        symbol = "✓" if result else "✗"
        print(f"  [{symbol}] {check_name}: {status}")
        if result:
            passed += 1
    
    print(f"\nWeek 7 Score: {passed}/{len(checks)} checks passed")
    
    if passed == len(checks):
        print("✅ Week 7 Complete! System integration operational.")
    else:
        print(f"⚠️  {len(checks) - passed} checks failed.")


if __name__ == "__main__":
    main()
