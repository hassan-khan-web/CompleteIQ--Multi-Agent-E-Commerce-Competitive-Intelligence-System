from typing import List, Dict, Any
from langfuse import Langfuse

from .base_models import CatalogAnalysis


class Nexus:

    def __init__(self, search_engine, langfuse: Langfuse, session_id: str):
        self.search_engine = search_engine
        self.langfuse = langfuse
        self.session_id = session_id
        self.name = "Nexus"

    def analyze_company_catalog(self, products: List[Dict[str, Any]], company: str) -> CatalogAnalysis:
        trace = self.langfuse.trace(
            name="nexus_analyze_company",
            session_id=self.session_id,
        )
        trace.input = {"company": company, "product_count": len(products)}
        
        company_products = [p for p in products if p.get("company") == company]
        
        if not company_products:
            analysis = CatalogAnalysis(
                company=company,
                total_products=0,
                categories=[],
                avg_price=0,
                price_range={"min": 0, "max": 0},
                competitive_strength="UNKNOWN",
                market_position="NO_DATA",
                confidence_score=0.0,
                reasoning="No products found"
            )
            trace.output = {"status": "no_data"}
            return analysis
        
        categories = list(set(p.get("category", "") for p in company_products if p.get("category")))
        prices = [p.get("effective_price", 0) for p in company_products if p.get("effective_price", 0) > 0]
        
        avg_price = sum(prices) / len(prices) if prices else 0
        min_price = min(prices) if prices else 0
        max_price = max(prices) if prices else 0
        
        low_price_count = sum(1 for p in prices if p < 100)
        high_price_count = sum(1 for p in prices if p > 200)
        
        if high_price_count > len(prices) / 2:
            competitive_strength = "PREMIUM"
        elif low_price_count > len(prices) / 2:
            competitive_strength = "VALUE"
        else:
            competitive_strength = "BALANCED"
        
        market_position = f"{competitive_strength}_MARKET_LEADER"
        confidence = 0.82
        reasoning = f"Analysis based on {len(company_products)} products across {len(categories)} categories"
        
        analysis = CatalogAnalysis(
            company=company,
            total_products=len(company_products),
            categories=categories,
            avg_price=round(avg_price, 2),
            price_range={"min": min_price, "max": max_price, "avg": avg_price},
            competitive_strength=competitive_strength,
            market_position=market_position,
            confidence_score=confidence,
            reasoning=reasoning
        )
        
        trace.output = {
            "total_products": len(company_products),
            "categories": len(categories),
            "competitive_strength": competitive_strength
        }
        
        return analysis

    def compare_catalogs(self, products: List[Dict[str, Any]]) -> Dict[str, CatalogAnalysis]:
        trace = self.langfuse.trace(
            name="nexus_compare_catalogs",
            session_id=self.session_id,
        )
        
        companies = list(set(p.get("company", "") for p in products if p.get("company")))
        trace.input = {"companies": companies}
        
        comparisons = {}
        for company in companies:
            analysis = self.analyze_company_catalog(products, company)
            comparisons[company] = analysis
        
        trace.output = {"compared_companies": len(comparisons)}
        return comparisons
