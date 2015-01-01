from effect import sync_performer

import requests


@sync_performer
def perform_request_with_requests(dispatcher, http_request):
    """
    A performer for :obj:`HTTPRequest` that uses the ``requests`` library.
    """
    headers = (
        http_request.headers.copy()
        if http_request.headers is not None
        else {})
    if 'user-agent' not in headers:
        headers['user-agent'] = ['Effect example']
    response = requests.request(
        http_request.method.lower(),
        http_request.url,
        headers=headers,
        data=http_request.data)
    return response.content
