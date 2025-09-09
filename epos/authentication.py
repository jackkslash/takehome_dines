from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed
from django.conf import settings


class APIKeyAuthentication(BaseAuthentication):
    """
    Simple API key authentication using X-API-Key header
    """
    
    def authenticate(self, request):
        api_key = request.META.get('HTTP_X_API_KEY')
        
        if not api_key:
            return None
            
        expected_api_key = getattr(settings, 'API_KEY', 'demo')
        
        if api_key != expected_api_key:
            raise AuthenticationFailed('Invalid API key')
            
        # Return a tuple of (user, auth) - we don't need a user for this simple auth
        return (None, api_key)
