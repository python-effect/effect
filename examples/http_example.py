from effect.twisted import deferred_performer


class HTTPRequest(object):
    """
    An HTTP request intent.
    """

    def __init__(self, method, url, headers=None, data=None):
        self.method = method
        self.url = url
        self.headers = headers
        self.data = data

    def __repr__(self):
        return "HTTPRequest(%r, %r, headers=%r, data=%r)" % (
            self.method, self.url, self.headers, self.data)


@deferred_performer
def treq_http_request(dispatcher, http_request):
    """A performer for :obj:`HTTPRequest` that uses the ``treq`` library."""
    import treq
    headers = (
        http_request.headers.copy()
        if http_request.headers is not None
        else {})
    if 'user-agent' not in headers:
        headers['user-agent'] = ['Effect example']
    d = treq.request(
        http_request.method.lower(),
        http_request.url,
        headers=headers,
        data=http_request.data).addCallback(treq.content)
    return d
