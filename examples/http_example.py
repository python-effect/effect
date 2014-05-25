class HTTPRequest(object):
    """
    An HTTP effect request. Default implementation uses treq.
    """

    def __init__(self, method, url, headers=None, data=None):
        self.method = method
        self.url = url
        self.headers = headers
        self.data = data

    def perform_effect(self, handlers):
        import treq
        func = getattr(treq, self.method.lower())
        return func(self.url, headers=self.headers, data=self.data)
