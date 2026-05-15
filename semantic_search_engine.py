import os
import json
import uuid
import hashlib
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from dotenv import load_dotenv
import chromadb
import requests
from langfuse import Langfuse
load_dotenv()
langfuse = Langfuse(public_key=os.getenv('LANGFUSE_PUBLIC_KEY'), secret_key=os.getenv('LANGFUSE_SECRET_KEY'), host=os.getenv('LANGFUSE_HOST', 'https://jp.cloud.langfuse.com'))
OPENROUTER_API_KEY = os.getenv('OPENROUTER_API_KEY', os.getenv('OPENAI_API_KEY', ''))
OPENROUTER_BASE_URL = 'https://openrouter.ai/api/v1'
SESSION_ID = str(uuid.uuid4())

def generate_embedding_openrouter(texts: List[str]) -> List[List[float]]:
    if not OPENROUTER_API_KEY:
        print('[WARN] OpenRouter API key not configured, using mock embeddings')
        return [create_mock_embedding(text) for text in texts]
    headers = {'Authorization': f'Bearer {OPENROUTER_API_KEY}', 'Content-Type': 'application/json'}
    payload = {'model': 'openai/text-embedding-3-small', 'input': texts}
    try:
        response = requests.post(f'{OPENROUTER_BASE_URL}/embeddings', headers=headers, json=payload)
        response.raise_for_status()
        data = response.json()
        embeddings = [item['embedding'] for item in data['data']]
        return embeddings
    except requests.exceptions.RequestException as e:
        print(f'[WARN] OpenRouter request failed ({e}), falling back to mock embeddings')
        return [create_mock_embedding(text) for text in texts]

def create_mock_embedding(text: str, seed: int=0) -> List[float]:
    hash_val = int(hashlib.md5((text + str(seed)).encode()).hexdigest(), 16)
    embedding = []
    for i in range(1536):
        val = ((hash_val >> (i % 32)) & 255) / 128.0 - 1.0
        embedding.append(val)
    return embedding

