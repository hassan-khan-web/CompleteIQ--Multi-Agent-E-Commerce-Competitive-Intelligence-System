import os
import sys
import json
import re
import uuid
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from dotenv import load_dotenv
import pandas as pd
import numpy as np
from openai import OpenAI
from langfuse import Langfuse
load_dotenv()
langfuse = Langfuse(public_key=os.getenv('LANGFUSE_PUBLIC_KEY'), secret_key=os.getenv('LANGFUSE_SECRET_KEY'), host=os.getenv('LANGFUSE_HOST', 'https://jp.cloud.langfuse.com'))
openai_client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
SESSION_ID = str(uuid.uuid4())
COMPANY_X_CATALOG = {'company': 'Company X', 'description': 'Premium consumer electronics brand', 'products': [{'category': 'Wireless Headphones', 'product_name': 'Headphones X1', 'price': 99.99, 'currency': 'USD', 'features': ['Bluetooth 5.0', 'Noise Cancelling', '20h Battery', 'Foldable'], 'discount': '10% off', 'availability': 'In Stock', 'sku': 'X1-HP-001'}, {'category': 'Wireless Headphones', 'product_name': 'Headphones X2 Pro', 'price': 149.99, 'currency': 'USD', 'features': ['Bluetooth 5.2', 'Advanced ANC', '30h Battery', 'Foldable', 'USB-C', 'Multipoint'], 'discount': None, 'availability': 'In Stock', 'sku': 'X2-HP-002'}, {'category': 'Smart Watches', 'product_name': 'Watch X1', 'price': 199.99, 'currency': 'USD', 'features': ['Heart Rate', 'GPS', '5 Day Battery', 'Water Resistant', 'Sleep Tracking'], 'discount': '15% off', 'availability': 'In Stock', 'sku': 'X1-SW-001'}, {'category': 'Smart Watches', 'product_name': 'Watch X2 Ultra', 'price': 349.99, 'currency': 'USD', 'features': ['Heart Rate', 'GPS', 'ECG', '10 Day Battery', 'Titanium', 'Dive Mode'], 'discount': None, 'availability': 'Limited Stock', 'sku': 'X2-SW-002'}, {'category': 'Portable Speakers', 'product_name': 'Speaker X1', 'price': 79.99, 'currency': 'USD', 'features': ['Bluetooth 5.0', 'Waterproof', '12h Battery', 'Portable'], 'discount': '20% off', 'availability': 'In Stock', 'sku': 'X1-PS-001'}, {'category': 'Portable Speakers', 'product_name': 'Speaker X2 Max', 'price': 129.99, 'currency': 'USD', 'features': ['Bluetooth 5.1', 'Waterproof', '24h Battery', 'Portable', '360 Audio'], 'discount': None, 'availability': 'In Stock', 'sku': 'X2-PS-002'}]}
COMPANY_Y_CATALOG = {'company': 'Company Y', 'description': 'Value-focused consumer electronics', 'products': [{'category': 'Wireless Headphones', 'product_name': 'Headphones Z1', 'price': 105.0, 'currency': 'USD', 'features': ['Bluetooth 5.2', 'Noise Cancelling', '25h Battery', 'Quick Charge', 'Foldable'], 'discount': '5% off + Free Case', 'availability': 'In Stock', 'sku': 'Z1-HP-001'}, {'category': 'Wireless Headphones', 'product_name': 'Headphones Z2', 'price': 115.0, 'currency': 'USD', 'features': ['Bluetooth 5.2', 'Advanced Noise Cancelling', '30h Battery', 'Waterproof'], 'discount': None, 'availability': 'In Stock', 'sku': 'Z2-HP-002'}, {'category': 'Smart Watches', 'product_name': 'Watch Z1', 'price': 189.99, 'currency': 'USD', 'features': ['Heart Rate', 'GPS', '7 Day Battery', 'Water Resistant', 'Sleep Tracking', 'SpO2'], 'discount': '20% off', 'availability': 'In Stock', 'sku': 'Z1-SW-001'}, {'category': 'Smart Watches', 'product_name': 'Watch Z2 Sport', 'price': 279.99, 'currency': 'USD', 'features': ['Heart Rate', 'GPS', '5 Day Battery', '100+ Workouts', 'Voice Assistant'], 'discount': '10% off', 'availability': 'In Stock', 'sku': 'Z2-SW-002'}, {'category': 'Portable Speakers', 'product_name': 'Speaker Z1', 'price': 69.99, 'currency': 'USD', 'features': ['Bluetooth 5.0', 'Waterproof', '15h Battery', 'Portable'], 'discount': '15% off', 'availability': 'In Stock', 'sku': 'Z1-PS-001'}, {'category': 'Portable Speakers', 'product_name': 'Speaker Z2 Pro', 'price': 119.99, 'currency': 'USD', 'features': ['Bluetooth 5.1', 'Waterproof', '20h Battery', 'Portable', 'Bass Boost'], 'discount': None, 'availability': 'In Stock', 'sku': 'Z2-PS-002'}]}

