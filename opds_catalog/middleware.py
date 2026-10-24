import base64
import binascii
from functools import wraps

from django.http import HttpResponse
from django.contrib import auth
from django.utils import translation
from django.utils.deprecation import MiddlewareMixin

from constance import config


def sopds_auth_required(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if config.SOPDS_AUTH and not request.user.is_authenticated:
            result = BasicAuthMiddleware().process_request(request)
            if result is not None:
                return result
        return view_func(request, *args, **kwargs)
    return wrapper


class BasicAuthMiddleware(object):
    header = "HTTP_AUTHORIZATION"

    def unauthed(self):
        response = HttpResponse("""<html><title>Auth required</title><body>
                            <h1>Authorization Required</h1></body></html>""", content_type="text/html")
        response['WWW-Authenticate'] = 'Basic realm="OPDS"'
        response.status_code = 401
        return response

    def process_request(self,request):
        if not config.SOPDS_AUTH:
            return

        try:
            authentication = request.META[self.header]
        except KeyError:
            return self.unauthed()

        try:
            (auth_meth, auth_data) = authentication.split(' ', 1)
            if 'basic' != auth_meth.lower():
                return self.unauthed()
            username, password = base64.b64decode(auth_data.strip()).decode('utf-8').split(':', 1)
        except (ValueError, UnicodeDecodeError, binascii.Error):
            return self.unauthed()

        user = auth.authenticate(username=username, password=password)
        if user and user.is_active:
            request.user = user
            auth.login(request, user)
            return None

        return self.unauthed()


class SOPDSLocaleMiddleware(MiddlewareMixin):

    def process_request(self, request):
            request.LANG = config.SOPDS_LANGUAGE
            translation.activate(request.LANG)
            request.LANGUAGE_CODE = request.LANG
