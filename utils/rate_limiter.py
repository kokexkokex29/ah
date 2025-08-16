import asyncio
import aiohttp
import logging
from typing import Optional
import time

logger = logging.getLogger(__name__)

class RateLimitHandler:
    """Handle Discord API rate limiting and connection management"""
    
    def __init__(self):
        self.session: Optional[aiohttp.ClientSession] = None
        self.rate_limit_reset = {}
        self.request_count = {}
        
    async def get_session(self) -> aiohttp.ClientSession:
        """Get or create aiohttp session with proper configuration"""
        if self.session is None or self.session.closed:
            connector = aiohttp.TCPConnector(
                limit=100,
                limit_per_host=30,
                ttl_dns_cache=300,
                use_dns_cache=True,
                keepalive_timeout=30,
                enable_cleanup_closed=True
            )
            
            timeout = aiohttp.ClientTimeout(total=30, connect=10)
            
            self.session = aiohttp.ClientSession(
                connector=connector,
                timeout=timeout,
                headers={
                    'User-Agent': 'Football Club Bot (Discord Bot, v1.0)'
                }
            )
            
        return self.session
    
    async def make_request(self, method: str, url: str, **kwargs):
        """Make an HTTP request with rate limiting"""
        session = await self.get_session()
        
        max_retries = 3
        base_delay = 1
        
        for attempt in range(max_retries):
            try:
                # Check rate limit
                await self._check_rate_limit(url)
                
                async with session.request(method, url, **kwargs) as response:
                    # Update rate limit info
                    self._update_rate_limit_info(url, response.headers)
                    
                    if response.status == 429:
                        # Rate limited
                        retry_after = float(response.headers.get('Retry-After', base_delay * (2 ** attempt)))
                        logger.warning(f"Rate limited, waiting {retry_after} seconds")
                        await asyncio.sleep(retry_after)
                        continue
                        
                    return response
                    
            except aiohttp.ClientError as e:
                logger.error(f"Request error (attempt {attempt + 1}): {e}")
                if attempt == max_retries - 1:
                    raise
                await asyncio.sleep(base_delay * (2 ** attempt))
                
        raise aiohttp.ClientError("Max retries exceeded")
    
    async def _check_rate_limit(self, url: str):
        """Check if we're rate limited for this endpoint"""
        current_time = time.time()
        
        if url in self.rate_limit_reset:
            if current_time < self.rate_limit_reset[url]:
                wait_time = self.rate_limit_reset[url] - current_time
                logger.info(f"Waiting {wait_time:.2f}s for rate limit reset")
                await asyncio.sleep(wait_time)
    
    def _update_rate_limit_info(self, url: str, headers):
        """Update rate limit information from response headers"""
        try:
            if 'X-RateLimit-Reset' in headers:
                reset_time = float(headers['X-RateLimit-Reset'])
                self.rate_limit_reset[url] = reset_time
                
            if 'X-RateLimit-Remaining' in headers:
                remaining = int(headers['X-RateLimit-Remaining'])
                if remaining == 0 and 'X-RateLimit-Reset' in headers:
                    reset_time = float(headers['X-RateLimit-Reset'])
                    self.rate_limit_reset[url] = reset_time
                    
        except (ValueError, KeyError) as e:
            logger.debug(f"Error parsing rate limit headers: {e}")
    
    async def close(self):
        """Clean up resources"""
        if self.session and not self.session.closed:
            await self.session.close()
            logger.info("HTTP session closed")
