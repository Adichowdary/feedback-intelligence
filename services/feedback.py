from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from hindsight_client import Hindsight
import uuid
import logging
import os
from config import settings

logger = logging.getLogger(__name__)


class FeedbackService:
    def __init__(self, client: Hindsight, bank_id: str):
        self.client = client
        self.bank_id = bank_id
        # In-memory feedback store guarantees continuous availability and instant stats
        self._feedback_store: List[Dict[str, Any]] = []
        self._hindsight_available: bool = True

    def _build_tags(self, product_area: str, source: str, user_id: Optional[str] = None) -> List[str]:
        """Build tags for feedback item"""
        tags = [
            "feedback",
            f"product_area:{product_area}",
            f"source:{source}"
        ]
        if user_id:
            tags.append(f"user:{user_id}")
        return tags

    def _build_context(self, product_area: str, source: str) -> str:
        """Build context string for Hindsight"""
        return f"user_feedback_{product_area}_{source}"

    def _detect_sentiment(self, text: str) -> str:
        """Helper to classify sentiment from text"""
        t = text.lower()
        negative_words = [
            "fail", "error", "broken", "bug", "timeout", "slow", "sluggish", "worst",
            "frustrat", "crash", "stuck", "terrible", "bad", "unacceptable", "issue",
            "hate", "problem", "cannot", "can't", "blocking", "urgent", "wrong"
        ]
        positive_words = [
            "great", "love", "fast", "instant", "excellent", "improved", "clean",
            "seamless", "amazing", "stable", "smooth", "win", "good", "perfect"
        ]
        
        neg_count = sum(1 for w in negative_words if w in t)
        pos_count = sum(1 for w in positive_words if w in t)
        
        if neg_count > pos_count:
            return "negative"
        elif pos_count > neg_count:
            return "positive"
        return "neutral"

    def _normalize_dt(self, dt: Optional[datetime]) -> datetime:
        """Normalize datetime to timezone-aware UTC datetime"""
        if dt is None:
            return datetime.min.replace(tzinfo=timezone.utc)
        if dt.tzinfo is None:
            return dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)

    def _parse_date(self, date_str: Optional[str]) -> datetime:
        """Parse date string into UTC datetime"""
        if not date_str:
            return datetime.now(timezone.utc)
        try:
            cleaned = str(date_str).replace('Z', '+00:00')
            parsed = datetime.fromisoformat(cleaned)
            return self._normalize_dt(parsed)
        except Exception:
            return datetime.now(timezone.utc)

    async def submit_feedback(
        self,
        text: str,
        product_area: str = "other",
        source: str = "in_app_feedback",
        user_id: Optional[str] = None,
        date: Optional[str] = None
    ) -> Dict[str, Any]:
        """Submit a single feedback item to Hindsight with seamless fallback"""
        
        timestamp = self._parse_date(date)
        date_str = timestamp.isoformat()
        document_id = f"feedback_{uuid.uuid4().hex[:12]}"
        
        metadata = {
            "product_area": product_area,
            "source": source,
        }
        if user_id:
            metadata["user_id"] = user_id
        
        tags = self._build_tags(product_area, source, user_id)
        context = self._build_context(product_area, source)
        sentiment = self._detect_sentiment(text)
        
        stored_item = {
            "id": document_id,
            "document_id": document_id,
            "text": text,
            "product_area": product_area,
            "source": source,
            "user_id": user_id or "anonymous",
            "date": date_str,
            "timestamp": timestamp,
            "sentiment": sentiment,
            "context": context,
            "tags": tags,
            "hindsight_retained": False
        }
        self._feedback_store.append(stored_item)
        
        # Try Hindsight retain (only if a client and a valid API key are available)
        hindsight_key = settings.HINDSIGHT_LLM_API_KEY or os.environ.get("OPENAI_API_KEY")
        if self.client is not None and hindsight_key and "dummy" not in hindsight_key.lower():
            try:
                result = await self.client.aretain(
                    bank_id=self.bank_id,
                    content=text,
                    context=context,
                    timestamp=date_str,
                    document_id=document_id,
                    metadata=metadata,
                    tags=tags
                )
                stored_item["hindsight_retained"] = getattr(result, "success", True)
            except Exception as e:
                logger.info(f"Hindsight retain fallback: {e}")
        else:
            logger.debug("Skipping Hindsight retain (no valid API key) - using local store only")
        
        return {
            "document_id": document_id,
            "success": True,
            "items_count": 1,
            "hindsight_synced": stored_item["hindsight_retained"],
            "product_area": product_area,
            "source": source,
            "date": date_str
        }

    async def submit_feedback_batch(self, items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Submit multiple feedback items in batch with resilience"""
        retain_items = []
        results = []
        
        for item in items:
            timestamp = self._parse_date(item.get("date"))
            date_str = timestamp.isoformat()
            document_id = f"feedback_{uuid.uuid4().hex[:12]}"
            area = item.get("product_area", "other")
            src = item.get("source", "in_app_feedback")
            uid = item.get("user_id")
            txt = item.get("text", "")
            sentiment = self._detect_sentiment(txt)
            
            metadata = {
                "product_area": area,
                "source": src,
            }
            if uid:
                metadata["user_id"] = uid
            
            tags = self._build_tags(area, src, uid)
            context = self._build_context(area, src)
            
            stored_item = {
                "id": document_id,
                "document_id": document_id,
                "text": txt,
                "product_area": area,
                "source": src,
                "user_id": uid or "anonymous",
                "date": date_str,
                "timestamp": timestamp,
                "sentiment": sentiment,
                "context": context,
                "tags": tags,
                "hindsight_retained": False
            }
            self._feedback_store.append(stored_item)
            
            retain_items.append({
                "content": txt,
                "context": context,
                "timestamp": date_str,
                "document_id": document_id,
                "metadata": metadata,
                "tags": tags
            })
            
            results.append({
                "document_id": document_id,
                "success": True,
                "items_count": 1
            })
        
# Batch retain in Hindsight (only if a client and a valid API key are available)
        hindsight_key = settings.HINDSIGHT_LLM_API_KEY or os.environ.get("OPENAI_API_KEY")
        if self.client is not None and hindsight_key and "dummy" not in hindsight_key.lower():
            try:
                await self.client.aretain_batch(
                    bank_id=self.bank_id,
                    items=retain_items,
                    retain_async=False
                )
                for s in self._feedback_store[-len(items):]:
                    s["hindsight_retained"] = True
            except Exception as e:
                logger.info(f"Hindsight batch retain note: {e}")
        else:
            logger.debug("Skipping Hindsight batch retain (no valid API key) - using local store only")
        
        return results

    def get_recent(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Return the most recent feedback submissions safely sorted by UTC datetime"""
        sorted_items = sorted(
            self._feedback_store,
            key=lambda x: self._normalize_dt(x.get("timestamp")),
            reverse=True
        )
        return sorted_items[:limit]

    def get_all(self) -> List[Dict[str, Any]]:
        """Return all stored feedback items"""
        return list(self._feedback_store)

    async def clear_bank(self):
        """Asynchronously attempt to reset or recreate Hindsight bank"""
        self._feedback_store.clear()
        if self.client is None:
            return
        try:
            await self.client.adelete_bank(bank_id=self.bank_id)
            await self.client.acreate_bank(bank_id=self.bank_id)
        except Exception as e:
            logger.info(f"Hindsight bank reset note: {e}")

    def clear(self):
        """Reset the feedback store for clean demo progression"""
        self._feedback_store.clear()

    async def get_stats(self) -> Dict[str, Any]:
        """Get comprehensive statistics about stored feedback"""
        total = len(self._feedback_store)
        product_area_counts: Dict[str, int] = {}
        source_counts: Dict[str, int] = {}
        sentiment_counts = {"positive": 0, "negative": 0, "neutral": 0}
        monthly_counts: Dict[str, int] = {}
        
        for item in self._feedback_store:
            area = item.get("product_area", "other")
            source = item.get("source", "other")
            sentiment = item.get("sentiment", "neutral")
            
            product_area_counts[area] = product_area_counts.get(area, 0) + 1
            source_counts[source] = source_counts.get(source, 0) + 1
            sentiment_counts[sentiment] = sentiment_counts.get(sentiment, 0) + 1
            
            date_str = item.get("date", "")
            if date_str and len(date_str) >= 7:
                month_key = date_str[:7]
                monthly_counts[month_key] = monthly_counts.get(month_key, 0) + 1
        
        sorted_areas = dict(sorted(product_area_counts.items(), key=lambda x: x[1], reverse=True))
        sorted_sources = dict(sorted(source_counts.items(), key=lambda x: x[1], reverse=True))
        sorted_months = dict(sorted(monthly_counts.items(), key=lambda x: x[0]))
        
        top_area = list(sorted_areas.keys())[0] if sorted_areas else "None"
        top_area_count = sorted_areas.get(top_area, 0)
        
        neg_pct = round((sentiment_counts["negative"] / total * 100), 1) if total > 0 else 0
        pos_pct = round((sentiment_counts["positive"] / total * 100), 1) if total > 0 else 0
        neu_pct = round((sentiment_counts["neutral"] / total * 100), 1) if total > 0 else 0

        return {
            "total_memories": total,
            "by_product_area": sorted_areas,
            "by_source": sorted_sources,
            "by_sentiment": sentiment_counts,
            "sentiment_percentages": {
                "negative": neg_pct,
                "positive": pos_pct,
                "neutral": neu_pct
            },
            "monthly_volume": sorted_months,
            "top_product_area": top_area,
            "top_product_area_count": top_area_count,
            "hindsight_bank": self.bank_id
        }