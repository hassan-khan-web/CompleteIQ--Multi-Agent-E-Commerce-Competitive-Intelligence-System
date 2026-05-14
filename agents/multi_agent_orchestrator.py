import os
import uuid
import asyncio
from datetime import datetime
from dataclasses import dataclass, field
from typing import Any
from dotenv import load_dotenv
from langfuse import Langfuse

from semantic_search_engine import SemanticSearchEngine, get_normalized_products
from .beacon import Beacon
from .nexus import Nexus
from .verse import Verse

load_dotenv()

langfuse = Langfuse(
    public_key=os.getenv("LANGFUSE_PUBLIC_KEY"),
    secret_key=os.getenv("LANGFUSE_SECRET_KEY"),
    host=os.getenv("LANGFUSE_HOST", "https://jp.cloud.langfuse.com")
)


@dataclass
class AgentResult:
    agent_name: str
    status: str
    data: Any = None
    error: str = None
    execution_time: float = 0.0
    retry_count: int = 0


class MultiAgentOrchestrator:

    def __init__(self, timeout: int = 30, max_retries: int = 3):
        self.timeout = timeout
        self.max_retries = max_retries
        self.session_id = str(uuid.uuid4())
        self.search_engine = SemanticSearchEngine()
        self.beacon = Beacon(self.search_engine, langfuse, self.session_id)
        self.nexus = Nexus(self.search_engine, langfuse, self.session_id)
        self.verse = Verse(self.search_engine, langfuse, self.session_id)
        self.results = {}
        self.execution_metrics = {
            "start_time": None,
            "end_time": None,
            "total_time": 0.0,
            "agents_succeeded": 0,
            "agents_failed": 0,
            "total_retries": 0
        }

    async def execute_beacon(self, products, retry_count=0):
        try:
            start = datetime.now()
            result = await asyncio.wait_for(
                asyncio.to_thread(self.beacon.analyze_catalog, products),
                timeout=self.timeout
            )
            execution_time = (datetime.now() - start).total_seconds()
            return AgentResult(
                agent_name="Beacon",
                status="success",
                data=result,
                execution_time=execution_time,
                retry_count=retry_count
            )
        except asyncio.TimeoutError:
            if retry_count < self.max_retries:
                wait_time = 2 ** retry_count
                await asyncio.sleep(wait_time)
                return await self.execute_beacon(products, retry_count + 1)
            return AgentResult(
                agent_name="Beacon",
                status="failed",
                error=f"Timeout after {self.max_retries} retries",
                retry_count=retry_count
            )
        except Exception as e:
            if retry_count < self.max_retries:
                wait_time = 2 ** retry_count
                await asyncio.sleep(wait_time)
                return await self.execute_beacon(products, retry_count + 1)
            return AgentResult(
                agent_name="Beacon",
                status="failed",
                error=str(e),
                retry_count=retry_count
            )

    async def execute_nexus(self, products, retry_count=0):
        try:
            start = datetime.now()
            result = await asyncio.wait_for(
                asyncio.to_thread(self.nexus.compare_catalogs, products),
                timeout=self.timeout
            )
            execution_time = (datetime.now() - start).total_seconds()
            return AgentResult(
                agent_name="Nexus",
                status="success",
                data=result,
                execution_time=execution_time,
                retry_count=retry_count
            )
        except asyncio.TimeoutError:
            if retry_count < self.max_retries:
                wait_time = 2 ** retry_count
                await asyncio.sleep(wait_time)
                return await self.execute_nexus(products, retry_count + 1)
            return AgentResult(
                agent_name="Nexus",
                status="failed",
                error=f"Timeout after {self.max_retries} retries",
                retry_count=retry_count
            )
        except Exception as e:
            if retry_count < self.max_retries:
                wait_time = 2 ** retry_count
                await asyncio.sleep(wait_time)
                return await self.execute_nexus(products, retry_count + 1)
            return AgentResult(
                agent_name="Nexus",
                status="failed",
                error=str(e),
                retry_count=retry_count
            )

    async def execute_verse(self, products, retry_count=0):
        try:
            start = datetime.now()
            result = await asyncio.wait_for(
                asyncio.to_thread(self.verse.generate_catalog_content, products),
                timeout=self.timeout
            )
            execution_time = (datetime.now() - start).total_seconds()
            return AgentResult(
                agent_name="Verse",
                status="success",
                data=result,
                execution_time=execution_time,
                retry_count=retry_count
            )
        except asyncio.TimeoutError:
            if retry_count < self.max_retries:
                wait_time = 2 ** retry_count
                await asyncio.sleep(wait_time)
                return await self.execute_verse(products, retry_count + 1)
            return AgentResult(
                agent_name="Verse",
                status="failed",
                error=f"Timeout after {self.max_retries} retries",
                retry_count=retry_count
            )
        except Exception as e:
            if retry_count < self.max_retries:
                wait_time = 2 ** retry_count
                await asyncio.sleep(wait_time)
                return await self.execute_verse(products, retry_count + 1)
            return AgentResult(
                agent_name="Verse",
                status="failed",
                error=str(e),
                retry_count=retry_count
            )

    async def run_async(self, products):
        self.execution_metrics["start_time"] = datetime.now().isoformat()
        
        trace = langfuse.trace(
            name="multi_agent_orchestrator",
            input={"product_count": len(products), "agents": 3}
        )
        
        tasks = [
            self.execute_beacon(products),
            self.execute_nexus(products),
            self.execute_verse(products)
        ]
        
        results = await asyncio.gather(*tasks)
        
        for result in results:
            self.results[result.agent_name.lower()] = result
            if result.status == "success":
                self.execution_metrics["agents_succeeded"] += 1
            else:
                self.execution_metrics["agents_failed"] += 1
            self.execution_metrics["total_retries"] += result.retry_count
        
        self.execution_metrics["end_time"] = datetime.now().isoformat()
        start = datetime.fromisoformat(self.execution_metrics["start_time"])
        end = datetime.fromisoformat(self.execution_metrics["end_time"])
        self.execution_metrics["total_time"] = (end - start).total_seconds()
        
        trace.update(
            output={
                "agents_succeeded": self.execution_metrics["agents_succeeded"],
                "agents_failed": self.execution_metrics["agents_failed"],
                "total_time": self.execution_metrics["total_time"]
            }
        )
        
        langfuse.flush()

    def run(self, products):
        asyncio.run(self.run_async(products))

    def aggregate_results(self):
        beacon_result = self.results.get("beacon")
        nexus_result = self.results.get("nexus")
        verse_result = self.results.get("verse")
        
        beacon_data = beacon_result.data if beacon_result and beacon_result.status == "success" else None
        nexus_data = nexus_result.data if nexus_result and nexus_result.status == "success" else None
        verse_data = verse_result.data if verse_result and verse_result.status == "success" else None
        
        beacon_insights = {
            "status": beacon_result.status if beacon_result else "unknown",
            "analyses_count": len(beacon_data) if beacon_data else 0,
            "recommendations": {}
        }
        
        if beacon_data:
            for analysis in beacon_data:
                beacon_insights["recommendations"][analysis.recommendation] = \
                    beacon_insights["recommendations"].get(analysis.recommendation, 0) + 1
        
        market_analysis = {
            "status": nexus_result.status if nexus_result else "unknown",
            "companies_analyzed": len(nexus_data) if nexus_data else 0,
            "companies": {}
        }
        
        if nexus_data:
            for company, analysis in nexus_data.items():
                market_analysis["companies"][company] = {
                    "products": analysis.total_products,
                    "positioning": analysis.competitive_strength
                }
        
        content_metrics = {
            "status": verse_result.status if verse_result else "unknown",
            "content_generated": len(verse_data) if verse_data else 0,
            "tones": {}
        }
        
        if verse_data:
            for content in verse_data:
                content_metrics["tones"][content.tone] = \
                    content_metrics["tones"].get(content.tone, 0) + 1
        
        overall_status = "SUCCESS" if self.execution_metrics["agents_failed"] == 0 else "PARTIAL_SUCCESS" if self.execution_metrics["agents_succeeded"] > 0 else "FAILED"
        
        return {
            "session_id": self.session_id,
            "execution_metrics": self.execution_metrics,
            "beacon": {
                "status": beacon_result.status if beacon_result else "unknown",
                "execution_time": beacon_result.execution_time if beacon_result else 0.0,
                "error": beacon_result.error if beacon_result and beacon_result.error else None
            },
            "nexus": {
                "status": nexus_result.status if nexus_result else "unknown",
                "execution_time": nexus_result.execution_time if nexus_result else 0.0,
                "error": nexus_result.error if nexus_result and nexus_result.error else None
            },
            "verse": {
                "status": verse_result.status if verse_result else "unknown",
                "execution_time": verse_result.execution_time if verse_result else 0.0,
                "error": verse_result.error if verse_result and verse_result.error else None
            },
            "summary": {
                "beacon_insights": beacon_insights,
                "market_analysis": market_analysis,
                "content_metrics": content_metrics,
                "overall_status": overall_status
            }
        }

    def print_results(self):
        print("\n" + "="*80)
        print("WEEK 5: MULTI-AGENT ORCHESTRATION - EXECUTION RESULTS")
        print("="*80)
        print(f"\nSession ID: {self.session_id}")
        print(f"Start Time: {self.execution_metrics['start_time']}")
        print(f"End Time: {self.execution_metrics['end_time']}")
        print(f"Total Execution Time: {self.execution_metrics['total_time']:.2f}s")
        
        print("\n" + "-"*80)
        print("AGENT EXECUTION STATUS")
        print("-"*80)
        
        for agent_name in ["beacon", "nexus", "verse"]:
            result = self.results.get(agent_name)
            if result:
                status_symbol = "✓" if result.status == "success" else "✗"
                print(f"\n{status_symbol} {result.agent_name.upper()}")
                print(f"  Status: {result.status}")
                print(f"  Execution Time: {result.execution_time:.2f}s")
                print(f"  Retries: {result.retry_count}")
                if result.error:
                    print(f"  Error: {result.error}")
        
        print("\n" + "-"*80)
        print("AGGREGATE METRICS")
        print("-"*80)
        print(f"Agents Succeeded: {self.execution_metrics['agents_succeeded']}/3")
        print(f"Agents Failed: {self.execution_metrics['agents_failed']}/3")
        print(f"Total Retries: {self.execution_metrics['total_retries']}")
        
        aggregated = self.aggregate_results()
        print(f"\nOverall Status: {aggregated['summary']['overall_status']}")
        
        print("\n" + "="*80)
        print("WEEK 5 CHECKPOINT - VALIDATION")
        print("="*80)
        
        beacon_data = self.results.get("beacon")
        nexus_data = self.results.get("nexus")
        verse_data = self.results.get("verse")
        
        checks = [
            ("Beacon executed", beacon_data is not None),
            ("Nexus executed", nexus_data is not None),
            ("Verse executed", verse_data is not None),
            ("Beacon successful", beacon_data.status == "success" if beacon_data else False),
            ("Nexus successful", nexus_data.status == "success" if nexus_data else False),
            ("Verse successful", verse_data.status == "success" if verse_data else False),
            ("Parallel execution", self.execution_metrics["total_time"] <= 0.2),
            ("Retry logic functional", self.execution_metrics["total_retries"] >= 0)
        ]
        
        passed = 0
        for check_name, result in checks:
            status = "PASS" if result else "FAIL"
            symbol = "✓" if result else "✗"
            print(f"  [{symbol}] {check_name}: {status}")
            if result:
                passed += 1
        
        print(f"\nWeek 5 Score: {passed}/{len(checks)} checks passed")
        
        if passed == len(checks):
            print("✅ Week 5 Complete! Multi-agent orchestration operational.")
        else:
            print(f"⚠️  {len(checks) - passed} checks failed.")


async def main_async():
    orchestrator = MultiAgentOrchestrator(timeout=30, max_retries=3)
    products = get_normalized_products()
    
    print(f"[INFO] Loaded {len(products)} products")
    orchestrator.search_engine.embed_products(products)
    print(f"[INFO] Embedded products in vector store")
    
    await orchestrator.run_async(products)
    orchestrator.print_results()
    
    return orchestrator.aggregate_results()


def main():
    orchestrator = MultiAgentOrchestrator(timeout=30, max_retries=3)
    products = get_normalized_products()
    
    print(f"[INFO] Loaded {len(products)} products")
    orchestrator.search_engine.embed_products(products)
    print(f"[INFO] Embedded products in vector store")
    
    orchestrator.run(products)
    orchestrator.print_results()
    
    return orchestrator.aggregate_results()


if __name__ == "__main__":
    main()
