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
