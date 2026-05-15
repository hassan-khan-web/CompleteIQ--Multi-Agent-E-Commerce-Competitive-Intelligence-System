import os
import uuid
from dotenv import load_dotenv
from langfuse import Langfuse

from semantic_search_engine import SemanticSearchEngine, get_normalized_products
from agents import Beacon, Nexus, Verse

load_dotenv()

langfuse = Langfuse(
    public_key=os.getenv("LANGFUSE_PUBLIC_KEY"),
    secret_key=os.getenv("LANGFUSE_SECRET_KEY"),
    host=os.getenv("LANGFUSE_HOST", "https://jp.cloud.langfuse.com")
)


class AgentOrchestrator:

    def __init__(self):
        self.session_id = str(uuid.uuid4())
        self.search_engine = SemanticSearchEngine()
        self.beacon = Beacon(self.search_engine, langfuse, self.session_id)
        self.nexus = Nexus(self.search_engine, langfuse, self.session_id)
        self.verse = Verse(self.search_engine, langfuse, self.session_id)
        print(f"[INFO] AgentOrchestrator initialized")
        print(f"  Session ID: {self.session_id}")
        print(f"  Agents: Beacon, Nexus, Verse")

    def run(self):
        print("\n[INFO] Week 4: Single Agent Design - Agent Orchestration")
        print("="*80)
        
        products = get_normalized_products()
        print(f"[INFO] Loaded {len(products)} products")
        
        self.search_engine.embed_products(products)
        print(f"[INFO] Embedded products in vector store")
        
        print("\n" + "="*80)
        print("[AGENT] BEACON - Price Monitoring & Recommendations")
        print("="*80)
        beacon_results = self.beacon.analyze_catalog(products)
        
        for result in beacon_results[:3]:
            print(f"\n{result.product_name}:")
            print(f"  Current Price: ${result.current_price:.2f}")
            print(f"  Competitor Price: ${result.competitor_price:.2f}" if result.competitor_price else "  Competitor Price: N/A")
            print(f"  Recommendation: {result.recommendation}")
            print(f"  Confidence: {result.confidence_score:.2f}")
            print(f"  Reasoning: {result.reasoning}")
        
        print("\n" + "="*80)
        print("[AGENT] NEXUS - Catalog Analysis & Market Comparison")
        print("="*80)
        nexus_results = self.nexus.compare_catalogs(products)
        
        for company, result in nexus_results.items():
            print(f"\n{company}:")
            print(f"  Total Products: {result.total_products}")
            print(f"  Categories: {', '.join(result.categories)}")
            print(f"  Avg Price: ${result.avg_price:.2f}")
            print(f"  Price Range: ${result.price_range['min']:.2f} - ${result.price_range['max']:.2f}")
            print(f"  Competitive Strength: {result.competitive_strength}")
            print(f"  Market Position: {result.market_position}")
            print(f"  Confidence: {result.confidence_score:.2f}")
        
        print("\n" + "="*80)
        print("[AGENT] VERSE - Marketing Content Generation")
        print("="*80)
        verse_results = self.verse.generate_catalog_content(products)
        
        for result in verse_results[:3]:
            print(f"\n{result.product_name}:")
            print(f"  Headline: {result.headline}")
            print(f"  Tone: {result.tone}")
            print(f"  Description: {result.description[:100]}...")
            print(f"  Key Points: {', '.join(result.key_selling_points[:2])}")
            print(f"  Confidence: {result.confidence_score:.2f}")
        
        print("\n" + "="*80)
        print("WEEK 4 CHECKPOINT - VALIDATION")
        print("="*80)
        
        checks = [
            ("Beacon initialized", self.beacon is not None),
            ("Nexus initialized", self.nexus is not None),
            ("Verse initialized", self.verse is not None),
            ("Beacon analyses generated", len(beacon_results) == 12),
            ("Nexus analyses generated", len(nexus_results) == 2),
            ("Verse contents generated", len(verse_results) == 12),
            ("All analyses have confidence scores", all(0 <= a.confidence_score <= 1 for a in beacon_results)),
            ("All analyses have reasoning", all(a.reasoning for a in beacon_results))
        ]
        
        passed = 0
        for check_name, result in checks:
            status = "PASS" if result else "FAIL"
            symbol = "✓" if result else "✗"
            print(f"  [{symbol}] {check_name}: {status}")
            if result:
                passed += 1
        
        print(f"\nWeek 4 Score: {passed}/{len(checks)} checks passed")
        
        if passed == len(checks):
            print("✅ Week 4 Complete! All agents operational.")
        else:
            print(f"⚠️  {len(checks) - passed} checks failed.")
        
        langfuse.flush()
        
        return {
            "beacon_results": beacon_results,
            "nexus_results": nexus_results,
            "verse_results": verse_results
        }


def main():
    orchestrator = AgentOrchestrator()
    results = orchestrator.run()
    return results


if __name__ == "__main__":
    main()