class SemanticSearchEngine:

    def __init__(self, db_path: str='./chroma_db', collection_name: str='products'):
        self.db_path = db_path
        self.collection_name = collection_name
        self.embedding_model = 'openai/text-embedding-3-small'
        self.batch_size = 128
        print(f'[INFO] Initializing SemanticSearchEngine')
        print(f'  Database path: {self.db_path}')
        print(f'  Collection name: {self.collection_name}')
        print(f'  Embedding model: {self.embedding_model}')
        print(f'  API Provider: OpenRouter')
        self.client = chromadb.PersistentClient(path=self.db_path)
        print(f'[INFO] ChromaDB persistent client initialized at {self.db_path}')
        self.collection = self.client.get_or_create_collection(name=self.collection_name, metadata={'hnsw:space': 'cosine'})
        print(f"[INFO] Collection '{self.collection_name}' ready")

    def _generate_embeddings_batch(self, texts: List[str]) -> List[List[float]]:
        trace = langfuse.trace(name='generate_embeddings_batch', session_id=SESSION_ID)
        trace.input = {'text_count': len(texts), 'batch_size': len(texts)}
        try:
            embeddings = generate_embedding_openrouter(texts)
            trace.output = {'embedding_count': len(embeddings), 'dimension': len(embeddings[0]) if embeddings else 0}
            print(f'[INFO] Generated {len(embeddings)} embeddings via OpenRouter')
            return embeddings
        except Exception as e:
            print(f'[ERROR] Embedding generation failed: {e}')
            trace.output = {'error': str(e)}
            raise

    def _create_product_description(self, product: Dict[str, Any]) -> str:
        parts = [product.get('product_name', ''), product.get('category', ''), ' '.join(product.get('features', [])), product.get('company', '')]
        return ' '.join(filter(None, parts))

    def embed_products(self, products: List[Dict[str, Any]]) -> None:
        if not products:
            raise ValueError('Products list cannot be empty')
        trace = langfuse.trace(name='embed_products', session_id=SESSION_ID)
        trace.input = {'product_count': len(products)}
        print(f'[INFO] Starting embedding of {len(products)} products')
        existing_count = self.collection.count()
        if existing_count > 0:
            print(f'[WARN] Collection already contains {existing_count} products')
            print(f'[INFO] Clearing existing products before re-embedding')
            existing_ids = self.collection.get()['ids']
            if existing_ids:
                self.collection.delete(ids=existing_ids)
        total_batches = (len(products) + self.batch_size - 1) // self.batch_size
        for i in range(0, len(products), self.batch_size):
            batch = products[i:i + self.batch_size]
            batch_num = i // self.batch_size + 1
            print(f'[INFO] Processing batch {batch_num}/{total_batches} ({len(batch)} products)')
            descriptions = [self._create_product_description(p) for p in batch]
            embeddings = self._generate_embeddings_batch(descriptions)
            ids = [str(p.get('sku', f'product_{idx}')) for idx, p in enumerate(batch)]
            metadatas = [{'company': p.get('company', ''), 'category': p.get('category', ''), 'product_name': p.get('product_name', ''), 'price': str(p.get('price', 0)), 'effective_price': str(p.get('effective_price', 0)), 'sku': p.get('sku', '')} for p in batch]
            documents = descriptions
            self.collection.upsert(ids=ids, embeddings=embeddings, metadatas=metadatas, documents=documents)
            print(f'[INFO] Stored {len(batch)} products in collection')
        final_count = self.collection.count()
        trace.output = {'total_products_embedded': final_count, 'batches_processed': total_batches}
        print(f'[INFO] Embedding complete. Total products in store: {final_count}')

    def semantic_search(self, query: str, k: int=5) -> List[Dict[str, Any]]:
        trace = langfuse.trace(name='semantic_search', session_id=SESSION_ID)
        trace.input = {'query': query, 'k': k}
        print(f"[INFO] Semantic search: '{query}' (top {k})")
        query_embedding = self._generate_embeddings_batch([query])[0]
        results = self.collection.query(query_embeddings=[query_embedding], n_results=k, include=['embeddings', 'metadatas', 'documents', 'distances'])
        formatted_results = []
        for i in range(len(results['ids'][0])):
            result = {'id': results['ids'][0][i], 'product_name': results['metadatas'][0][i].get('product_name', ''), 'company': results['metadatas'][0][i].get('company', ''), 'category': results['metadatas'][0][i].get('category', ''), 'price': float(results['metadatas'][0][i].get('price', 0)), 'effective_price': float(results['metadatas'][0][i].get('effective_price', 0)), 'document': results['documents'][0][i], 'similarity_score': 1 - results['distances'][0][i]}
            formatted_results.append(result)
        trace.output = {'results_count': len(formatted_results), 'top_result': formatted_results[0]['product_name'] if formatted_results else None, 'top_similarity': formatted_results[0]['similarity_score'] if formatted_results else None}
        print(f'[INFO] Found {len(formatted_results)} results')
        if formatted_results:
            print(f"  Top result: {formatted_results[0]['product_name']} ({formatted_results[0]['similarity_score']:.3f})")
        return formatted_results

    def search_with_filters(self, query: str, company: Optional[str]=None, category: Optional[str]=None, k: int=5) -> List[Dict[str, Any]]:
        trace = langfuse.trace(name='search_with_filters', session_id=SESSION_ID)
        trace.input = {'query': query, 'company': company, 'category': category, 'k': k}
        print(f"[INFO] Filtered search: '{query}'")
        if company:
            print(f'  Filter by company: {company}')
        if category:
            print(f'  Filter by category: {category}')
        query_embedding = self._generate_embeddings_batch([query])[0]
        where_conditions = []
        if company:
            where_conditions.append({'company': company})
        if category:
            where_conditions.append({'category': category})
        where = None
        if where_conditions:
            if len(where_conditions) == 1:
                where = where_conditions[0]
            else:
                where = {'$and': where_conditions}
        results = self.collection.query(query_embeddings=[query_embedding], n_results=k, where=where, include=['embeddings', 'metadatas', 'documents', 'distances'])
        formatted_results = []
        for i in range(len(results['ids'][0])):
            result = {'id': results['ids'][0][i], 'product_name': results['metadatas'][0][i].get('product_name', ''), 'company': results['metadatas'][0][i].get('company', ''), 'category': results['metadatas'][0][i].get('category', ''), 'price': float(results['metadatas'][0][i].get('price', 0)), 'effective_price': float(results['metadatas'][0][i].get('effective_price', 0)), 'document': results['documents'][0][i], 'similarity_score': 1 - results['distances'][0][i]}
            formatted_results.append(result)
        trace.output = {'results_count': len(formatted_results), 'filters_applied': {'company': company, 'category': category}}
        print(f'[INFO] Found {len(formatted_results)} results (with filters)')
        return formatted_results

    def get_product_by_id(self, product_id: str) -> Optional[Dict[str, Any]]:
        trace = langfuse.trace(name='get_product_by_id', session_id=SESSION_ID)
        trace.input = {'product_id': product_id}
        results = self.collection.get(ids=[product_id])
        if results and results['ids']:
            product = {'id': results['ids'][0], 'product_name': results['metadatas'][0].get('product_name', ''), 'company': results['metadatas'][0].get('company', ''), 'category': results['metadatas'][0].get('category', ''), 'price': float(results['metadatas'][0].get('price', 0)), 'effective_price': float(results['metadatas'][0].get('effective_price', 0)), 'sku': results['metadatas'][0].get('sku', ''), 'document': results['documents'][0] if results['documents'] else ''}
            trace.output = {'found': True, 'product_name': product['product_name']}
            print(f"[INFO] Found product: {product['product_name']}")
            return product
        else:
            trace.output = {'found': False}
            print(f'[WARN] Product not found: {product_id}')
            return None

    def get_stats(self) -> Dict[str, Any]:
        trace = langfuse.trace(name='get_stats', session_id=SESSION_ID)
        count = self.collection.count()
        stats = {'total_products': count, 'collection_name': self.collection_name, 'embedding_model': self.embedding_model, 'db_path': self.db_path, 'api_provider': 'OpenRouter'}
        trace.output = stats
        print(f'[INFO] Vector store stats: {stats}')
        return stats

    def clear_store(self) -> None:
        trace = langfuse.trace(name='clear_store', session_id=SESSION_ID)
        existing_ids = self.collection.get()['ids']
        if existing_ids:
            self.collection.delete(ids=existing_ids)
        count = self.collection.count()
        trace.output = {'remaining_products': count}
        print(f'[INFO] Vector store cleared')

