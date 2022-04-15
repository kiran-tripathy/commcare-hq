from django.utils.decorators import method_decorator
from django.utils.deprecation import MiddlewareMixin
from django.views.decorators.debug import sensitive_post_parameters

from .api import set_request


class GlobalRequestMiddleware(MiddlewareMixin):

    @method_decorator(sensitive_post_parameters('password'))
    def process_request(self, request):
        set_request(request)

    def process_response(self, request, response):
        set_request(None)
        #response['Content-Security-Policy'] = "'self' https://dimagi-demo.my.connect.aws/"
        return response
