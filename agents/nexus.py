from typing import List, Dict, Any
from langfuse import Langfuse
from .base_models import CatalogAnalysis
from .llm_utils import create_market_chain

class Nexus:

    def __init__(self, search_engine, langfuse: Langfuse, session_id: str, openrouter_api_key: str, model: str):
        self.search_engine = search_engine
        self.langfuse = langfuse
        self.session_id = session_id
        self.name = 'Nexus'
        self.openrouter_api_key = openrouter_api_key
        self.model = model
        self.chain = create_market_chain(openrouter_api_key, model)

    def analyze_company_catalog(self, products: List[Dict[str, Any]], company: str) -> CatalogAnalysis:
        trace = self.langfuse.trace(name='nexus_analyze_company', session_id=self.session_id)
        trace.input = {'company': company, 'product_count': len(products), 'model': self.model}
        try:
            company_products = [p for p in products if p.get('company') == company]
            if not company_products:
                analysis = CatalogAnalysis(company=company, total_products=0, categories=[], avg_price=0, price_range={'min': 0, 'max': 0}, competitive_strength='UNKNOWN', market_position='NO_DATA', confidence_score=0.0, reasoning='No products found')
                trace.output = {'status': 'no_data'}
                return analysis
            categories = list(set((p.get('category', '') for p in company_products if p.get('category'))))
            prices = [p.get('effective_price', 0) for p in company_products if p.get('effective_price', 0) > 0]
            avg_price = sum(prices) / len(prices) if prices else 0
            min_price = min(prices) if prices else 0
            max_price = max(prices) if prices else 0
            all_companies = list(set((p.get('company', '') for p in products if p.get('company'))))
            competitor_name = [c for c in all_companies if c != company][0] if len(all_companies) > 1 else 'N/A'
            competitor_products = [p for p in products if p.get('company') == competitor_name]
            competitor_prices = [p.get('effective_price', 0) for p in competitor_products if p.get('effective_price', 0) > 0]
            competitor_avg_price = sum(competitor_prices) / len(competitor_prices) if competitor_prices else 0
            all_features = []
            for p in products:
                all_features.extend(p.get('features', []))
            feature_counts = {}
            for f in all_features:
                feature_counts[f] = feature_counts.get(f, 0) + 1
            top_features = sorted(feature_counts.items(), key=lambda x: x[1], reverse=True)[:5]
            top_features_str = ', '.join([f[0] for f in top_features])
            llm_input = {'company': company, 'total_products': len(company_products), 'categories': ', '.join(categories), 'min_price': min_price, 'max_price': max_price, 'avg_price': avg_price, 'competitor_name': competitor_name, 'competitor_products': len(competitor_products), 'competitor_avg_price': competitor_avg_price, 'top_features': top_features_str, 'market_trends': 'Increasing demand for feature-rich products with competitive pricing'}
            llm_output = self.chain.invoke(llm_input)
            competitive_strength = llm_output.get('competitive_strength', 'BALANCED')
            market_position = llm_output.get('market_position', 'BALANCED_MARKET_POSITION')
            key_insights = llm_output.get('key_insights', [])
            confidence = llm_output.get('confidence_score', 0.82)
            reasoning = llm_output.get('reasoning', 'LLM market analysis')
            analysis = CatalogAnalysis(company=company, total_products=len(company_products), categories=categories, avg_price=round(avg_price, 2), price_range={'min': min_price, 'max': max_price, 'avg': avg_price}, competitive_strength=competitive_strength, market_position=market_position, confidence_score=confidence, reasoning=reasoning)
            trace.output = {'total_products': len(company_products), 'categories': len(categories), 'competitive_strength': competitive_strength, 'model': self.model}
            return analysis
        except Exception as e:
            print(f'[WARN] Nexus LLM failed: {str(e)}, using fallback logic')
            trace.output = {'error': str(e), 'fallback': True}
            return self._fallback_catalog_analysis(products, company)

    def _fallback_catalog_analysis(self, products: List[Dict[str, Any]], company: str) -> CatalogAnalysis:
        company_products = [p for p in products if p.get('company') == company]
        if not company_products:
            return CatalogAnalysis(company=company, total_products=0, categories=[], avg_price=0, price_range={'min': 0, 'max': 0}, competitive_strength='UNKNOWN', market_position='NO_DATA', confidence_score=0.0, reasoning='No products found')
        categories = list(set((p.get('category', '') for p in company_products if p.get('category'))))
        prices = [p.get('effective_price', 0) for p in company_products if p.get('effective_price', 0) > 0]
        avg_price = sum(prices) / len(prices) if prices else 0
        min_price = min(prices) if prices else 0
        max_price = max(prices) if prices else 0
        low_price_count = sum((1 for p in prices if p < 100))
        high_price_count = sum((1 for p in prices if p > 200))
        if high_price_count > len(prices) / 2:
            competitive_strength = 'PREMIUM'
        elif low_price_count > len(prices) / 2:
            competitive_strength = 'VALUE'
        else:
            competitive_strength = 'BALANCED'
        market_position = f'{competitive_strength}_MARKET_LEADER'
        confidence = 0.82
        reasoning = f'Analysis based on {len(company_products)} products across {len(categories)} categories'
        return CatalogAnalysis(company=company, total_products=len(company_products), categories=categories, avg_price=round(avg_price, 2), price_range={'min': min_price, 'max': max_price, 'avg': avg_price}, competitive_strength=competitive_strength, market_position=market_position, confidence_score=confidence, reasoning=reasoning)

    def compare_catalogs(self, products: List[Dict[str, Any]]) -> Dict[str, CatalogAnalysis]:
        trace = self.langfuse.trace(name='nexus_compare_catalogs', session_id=self.session_id)
        companies = list(set((p.get('company', '') for p in products if p.get('company'))))
        trace.input = {'companies': companies, 'model': self.model}
        comparisons = {}
        for company in companies:
            analysis = self.analyze_company_catalog(products, company)
            comparisons[company] = analysis
        trace.output = {'compared_companies': len(comparisons), 'model': self.model}
        return comparisons