class TracedProductCatalogProcessor:

    def __init__(self):
        self.processed_products = []
        self.feature_vocabulary = set()

    def parse_discount(self, discount_str: str) -> Tuple[int, str]:
        if not discount_str:
            return (0, 'none')
        discount_str = discount_str.lower()
        percent_match = re.search('(\\d+)\\s*%', discount_str)
        discount_pct = int(percent_match.group(1)) if percent_match else 0
        if 'free case' in discount_str or ('free' in discount_str and '+' in discount_str):
            discount_type = 'bundle'
        elif 'free shipping' in discount_str or 'shipping' in discount_str:
            discount_type = 'shipping'
        elif '%' in discount_str:
            discount_type = 'percentage'
        else:
            discount_type = 'other'
        return (discount_pct, discount_type)

    def normalize_features(self, features: List[str]) -> List[str]:
        normalized = []
        abbreviations = {'anc': 'noise cancelling', 'noise cancelling': 'noise cancelling', 'advanced anc': 'advanced noise cancelling', 'advanced noise cancelling': 'advanced noise cancelling', 'usb-c': 'usb type-c', 'ecg': 'electrocardiogram', 'spo2': 'blood oxygen', 'gps': 'gps', 'bluetooth': 'bluetooth', 'waterproof': 'waterproof', 'water resistant': 'water resistant'}
        for feature in features:
            feat_lower = feature.lower().strip()
            standardized = abbreviations.get(feat_lower, feat_lower)
            normalized.append(standardized)
            self.feature_vocabulary.add(standardized)
        return normalized

    def normalize_product(self, product: Dict, company: str) -> Dict:
        discount_pct, discount_type = self.parse_discount(product.get('discount'))
        base_price = product.get('price', 0)
        effective_price = base_price * (1 - discount_pct / 100)
        raw_features = product.get('features', [])
        normalized_features = self.normalize_features(raw_features)
        feature_count = len(normalized_features)
        price_per_feature = effective_price / feature_count if feature_count > 0 else 0
        normalized = {'company': company, 'category': product.get('category'), 'product_name': product.get('product_name'), 'sku': product.get('sku'), 'base_price': base_price, 'discount_pct': discount_pct, 'discount_type': discount_type, 'discount_text': product.get('discount'), 'effective_price': round(effective_price, 2), 'features': raw_features, 'features_normalized': normalized_features, 'feature_count': feature_count, 'price_per_feature': round(price_per_feature, 2), 'availability': product.get('availability'), 'currency': product.get('currency', 'USD')}
        return normalized

    def process_catalog_with_tracing(self, catalog: Dict) -> List[Dict]:
        company = catalog.get('company', 'Unknown')
        products = catalog.get('products', [])
        trace = langfuse.trace(name=f"process_catalog_{company.replace(' ', '_')}", user_id=company, tags=['catalog-processing', 'week-2'], metadata={'company': company, 'product_count': len(products), 'session_id': SESSION_ID})
        processed = []
        try:
            for idx, product in enumerate(products):
                span = trace.span(name=f'normalize_product_{idx}', input={'product_name': product.get('product_name')}, metadata={'index': idx})
                try:
                    normalized = self.normalize_product(product, company)
                    normalized['product_id'] = f"{company.replace(' ', '')}{idx:03d}"
                    processed.append(normalized)
                    self.processed_products.append(normalized)
                    span.end(output={'product_id': normalized['product_id']}, metadata={'success': True})
                except Exception as e:
                    span.end(metadata={'success': False, 'error': str(e)})
                    raise
            trace.update(output={'processed_count': len(processed), 'feature_vocabulary_size': len(self.feature_vocabulary), 'avg_features_per_product': len(processed) > 0 and sum((p['feature_count'] for p in processed)) / len(processed) or 0})
        except Exception as e:
            trace.end(metadata={'error': str(e)})
            raise
        return processed

    def compare_products(self, product_x: Dict, product_y: Dict) -> Dict:
        price_x = product_x['effective_price']
        price_y = product_y['effective_price']
        price_diff = abs(price_x - price_y)
        price_diff_pct = price_diff / min(price_x, price_y) * 100 if min(price_x, price_y) > 0 else 0
        if price_x < price_y:
            price_advantage = 'X'
        elif price_y < price_x:
            price_advantage = 'Y'
        else:
            price_advantage = 'tie'
        features_x = set(product_x['features_normalized'])
        features_y = set(product_y['features_normalized'])
        common_features = features_x & features_y
        unique_to_x = features_x - features_y
        unique_to_y = features_y - features_x
        count_x = len(features_x)
        count_y = len(features_y)
        if count_x > count_y:
            feature_advantage = 'X'
        elif count_y > count_x:
            feature_advantage = 'Y'
        else:
            feature_advantage = 'tie'
        value_x = product_x['price_per_feature']
        value_y = product_y['price_per_feature']
        if value_x < value_y:
            value_advantage = 'X'
        elif value_y < value_x:
            value_advantage = 'Y'
        else:
            value_advantage = 'tie'
        return {'category': product_x['category'], 'product_x_name': product_x['product_name'], 'product_y_name': product_y['product_name'], 'company_x': product_x['company'], 'company_y': product_y['company'], 'price_x': price_x, 'price_y': price_y, 'price_diff': round(price_diff, 2), 'price_diff_pct': round(price_diff_pct, 2), 'price_advantage': price_advantage, 'features_x': count_x, 'features_y': count_y, 'feature_advantage': feature_advantage, 'unique_to_x': list(unique_to_x), 'unique_to_y': list(unique_to_y), 'common_features': list(common_features), 'value_x': round(value_x, 2), 'value_y': round(value_y, 2), 'value_advantage': value_advantage}
