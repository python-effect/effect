class HTTPRequest(object):
    """
    An HTTP effect request. Default implementation uses treq.
    """

    def __init__(self, method, url, headers=None, data=None):
        self.method = method
        self.url = url
        self.headers = headers
        self.data = data

    def __repr__(self):
        return "HTTPRequest(%r, %r, headers=%r, data=%r)" % (
            self.method, self.url, self.headers, self.data)

    def perform_effect(self, dispatcher):
        import treq
        func = getattr(treq, self.method.lower())
        headers = self.headers.copy() if self.headers is not None else {}
        if 'user-agent' not in headers:
            headers['user-agent'] = ['Pure Snakes Example']
        return func(self.url, headers=headers, data=self.data).addCallback(
            treq.content)
