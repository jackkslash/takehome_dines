from rest_framework.permissions import BasePermission


class APIKeyPermission(BasePermission):
    """
    Custom permission class for API key authentication
    """
    
    def has_permission(self, request, view):
        # Check if the request has been authenticated
        # Our APIKeyAuthentication returns (None, api_key) on success
        # request.auth will be the api_key string if authentication succeeded
        return hasattr(request, 'auth') and request.auth is not None
