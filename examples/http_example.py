
import treq
import operator

class Request(object):
    op_type = 'http'
    def __init__(self, method, url, headers=None, data=None):
        self.method = method
        self.url = url
        self.headers = headers
        self.data = data

def schedule_http_BANG(request):
    func = getattr(treq, request.method.lower())
    return func(request.url, headers=request.headers, data=request.data)

