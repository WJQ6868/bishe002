import json
import hashlib
import redis
import jieba
import dashscope
from tenacity import retry, stop_after_attempt, wait_fixed
from typing import Generator, List, Tuple, Dict
from http import HTTPStatus
from ..config import settings

# Initialize Redis
try:
    redis_client = redis.Redis(
        host=settings.REDIS_HOST,
        port=settings.REDIS_PORT,
        db=settings.REDIS_DB,
        password=settings.REDIS_PASSWORD,
        decode_responses=True
    )
except Exception as e:
    print(f"Redis connection failed: {e}")
    redis_client = None

class QwenClient:
    def __init__(self):
        self.api_key = settings.DASHSCOPE_API_KEY
        dashscope.api_key = self.api_key
        # Sensitive words list (Mock)
        self.sensitive_words = ["暴力", "色情", "赌博"] 
    
    def _disable_redis(self):
        global redis_client
        redis_client = None

    def _check_sensitive(self, text: str) -> bool:
        words = jieba.lcut(text)
        for word in words:
            if word in self.sensitive_words:
                return True
        return False

    def _get_cache_key(self, question: str) -> str:
        hash_obj = hashlib.md5(question.encode('utf-8'))
        return f"ai:qa:{hash_obj.hexdigest()}"

    def _get_history_key(self, user_id: str) -> str:
        return f"ai:chat:{user_id}"

    def get_cached_answer(self, question: str) -> str:
        if not redis_client:
            return None
        key = self._get_cache_key(question)
        try:
            return redis_client.get(key)
        except Exception:
            # Redis unavailable; disable cache to avoid crashing stream
            self._disable_redis()
            return None

    def cache_answer(self, question: str, answer: str):
        if not redis_client:
            return
        key = self._get_cache_key(question)
        try:
            redis_client.setex(key, 3600, answer) # 1 hour
        except Exception:
            self._disable_redis()

    def get_history(self, user_id: str) -> List[Dict]:
        if not redis_client:
            return []
        key = self._get_history_key(user_id)
        try:
            history_json = redis_client.get(key)
            if history_json:
                return json.loads(history_json)
            return []
        except Exception:
            self._disable_redis()
            return []

    def update_history(self, user_id: str, question: str, answer: str):
        if not redis_client:
            return
        key = self._get_history_key(user_id)
        history = self.get_history(user_id)
        history.append({"role": "user", "content": question})
        history.append({"role": "assistant", "content": answer})
        # Keep last 10 rounds to avoid token limit
        if len(history) > 20:
            history = history[-20:]
        try:
            redis_client.setex(key, 86400, json.dumps(history)) # 24 hours
        except Exception:
            self._disable_redis()

    @retry(stop=stop_after_attempt(2), wait=wait_fixed(1))
    def call_stream_api(self, user_id: str, question: str, history_flag: bool) -> Generator[str, None, None]:
        if self._check_sensitive(question):
            yield "data: {\"content\": \"抱歉，您的问题包含敏感词，暂无法回答。\"}\n\n"
            return

        # Check cache first (if not needing history context strictly, or if exact match)
        # For multi-turn, cache might be tricky. 
        # Requirement says: "Cache answer (key: ai:qa:{question_hash})". 
        # This implies simple QA cache. If history is important, this cache might be invalid.
        # We will check cache only if history_flag is False or history is empty, 
        # OR we assume the cache is for the exact question regardless of context (which is a simplification).
        # Let's follow the prompt: "Cache query... if hit return".
        
        cached = self.get_cached_answer(question)
        if cached:
            # Simulate stream for cached response
            yield f"data: {json.dumps({'content': cached}, ensure_ascii=False)}\n\n"
            return

        messages = []
        if history_flag:
            messages = self.get_history(user_id)
        
        messages.append({"role": "user", "content": question})

        try:
            responses = dashscope.Generation.call(
                model=dashscope.Generation.Models.qwen_turbo,
                messages=messages,
                result_format='message',
                stream=True,
                incremental_output=True  # Important for real streaming
            )

            full_answer = ""
            for response in responses:
                if response.status_code == HTTPStatus.OK:
                    content = response.output.choices[0]['message']['content']
                    full_answer += content
                    yield f"data: {json.dumps({'content': content}, ensure_ascii=False)}\n\n"
                else:
                    yield f"data: {json.dumps({'content': f'Error: {response.message}'}, ensure_ascii=False)}\n\n"
            
            # Cache the full answer
            self.cache_answer(question, full_answer)
            # Update history
            self.update_history(user_id, question, full_answer)

        except Exception as e:
            print(f"API Error: {e}")
            yield f"data: {json.dumps({'content': '服务暂时不可用，请稍后再试。'}, ensure_ascii=False)}\n\n"
