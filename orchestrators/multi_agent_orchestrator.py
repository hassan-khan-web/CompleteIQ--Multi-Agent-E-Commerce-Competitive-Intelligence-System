import asyncio
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

@dataclass
class AgentResult:
    agent_name: str
    status: str
    data: Any = None
    error: str | None = None
    execution_time: float = 0.0
    retry_count: int = 0

class MultiAgentOrchestrator:

    def __init__(self, timeout: int=120, max_retries: int=2):
        self.timeout = timeout
        self.max_retries = max_retries
        self.session_id = str(uuid.uuid4())
        self.search_engine = None
        self.beacon = None
        self.nexus = None
        self.verse = None
        self.results = {}
        self.execution_metrics = {'start_time': None, 'end_time': None, 'total_time': 0.0, 'agents_succeeded': 0, 'agents_failed': 0, 'total_retries': 0}

    async def execute_beacon(self, products, retry_count=0):
        try:
            start = datetime.now()
            result = await asyncio.wait_for(asyncio.to_thread(self.beacon.analyze_catalog, products), timeout=self.timeout)
            execution_time = (datetime.now() - start).total_seconds()
            return AgentResult('Beacon', 'success', result, execution_time=execution_time, retry_count=retry_count)
        except Exception as e:
            if retry_count < self.max_retries:
                await asyncio.sleep(2 ** retry_count)
                return await self.execute_beacon(products, retry_count + 1)
            label = 'Timeout' if isinstance(e, TimeoutError) else str(e)
            return AgentResult('Beacon', 'failed', error=label, retry_count=retry_count)

    async def execute_nexus(self, products, retry_count=0):
        try:
            start = datetime.now()
            result = await asyncio.wait_for(asyncio.to_thread(self.nexus.compare_catalogs, products), timeout=self.timeout)
            execution_time = (datetime.now() - start).total_seconds()
            return AgentResult('Nexus', 'success', result, execution_time=execution_time, retry_count=retry_count)
        except Exception as e:
            if retry_count < self.max_retries:
                await asyncio.sleep(2 ** retry_count)
                return await self.execute_nexus(products, retry_count + 1)
            label = 'Timeout' if isinstance(e, TimeoutError) else str(e)
            return AgentResult('Nexus', 'failed', error=label, retry_count=retry_count)

    async def execute_verse(self, products, retry_count=0):
        try:
            start = datetime.now()
            result = await asyncio.wait_for(asyncio.to_thread(self.verse.generate_catalog_content, products), timeout=self.timeout)
            execution_time = (datetime.now() - start).total_seconds()
            return AgentResult('Verse', 'success', result, execution_time=execution_time, retry_count=retry_count)
        except Exception as e:
            if retry_count < self.max_retries:
                await asyncio.sleep(2 ** retry_count)
                return await self.execute_verse(products, retry_count + 1)
            label = 'Timeout' if isinstance(e, TimeoutError) else str(e)
            return AgentResult('Verse', 'failed', error=label, retry_count=retry_count)

    async def run_async(self, products):
        """Run agents sequentially to respect rate limits on free-tier APIs."""
        if not all([self.beacon, self.nexus, self.verse]):
            raise RuntimeError('Agents are not configured on orchestrator')
        self.execution_metrics['start_time'] = datetime.now().isoformat()

        # Run sequentially: Nexus (2 calls) → Beacon (12 calls) → Verse (12 calls)
        # This keeps total calls spread out via the global rate limiter
        print('[INFO] Running Nexus (market positioning)...')
        nexus_result = await self.execute_nexus(products)
        self.results[nexus_result.agent_name.lower()] = nexus_result

        print('[INFO] Running Beacon (pricing analysis)...')
        beacon_result = await self.execute_beacon(products)
        self.results[beacon_result.agent_name.lower()] = beacon_result

        print('[INFO] Running Verse (marketing content)...')
        verse_result = await self.execute_verse(products)
        self.results[verse_result.agent_name.lower()] = verse_result

        for result in [nexus_result, beacon_result, verse_result]:
            if result.status == 'success':
                self.execution_metrics['agents_succeeded'] += 1
            else:
                self.execution_metrics['agents_failed'] += 1
            self.execution_metrics['total_retries'] += result.retry_count

        self.execution_metrics['end_time'] = datetime.now().isoformat()
        start = datetime.fromisoformat(self.execution_metrics['start_time'])
        end = datetime.fromisoformat(self.execution_metrics['end_time'])
        self.execution_metrics['total_time'] = (end - start).total_seconds()

    def run(self, products):
        asyncio.run(self.run_async(products))

    def aggregate_results(self):
        beacon_result = self.results.get('beacon')
        nexus_result = self.results.get('nexus')
        verse_result = self.results.get('verse')
        beacon_data = beacon_result.data if beacon_result and beacon_result.status == 'success' else None
        nexus_data = nexus_result.data if nexus_result and nexus_result.status == 'success' else None
        verse_data = verse_result.data if verse_result and verse_result.status == 'success' else None
        beacon_insights = {'status': beacon_result.status if beacon_result else 'unknown', 'analyses_count': len(beacon_data) if beacon_data else 0, 'recommendations': {}}
        if beacon_data:
            for analysis in beacon_data:
                beacon_insights['recommendations'][analysis.recommendation] = beacon_insights['recommendations'].get(analysis.recommendation, 0) + 1
        market_analysis = {'status': nexus_result.status if nexus_result else 'unknown', 'companies_analyzed': len(nexus_data) if nexus_data else 0, 'companies': {}}
        if nexus_data:
            for company, analysis in nexus_data.items():
                market_analysis['companies'][company] = {'products': analysis.total_products, 'positioning': analysis.competitive_strength}
        content_metrics = {'status': verse_result.status if verse_result else 'unknown', 'content_generated': len(verse_data) if verse_data else 0, 'tones': {}}
        if verse_data:
            for content in verse_data:
                content_metrics['tones'][content.tone] = content_metrics['tones'].get(content.tone, 0) + 1
        overall_status = 'SUCCESS' if self.execution_metrics['agents_failed'] == 0 else 'PARTIAL_SUCCESS' if self.execution_metrics['agents_succeeded'] > 0 else 'FAILED'
        return {
            'session_id': self.session_id,
            'execution_metrics': self.execution_metrics,
            'beacon': {
                'status': beacon_result.status if beacon_result else 'unknown',
                'execution_time': beacon_result.execution_time if beacon_result else 0.0,
                'error': beacon_result.error if beacon_result and beacon_result.error else None,
                'data': beacon_data,
            },
            'nexus': {
                'status': nexus_result.status if nexus_result else 'unknown',
                'execution_time': nexus_result.execution_time if nexus_result else 0.0,
                'error': nexus_result.error if nexus_result and nexus_result.error else None,
                'data': nexus_data,
            },
            'verse': {
                'status': verse_result.status if verse_result else 'unknown',
                'execution_time': verse_result.execution_time if verse_result else 0.0,
                'error': verse_result.error if verse_result and verse_result.error else None,
                'data': verse_data,
            },
            'summary': {
                'beacon_insights': beacon_insights,
                'market_analysis': market_analysis,
                'content_metrics': content_metrics,
                'overall_status': overall_status,
            },
        }