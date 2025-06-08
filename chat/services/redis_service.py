# chat/services/redis_service.py - Enhanced Redis service for chat features
import json
import logging
import redis
from django.conf import settings
from datetime import datetime, timedelta
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)


class RedisChatService:
    def __init__(self):
        self.redis_client = redis.Redis(
            host=getattr(settings, 'REDIS_HOST', 'localhost'),
            port=getattr(settings, 'REDIS_PORT', 6379),
            db=getattr(settings, 'REDIS_DB', 0),
            decode_responses=True,
            socket_connect_timeout=5,
            socket_timeout=5,
            retry_on_timeout=True
        )
        self.default_ttl = 3600  # 1 hour

    def health_check(self) -> Dict[str, str]:
        """Check Redis connection health"""
        try:
            self.redis_client.ping()
            return {'status': 'healthy', 'message': 'Redis connection OK'}
        except Exception as e:
            logger.error(f"Redis health check failed: {str(e)}")
            return {'status': 'unhealthy', 'message': str(e)}

    # Message caching
    def cache_message(self, room_id: str, message_data: Dict) -> bool:
        """Cache a message in Redis with expiration"""
        try:
            key = f"room:{room_id}:message:{message_data['id']}"
            self.redis_client.setex(
                key,
                self.default_ttl,
                json.dumps(message_data)
            )

            # Also add to recent messages list
            recent_key = f"room:{room_id}:messages:recent"
            self.redis_client.lpush(recent_key, json.dumps(message_data))
            self.redis_client.ltrim(recent_key, 0, 99)  # Keep last 100 messages
            self.redis_client.expire(recent_key, self.default_ttl)

            return True
        except Exception as e:
            logger.error(f"Error caching message: {str(e)}")
            return False

    def get_cached_messages(self, room_id: str, limit: int = 50) -> List[Dict]:
        """Get cached messages for a room"""
        try:
            key = f"room:{room_id}:messages:recent"
            messages = self.redis_client.lrange(key, 0, limit - 1)
            return [json.loads(msg) for msg in messages]
        except Exception as e:
            logger.error(f"Error getting cached messages: {str(e)}")
            return []

    def invalidate_message(self, room_id: str, message_id: str) -> bool:
        """Remove a message from cache"""
        try:
            # Remove from individual cache
            key = f"room:{room_id}:message:{message_id}"
            self.redis_client.delete(key)

            # Remove from recent messages list (this is expensive, consider alternatives)
            recent_key = f"room:{room_id}:messages:recent"
            messages = self.redis_client.lrange(recent_key, 0, -1)
            self.redis_client.delete(recent_key)

            for msg_json in messages:
                msg = json.loads(msg_json)
                if msg['id'] != message_id:
                    self.redis_client.rpush(recent_key, msg_json)

            self.redis_client.expire(recent_key, self.default_ttl)
            return True
        except Exception as e:
            logger.error(f"Error invalidating message: {str(e)}")
            return False

    # User presence management
    def set_user_online(self, room_id: str, user_id: str) -> bool:
        """Mark user as online in a room"""
        try:
            key = f"room:{room_id}:online_users"
            timestamp = datetime.now().isoformat()
            self.redis_client.hset(key, user_id, timestamp)
            self.redis_client.expire(key, 300)  # 5 minutes
            return True
        except Exception as e:
            logger.error(f"Error setting user online: {str(e)}")
            return False

    def set_user_offline(self, room_id: str, user_id: str) -> bool:
        """Mark user as offline in a room"""
        try:
            key = f"room:{room_id}:online_users"
            self.redis_client.hdel(key, user_id)

            # Also remove from typing users
            typing_key = f"room:{room_id}:typing_users"
            self.redis_client.hdel(typing_key, user_id)
            return True
        except Exception as e:
            logger.error(f"Error setting user offline: {str(e)}")
            return False

    def get_online_users(self, room_id: str) -> List[str]:
        """Get list of online users in a room"""
        try:
            key = f"room:{room_id}:online_users"
            cutoff_time = datetime.now() - timedelta(minutes=5)

            online_users = []
            users_data = self.redis_client.hgetall(key)

            for user_id, timestamp_str in users_data.items():
                try:
                    timestamp = datetime.fromisoformat(timestamp_str)
                    if timestamp > cutoff_time:
                        online_users.append(user_id)
                    else:
                        # Remove stale entries
                        self.redis_client.hdel(key, user_id)
                except ValueError:
                    # Invalid timestamp, remove entry
                    self.redis_client.hdel(key, user_id)

            return online_users
        except Exception as e:
            logger.error(f"Error getting online users: {str(e)}")
            return []

    # Typing indicators
    def set_user_typing(self, room_id: str, user_id: str) -> bool:
        """Mark user as typing in a room"""
        try:
            key = f"room:{room_id}:typing_users"
            timestamp = datetime.now().isoformat()
            self.redis_client.hset(key, user_id, timestamp)
            self.redis_client.expire(key, 30)  # 30 seconds
            return True
        except Exception as e:
            logger.error(f"Error setting user typing: {str(e)}")
            return False

    def unset_user_typing(self, room_id: str, user_id: str) -> bool:
        """Remove user from typing list"""
        try:
            key = f"room:{room_id}:typing_users"
            self.redis_client.hdel(key, user_id)
            return True
        except Exception as e:
            logger.error(f"Error unsetting user typing: {str(e)}")
            return False

    def get_typing_users(self, room_id: str) -> List[str]:
        """Get list of users currently typing"""
        try:
            key = f"room:{room_id}:typing_users"
            cutoff_time = datetime.now() - timedelta(seconds=30)

            typing_users = []
            users_data = self.redis_client.hgetall(key)

            for user_id, timestamp_str in users_data.items():
                try:
                    timestamp = datetime.fromisoformat(timestamp_str)
                    if timestamp > cutoff_time:
                        typing_users.append(user_id)
                    else:
                        # Remove stale entries
                        self.redis_client.hdel(key, user_id)
                except ValueError:
                    # Invalid timestamp, remove entry
                    self.redis_client.hdel(key, user_id)

            return typing_users
        except Exception as e:
            logger.error(f"Error getting typing users: {str(e)}")
            return []

    # Room statistics
    def increment_message_count(self, room_id: str) -> int:
        """Increment message count for a room"""
        try:
            key = f"room:{room_id}:stats:message_count"
            count = self.redis_client.incr(key)
            self.redis_client.expire(key, 86400)  # 24 hours
            return count
        except Exception as e:
            logger.error(f"Error incrementing message count: {str(e)}")
            return 0

    def get_room_stats(self, room_id: str) -> Dict[str, int]:
        """Get comprehensive room statistics"""
        try:
            message_count_key = f"room:{room_id}:stats:message_count"
            online_users_key = f"room:{room_id}:online_users"
            typing_users_key = f"room:{room_id}:typing_users"

            # Get counts using pipeline for efficiency
            pipe = self.redis_client.pipeline()
            pipe.get(message_count_key)
            pipe.hlen(online_users_key)
            pipe.hlen(typing_users_key)
            results = pipe.execute()

            return {
                'total_messages': int(results[0] or 0),
                'online_users_count': results[1] or 0,
                'typing_users_count': results[2] or 0,
                'last_activity': datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"Error getting room stats: {str(e)}")
            return {
                'total_messages': 0,
                'online_users_count': 0,
                'typing_users_count': 0,
                'last_activity': datetime.now().isoformat()
            }

    def cleanup_room(self, room_id: str) -> bool:
        """Clean up all Redis data for a room"""
        try:
            keys = [
                f"room:{room_id}:*"
            ]

            for pattern in keys:
                keys_to_delete = self.redis_client.keys(pattern)
                if keys_to_delete:
                    self.redis_client.delete(*keys_to_delete)

            logger.info(f"Cleaned up Redis data for room {room_id}")
            return True
        except Exception as e:
            logger.error(f"Error cleaning up room data: {str(e)}")
            return False

    # Rate limiting
    def check_rate_limit(self, user_id: str, action: str, limit: int = 10, window: int = 60) -> bool:
        """Check if user has exceeded rate limit for an action"""
        try:
            key = f"rate_limit:{user_id}:{action}"
            current = self.redis_client.get(key)

            if current is None:
                self.redis_client.setex(key, window, 1)
                return True
            elif int(current) < limit:
                self.redis_client.incr(key)
                return True
            else:
                return False
        except Exception as e:
            logger.error(f"Error checking rate limit: {str(e)}")
            return True  # Allow on error

    # Message search cache
    def cache_search_results(self, query: str, room_id: str, results: List[Dict], ttl: int = 300) -> bool:
        """Cache search results"""
        try:
            key = f"search:{room_id}:{hash(query)}"
            self.redis_client.setex(key, ttl, json.dumps(results))
            return True
        except Exception as e:
            logger.error(f"Error caching search results: {str(e)}")
            return False

    def get_cached_search_results(self, query: str, room_id: str) -> Optional[List[Dict]]:
        """Get cached search results"""
        try:
            key = f"search:{room_id}:{hash(query)}"
            cached = self.redis_client.get(key)
            return json.loads(cached) if cached else None
        except Exception as e:
            logger.error(f"Error getting cached search results: {str(e)}")
            return None


# Create singleton instance
redis_chat_service = RedisChatService()