def get_normalized_products() -> List[Dict[str, Any]]:
    try:
        from product_catalog_processor import COMPANY_X_CATALOG, COMPANY_Y_CATALOG, TracedProductCatalogProcessor
        processor = TracedProductCatalogProcessor()
        company_x_products = processor.process_catalog_with_tracing(COMPANY_X_CATALOG)
        company_y_products = processor.process_catalog_with_tracing(COMPANY_Y_CATALOG)
        all_products = company_x_products + company_y_products
        print(f'[INFO] Loaded {len(all_products)} products from product_catalog_processor')
        return all_products
    except ImportError:
        print('[WARN] product_catalog_processor not available, using mock data')
        return get_mock_products()

def get_mock_products() -> List[Dict[str, Any]]:
    return [{'company': 'Company X', 'category': 'Wireless Headphones', 'product_name': 'Headphones X1', 'price': 99.99, 'currency': 'USD', 'features': ['bluetooth', 'noise cancelling', 'battery'], 'discount_percent': 10, 'effective_price': 89.99, 'availability': 'In Stock', 'sku': 'X1-HP-001'}, {'company': 'Company X', 'category': 'Wireless Headphones', 'product_name': 'Headphones X2 Pro', 'price': 149.99, 'currency': 'USD', 'features': ['bluetooth', 'advanced anc', 'battery', 'multipoint'], 'discount_percent': 0, 'effective_price': 149.99, 'availability': 'In Stock', 'sku': 'X2-HP-002'}, {'company': 'Company X', 'category': 'Smart Watches', 'product_name': 'Watch X1', 'price': 199.99, 'currency': 'USD', 'features': ['heart rate', 'gps', 'battery', 'water resistant'], 'discount_percent': 15, 'effective_price': 169.99, 'availability': 'In Stock', 'sku': 'X1-SW-001'}, {'company': 'Company X', 'category': 'Smart Watches', 'product_name': 'Watch X2 Ultra', 'price': 349.99, 'currency': 'USD', 'features': ['heart rate', 'gps', 'ecg', 'battery'], 'discount_percent': 0, 'effective_price': 349.99, 'availability': 'Limited Stock', 'sku': 'X2-SW-002'}, {'company': 'Company X', 'category': 'Portable Speakers', 'product_name': 'Speaker X1', 'price': 79.99, 'currency': 'USD', 'features': ['bluetooth', 'waterproof', 'battery'], 'discount_percent': 20, 'effective_price': 63.99, 'availability': 'In Stock', 'sku': 'X1-PS-001'}, {'company': 'Company X', 'category': 'Portable Speakers', 'product_name': 'Speaker X2 Max', 'price': 129.99, 'currency': 'USD', 'features': ['bluetooth', 'waterproof', 'battery', 'audio'], 'discount_percent': 0, 'effective_price': 129.99, 'availability': 'In Stock', 'sku': 'X2-PS-002'}, {'company': 'Company Y', 'category': 'Wireless Headphones', 'product_name': 'Headphones Z1', 'price': 105.0, 'currency': 'USD', 'features': ['bluetooth', 'noise cancelling', 'battery'], 'discount_percent': 5, 'effective_price': 99.75, 'availability': 'In Stock', 'sku': 'Z1-HP-001'}, {'company': 'Company Y', 'category': 'Wireless Headphones', 'product_name': 'Headphones Z2', 'price': 115.0, 'currency': 'USD', 'features': ['bluetooth', 'advanced anc', 'battery'], 'discount_percent': 0, 'effective_price': 115.0, 'availability': 'In Stock', 'sku': 'Z2-HP-002'}, {'company': 'Company Y', 'category': 'Smart Watches', 'product_name': 'Watch Z1', 'price': 189.99, 'currency': 'USD', 'features': ['heart rate', 'gps', 'battery', 'sleep tracking'], 'discount_percent': 20, 'effective_price': 151.99, 'availability': 'In Stock', 'sku': 'Z1-SW-001'}, {'company': 'Company Y', 'category': 'Smart Watches', 'product_name': 'Watch Z2 Sport', 'price': 279.99, 'currency': 'USD', 'features': ['heart rate', 'gps', 'battery', 'workouts'], 'discount_percent': 10, 'effective_price': 251.99, 'availability': 'In Stock', 'sku': 'Z2-SW-002'}, {'company': 'Company Y', 'category': 'Portable Speakers', 'product_name': 'Speaker Z1', 'price': 69.99, 'currency': 'USD', 'features': ['bluetooth', 'waterproof', 'battery'], 'discount_percent': 15, 'effective_price': 59.49, 'availability': 'In Stock', 'sku': 'Z1-PS-001'}, {'company': 'Company Y', 'category': 'Portable Speakers', 'product_name': 'Speaker Z2 Pro', 'price': 119.99, 'currency': 'USD', 'features': ['bluetooth', 'waterproof', 'battery', 'bass'], 'discount_percent': 0, 'effective_price': 119.99, 'availability': 'In Stock', 'sku': 'Z2-PS-002'}]
