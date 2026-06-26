from django.shortcuts import redirect
from django.contrib.auth import logout
from django.http import HttpResponse
import re
import time


class BlockedUserMiddleware:
    """Redirect blocked users to login immediately."""
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated and not request.path.startswith('/admin/'):
            try:
                if request.user.profile.is_blocked:
                    logout(request)
                    from django.contrib import messages
                    messages.error(request, "Votre compte a ete bloque. Contactez l'administrateur.")
                    return redirect('/login/')
            except Exception:
                pass
        return self.get_response(request)


class SecurityHeadersMiddleware:
    """Add essential security headers to every response."""
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        response['X-Content-Type-Options'] = 'nosniff'
        response['X-Frame-Options'] = 'DENY'
        response['X-XSS-Protection'] = '1; mode=block'
        response['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        response['Permissions-Policy'] = 'geolocation=(), microphone=(), camera=()'
        return response


class RateLimitMiddleware:
    """Simple in-memory rate limiter for login endpoint."""
    _attempts: dict = {}
    MAX_ATTEMPTS = 10
    WINDOW = 60  # seconds

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.method == 'POST' and request.path in ('/login/', '/admin/login/'):
            ip = self._get_ip(request)
            now = time.time()
            attempts, window_start = self._attempts.get(ip, (0, now))

            if now - window_start > self.WINDOW:
                attempts = 0
                window_start = now

            attempts += 1
            self._attempts[ip] = (attempts, window_start)

            if attempts > self.MAX_ATTEMPTS:
                return HttpResponse(
                    "Trop de tentatives de connexion. Attendez 60 secondes.",
                    status=429,
                    content_type='text/plain; charset=utf-8'
                )
        return self.get_response(request)

    def _get_ip(self, request):
        xff = request.META.get('HTTP_X_FORWARDED_FOR')
        if xff:
            return xff.split(',')[0].strip()
        return request.META.get('REMOTE_ADDR', '0.0.0.0')
