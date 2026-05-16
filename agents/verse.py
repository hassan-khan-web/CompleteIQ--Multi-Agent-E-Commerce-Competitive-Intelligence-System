from typing import List, Dict, Any
from langfuse import Langfuse
from .base_models import MarketingContent
from .llm_utils import create_content_chain, _rate_limited_invoke

class Verse:

    def __init__(self, search_engine, langfuse: Langfuse, session_id: str, openrouter_api_key: str, model: str):
        self.search_engine = search_engine
        self.langfuse = langfuse
        self.session_id = session_id
        self.name = 'Verse'
        self.openrouter_api_key = openrouter_api_key
        self.model = model
        self.chain = create_content_chain(openrouter_api_key, model)

    def generate_product_content(self, product: Dict[str, Any]) -> MarketingContent:
        trace = None
        if self.langfuse:
            trace = self.langfuse.trace(name='verse_generate_product', session_id=self.session_id)
            trace.input = {'product_id': product.get('sku'), 'model': self.model}
        try:
            product_id = product.get('sku', '')
            product_name = product.get('product_name', '')
            category = product.get('category', '')
            price = product.get('effective_price', 0)
            features = product.get('features', [])
            company = product.get('company', '')
            similar_products = self.search_engine.search_with_filters(product_name, category=category, k=5)
            competitor_name = 'N/A'
            competitor_price = 0
            advantages = []
            if similar_products:
                for p in similar_products:
                    if p['company'] != company:
                        competitor_name = p['company']
                        competitor_price = p.get('effective_price', 0)
                        our_features = set(features)
                        competitor_features = set(p.get('features', []))
                        advantages = list(our_features - competitor_features)
                        break
            if price < 100:
                tone = 'casual_accessible'
                target_audience = 'budget-conscious consumers'
            elif price > 200:
                tone = 'premium_sophisticated'
                target_audience = 'premium buyers seeking excellence'
            else:
                tone = 'professional'
                target_audience = 'value-focused consumers'
            llm_input = {'product_name': product_name, 'category': category, 'price': price, 'features': ', '.join(features[:5]) if features else 'quality product', 'company': company, 'competitor_name': competitor_name, 'competitor_price': competitor_price, 'advantages': ', '.join(advantages[:3]) if advantages else 'premium features', 'target_audience': target_audience}
            llm_output = _rate_limited_invoke(self.chain, llm_input)
            headline = llm_output.get('headline', f'{product_name}: Premium Choice')
            description = llm_output.get('description', f'Discover {product_name} - innovation meets quality.')
            key_points = llm_output.get('key_selling_points', features[:4])
            call_to_action = llm_output.get('call_to_action', 'Order Now')
            confidence = llm_output.get('confidence_score', 0.88)
            content = MarketingContent(product_id=product_id, product_name=product_name, category=category, headline=headline, description=description, key_selling_points=key_points, tone=tone, confidence_score=confidence, reasoning=f'LLM-generated content for {category} targeting {target_audience}')
            if trace:
                trace.output = {'headline': headline, 'tone': tone, 'key_points_count': len(key_points), 'model': self.model}
            return content
        except Exception as e:
            print(f'[WARN] Verse LLM failed: {str(e)}, using fallback logic')
            if trace:
                trace.output = {'error': str(e), 'fallback': True}
            return self._fallback_product_content(product)

    def _fallback_product_content(self, product: Dict[str, Any]) -> MarketingContent:
        product_id = product.get('sku', '')
        product_name = product.get('product_name', '')
        category = product.get('category', '')
        price = product.get('effective_price', 0)
        features = product.get('features', [])
        if price < 100:
            tone = 'casual_accessible'
        elif price > 200:
            tone = 'premium_sophisticated'
        else:
            tone = 'professional'
        if 'headphones' in product_name.lower() or 'earbuds' in product_name.lower():
            headline = f'{product_name}: Premium Audio Experience'
            key_points = ['Crystal clear sound quality', 'Long battery life', 'Comfortable fit', 'Wireless connectivity']
        elif 'watch' in product_name.lower():
            headline = f'{product_name}: Your Fitness & Health Companion'
            key_points = ['Advanced health monitoring', 'All-day battery life', 'Water resistant design', 'Smart notifications']
        elif 'speaker' in product_name.lower():
            headline = f'{product_name}: Portable Sound System'
            key_points = ['Powerful sound output', 'Waterproof design', 'Long battery duration', 'Bluetooth connectivity']
        else:
            headline = f'{product_name}: Innovation in {category}'
            key_points = [f'Feature: {f}' for f in features[:4]]
        description = f'{product_name} delivers exceptional value in the {category} market. '
        description += f'Designed for quality and reliability. '
        description += f'Available at ${price:.2f}, offering competitive pricing and premium features.'
        return MarketingContent(product_id=product_id, product_name=product_name, category=category, headline=headline, description=description, key_selling_points=key_points, tone=tone, confidence_score=0.85, reasoning='Fallback template-based content')

    def generate_catalog_content(self, products: List[Dict[str, Any]]) -> List[MarketingContent]:
        trace = None
        if self.langfuse:
            trace = self.langfuse.trace(name='verse_generate_catalog', session_id=self.session_id)
            trace.input = {'product_count': len(products), 'model': self.model}
        contents = []
        for product in products:
            content = self.generate_product_content(product)
            contents.append(content)
        if trace:
            trace.output = {'generated_count': len(contents), 'model': self.model}
        return contents