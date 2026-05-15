import uuid
from typing import List, Dict, Any
from langfuse import Langfuse
from .base_models import PriceAnalysis
from .llm_utils import create_pricing_chain

class Beacon:

    def __init__(self, search_engine, langfuse: Langfuse, session_id: str, openrouter_api_key: str, model: str):
        self.search_engine = search_engine
        self.langfuse = langfuse
        self.session_id = session_id
        self.name = 'Beacon'
        self.openrouter_api_key = openrouter_api_key
        self.model = model
        self.chain = create_pricing_chain(openrouter_api_key, model)

    def analyze_product_pricing(self, product: Dict[str, Any]) -> PriceAnalysis:
        trace = self.langfuse.trace(name='beacon_analyze_product', session_id=self.session_id)
        trace.input = {'product_id': product.get('sku'), 'model': self.model}
        try:
            product_name = product.get('product_name', '')
            current_price = product.get('effective_price', 0)
            category = product.get('category', '')
            company = product.get('company', '')
            features = product.get('features', [])
            similar_products = self.search_engine.search_with_filters(product_name, category=category, k=5)
            competitor_prices = [p['effective_price'] for p in similar_products if p['company'] != company and p['effective_price'] > 0]
            competitor_price = min(competitor_prices) if competitor_prices else None
            price_difference = current_price - competitor_price if competitor_price else 0
            competitor_name = 'N/A'
            if similar_products:
                for p in similar_products:
                    if p['company'] != company:
                        competitor_name = p['company']
                        break
            llm_input = {'product_name': product_name, 'current_price': current_price, 'category': category, 'company': company, 'features': ', '.join(features[:5]) if features else 'N/A', 'competitor_name': competitor_name, 'competitor_price': competitor_price or 0, 'price_difference': price_difference}
            llm_output = self.chain.invoke(llm_input)
            recommendation = llm_output.get('recommendation', 'MAINTAIN_PRICE')
            confidence = llm_output.get('confidence_score', 0.5)
            reasoning = llm_output.get('reasoning', 'LLM analysis')
            analysis = PriceAnalysis(product_id=product.get('sku', ''), product_name=product_name, current_price=current_price, competitor_price=competitor_price, price_difference=price_difference, recommendation=recommendation, confidence_score=confidence, reasoning=reasoning)
            trace.output = {'recommendation': recommendation, 'confidence': confidence, 'competitor_price': competitor_price, 'model': self.model}
            return analysis
        except Exception as e:
            print(f'[WARN] Beacon LLM failed: {str(e)}, using fallback logic')
            trace.output = {'error': str(e), 'fallback': True}
            return self._fallback_pricing_analysis(product)

    def _fallback_pricing_analysis(self, product: Dict[str, Any]) -> PriceAnalysis:
        product_name = product.get('product_name', '')
        current_price = product.get('effective_price', 0)
        category = product.get('category', '')
        company = product.get('company', '')
        similar_products = self.search_engine.search_with_filters(product_name, category=category, k=5)
        competitor_prices = [p['effective_price'] for p in similar_products if p['company'] != company and p['effective_price'] > 0]
        competitor_price = min(competitor_prices) if competitor_prices else None
        price_difference = current_price - competitor_price if competitor_price else 0
        if competitor_price is None:
            recommendation = 'BASELINE_PRODUCT'
            confidence = 0.6
            reasoning = 'No direct competitors found'
        elif price_difference > 20:
            recommendation = 'REDUCE_PRICE'
            confidence = 0.85
            reasoning = f'Product priced ${price_difference:.2f} above competitor'
        elif price_difference < -10:
            recommendation = 'INCREASE_PRICE'
            confidence = 0.8
            reasoning = f'Competitive advantage exists, can increase by ${abs(price_difference):.2f}'
        else:
            recommendation = 'MAINTAIN_PRICE'
            confidence = 0.9
            reasoning = 'Price aligned with competitor offerings'
        return PriceAnalysis(product_id=product.get('sku', ''), product_name=product_name, current_price=current_price, competitor_price=competitor_price, price_difference=price_difference, recommendation=recommendation, confidence_score=confidence, reasoning=reasoning)

    def analyze_catalog(self, products: List[Dict[str, Any]]) -> List[PriceAnalysis]:
        trace = self.langfuse.trace(name='beacon_analyze_catalog', session_id=self.session_id)
        trace.input = {'product_count': len(products), 'model': self.model}
        analyses = []
        for product in products:
            analysis = self.analyze_product_pricing(product)
            analyses.append(analysis)
        trace.output = {'analyzed_count': len(analyses), 'reduce_price_count': sum((1 for a in analyses if a.recommendation == 'REDUCE_PRICE')), 'increase_price_count': sum((1 for a in analyses if a.recommendation == 'INCREASE_PRICE')), 'model': self.model}
        return analyses
