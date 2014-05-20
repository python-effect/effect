def get_followers(name):
    req = Request("GET", "http://twitter.com/%s/followers" % name)
    return Callback(req, lambda x: [f['name'] for f in x])

def get_followers_followers(name):
    req = get_followers(name)
    def got_init_followers(names):
        reqs = [get_followers(name) for name in names]
        return Callback(gather(reqs), lambda x: reduce(operator.add, x))
    return Callback(req, got_init_followers)

