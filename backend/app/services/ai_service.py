import json
import os
import hashlib
import redis
import jieba
import dashscope
import httpx
from tenacity import retry, stop_after_attempt, wait_fixed
from typing import Generator, List, Dict, Optional
from http import HTTPStatus
from ..config import settings

try:
    from openai import OpenAI  # Optional: use if available
except Exception:
    OpenAI = None

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
        return redis_client.get(key)

    def cache_answer(self, question: str, answer: str):
        if not redis_client:
            return
        key = self._get_cache_key(question)
        redis_client.setex(key, 3600, answer) # 1 hour

    def get_history(self, user_id: str) -> List[Dict]:
        if not redis_client:
            return []
        key = self._get_history_key(user_id)
        history_json = redis_client.get(key)
        if history_json:
            return json.loads(history_json)
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
        redis_client.setex(key, 86400, json.dumps(history)) # 24 hours

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


class DashscopeOpenAIClient:
    def __init__(self):
        self.api_key = settings.DASHSCOPE_API_KEY
        self.base_url = "https://dashscope.aliyuncs.com/compatible-mode/v1"
        # Sensitive words list (Mock)
        self.sensitive_words = ["暴力", "色情", "赌博"]
        self.model = "qwen-plus"
        # Optional OpenAI client if library exists
        self._openai_client: Optional[object] = None
        if OpenAI and self.api_key:
            try:
                self._openai_client = OpenAI(api_key=self.api_key, base_url=self.base_url)
            except Exception:
                self._openai_client = None

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
        return redis_client.get(key)

    def cache_answer(self, question: str, answer: str):
        if not redis_client:
            return
        key = self._get_cache_key(question)
        redis_client.setex(key, 3600, answer)

    def get_history(self, user_id: str) -> List[Dict]:
        if not redis_client:
            return []
        key = self._get_history_key(user_id)
        history_json = redis_client.get(key)
        if history_json:
            return json.loads(history_json)
        return []

    def update_history(self, user_id: str, question: str, answer: str):
        if not redis_client:
            return
        key = self._get_history_key(user_id)
        history = self.get_history(user_id)
        history.append({"role": "user", "content": question})
        history.append({"role": "assistant", "content": answer})
        if len(history) > 20:
            history = history[-20:]
        redis_client.setex(key, 86400, json.dumps(history))

    @retry(stop=stop_after_attempt(2), wait=wait_fixed(1))
    def call_stream_api(
        self,
        user_id: str,
        question: str,
        history_flag: bool,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
    ) -> Generator[str, None, None]:
        if self._check_sensitive(question):
            yield "data: {\"content\": \"抱歉，您的问题包含敏感词，暂无法回答。\"}\n\n"
            return

        cached = self.get_cached_answer(question)
        if cached:
            yield f"data: {json.dumps({'content': cached}, ensure_ascii=False)}\n\n"
            return

        messages = []
        if history_flag:
            messages = self.get_history(user_id)
        messages.append({"role": "user", "content": question})

        # Allow per-call override from DB-configured admin settings
        api_key = (api_key or self.api_key or "").strip()
        base_url = (base_url or self.base_url or "").rstrip("/")
        use_model = (model or self.model or "").strip() or self.model

        try:
            if OpenAI and api_key and base_url:
                try:
                    client = OpenAI(api_key=api_key, base_url=base_url)
                except Exception:
                    client = None
            else:
                client = None

            if client:
                completion = client.chat.completions.create(
                    model=use_model,
                    messages=messages,
                    stream=False,
                )
                # OpenAI SDK returns pydantic-like object
                # Extract message content
                try:
                    content = completion.choices[0].message.content
                except Exception:
                    content = json.dumps(completion.model_dump(), ensure_ascii=False)
                self.cache_answer(question, content)
                self.update_history(user_id, question, content)
                yield f"data: {json.dumps({'content': content}, ensure_ascii=False)}\n\n"
                return

            # Fallback: HTTP call via httpx
            payload = {
                "model": use_model,
                "messages": messages,
                "stream": False
            }
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }
            with httpx.Client(base_url=base_url, timeout=30) as client:
                resp = client.post("/chat/completions", json=payload, headers=headers)
                if resp.status_code != 200:
                    try:
                        err = resp.json()
                        msg = err.get("error", {}).get("message") or str(err)
                    except Exception:
                        msg = resp.text
                    yield f"data: {json.dumps({'content': f'Error: {msg}'}, ensure_ascii=False)}\n\n"
                    return
                data = resp.json()
                # Try OpenAI style parsing
                content = None
                try:
                    content = data["choices"][0]["message"]["content"]
                except Exception:
                    content = json.dumps(data, ensure_ascii=False)
                self.cache_answer(question, content)
                self.update_history(user_id, question, content)
                yield f"data: {json.dumps({'content': content}, ensure_ascii=False)}\n\n"

        except Exception as e:
            print(f"OpenAI Compatible API Error: {e}")
            yield f"data: {json.dumps({'content': '服务暂时不可用，请稍后再试。'}, ensure_ascii=False)}\n\n"


class ArkResponsesClient:
    def __init__(self):
        self.api_key = os.getenv("ARK_API_KEY", "")
        self.base_url = "https://ark.cn-beijing.volces.com/api/v3"
        self.model = "deepseek-v3-2-251201"

    def call_stream_api(
        self,
        user_id: str,
        question: str,
        history_flag: bool,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
    ) -> Generator[str, None, None]:
        api_key = (api_key or self.api_key or "").strip()
        base_url = (base_url or self.base_url or "").rstrip("/")
        use_model = (model or self.model or "").strip() or self.model
        payload = {
            "model": use_model,
            "stream": False,
            "input": [
                {
                    "role": "user",
                    "content": [
                        {"type": "input_text", "text": question}
                    ]
                }
            ]
        }
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        try:
            with httpx.Client(timeout=30) as client:
                resp = client.post(f"{base_url}/responses", json=payload, headers=headers)
                if resp.status_code != 200:
                    try:
                        err = resp.json()
                        msg = err.get("error", {}).get("message") or str(err)
                    except Exception:
                        msg = resp.text
                    yield f"data: {json.dumps({'content': f'Error: {msg}'}, ensure_ascii=False)}\n\n"
                    return
                data = resp.json()
                try:
                    content = data.get("output", {}).get("choices", [{}])[0].get("message", {}).get("content", "")
                except Exception:
                    content = json.dumps(data, ensure_ascii=False)
                yield f"data: {json.dumps({'content': content or ''}, ensure_ascii=False)}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'content': '服务暂时不可用，请稍后再试。'}, ensure_ascii=False)}\n\n"
