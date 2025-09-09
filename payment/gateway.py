import uuid
import redis
from typing import Dict, Optional
from django.conf import settings


class MockPaymentGateway:
    """Mock payment gateway for internal testing"""
    
    def __init__(self):
        self.redis_client = redis.Redis(
            host=settings.REDIS_HOST,
            port=int(settings.REDIS_PORT),
            db=int(settings.REDIS_DB),
            decode_responses=True
        )
    
    def create_payment_intent(self, amount_p: int, currency: str = "gbp") -> Dict:
        """
        Create a mock payment intent
        
        Args:
            amount_p: Amount in pence
            currency: Currency code (default: gbp)
            
        Returns:
            Dict with intent_id, client_secret, amount, currency, and status
        """
        # Generate both IDs
        intent_id = f"pi_{uuid.uuid4().hex[:8]}"
        client_secret = f"secret_{uuid.uuid4().hex[:8]}"
        
        return {
            "id": intent_id,  # The public ID (same as intent_id)
            "intent_id": intent_id,  # Internal ID for our system
            "client_secret": client_secret,
            "amount": amount_p,
            "currency": currency,
            "status": "requires_confirmation"
        }
    
    def store_secret_mapping(self, client_secret: str, intent_id: str, expire_seconds: int = 900) -> bool:
        """
        Store the mapping between client_secret and intent_id in Redis
        
        Args:
            client_secret: Client secret (key)
            intent_id: Payment intent ID (value)
            expire_seconds: Expiration time in seconds (default: 15 minutes)
            
        Returns:
            True if stored successfully
        """
        cache_key = f"payment_secret:{client_secret}"
        return self.redis_client.setex(cache_key, expire_seconds, intent_id)
    
    def get_intent_id_from_secret(self, client_secret: str) -> Optional[str]:
        """
        Get the intent_id from client_secret in Redis
        
        Args:
            client_secret: Client secret to look up
            
        Returns:
            Intent ID if found, None if not found or expired
        """
        cache_key = f"payment_secret:{client_secret}"
        return self.redis_client.get(cache_key)
    
    def confirm_payment_intent(self, intent_id: str, amount_p: int) -> Dict:
        """
        Confirm a payment intent (simulate payment processing)
        
        Args:
            intent_id: Payment intent ID to confirm
            amount_p: Amount in pence
            
        Returns:
            Dict with status and optional reason (status: "succeeded" or "failed")
        """
        # Simulate failure if amount ends in 13 pence
        if amount_p % 100 == 13:  # Amount ends in 13 pence
            return {
                "status": "failed",
                "reason": "Insufficient funds"
            }
        else:
            return {
                "status": "succeeded"
            }
    
    def cleanup_secret_mapping(self, client_secret: str) -> bool:
        """
        Remove the secret mapping from Redis after payment completion
        
        Args:
            client_secret: Client secret to remove
            
        Returns:
            True if removed, False if not found
        """
        cache_key = f"payment_secret:{client_secret}"
        return bool(self.redis_client.delete(cache_key))

    def get_client_secret_from_intent_id(self, intent_id: str) -> Optional[str]:
        """
        Get the client_secret from intent_id (reverse lookup)
        This is less efficient but needed for existing payment lookups
        
        Args:
            intent_id: Payment intent ID to look up
            
        Returns:
            Client secret if found, None if not found
        """
        # This is a simple implementation - in production you might want to store both mappings
        # For now, we'll iterate through Redis keys (not ideal for production)
        pattern = "payment_secret:*"
        keys = self.redis_client.keys(pattern)
        
        for key in keys:
            stored_intent_id = self.redis_client.get(key)
            if stored_intent_id == intent_id:
                # Extract client_secret from key
                return key.replace("payment_secret:", "")
        
        return None
