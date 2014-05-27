#Pure Snakes

##Requirements

I want to make all of these properties hold

- represent effects in a purely functional way
- represent processing on the *result* of effects in a purely functional way
- binding the production of the effect to the post-processing of the effect in one clean abstraction
- test those abstractions without executing effects
- use those abstractions in new functions
- limit the knowledge of tests to the same knowledge of the code-under-test
- limit the implementation specificity of the tests to avoid ordering concerns and unduly affecting distant code (i.e., no patching or mocking)
- The implementations of effects should be replaceable; async vs sync should not matter.


## A Story

Whenever I write software, I often have a feeling in the back of my head that I'm doing things in a hacky way.

Let's say we want a function that fetches the twitter followers of a user, given that user's name. The function should basically be defined like this (in pseudo-code):

    get-followers(name) ->
      HTTP.GET http://twitter.com/$name/followers

This is pretty much the ideal level of abstraction for this function; something else (HTTP.GET) takes care of HTTP and IO. The only thing it needs to do is describe the HTTP request to make.

What's the ideal *test* for this function? Well, we in the Python community often resort to mocking:

    test get-followers ->
      replace the HTTP module with a mock object
      expect a call to HTTP.GET with arguments http://twitter.com/radix/followers
        returning a dummy value
      assert get-followers('radix') returns the dummy value

This isn't too bad as far as our layers of abstractions are concerned, but it is unfortunate that we have to patch the HTTP library to test our function. We could extend our implementation to parameterize the library:

    get-followers(name, http) ->
      $http.GET http://twitter.com/$name/followers

and then our test at least doesn't need to mutate global state to test the function; it can just pass in a stub.

    test get-followers ->
      http = stub object with GET method
      expect a call to http.GET with arguments http://twitter.com/radix/followers
        returning a dummy value
      assert get-followers(http, 'radix') returns the dummy value

This is a little bit better, but it's still concerned about state and time, which is an unnecessary complection with our main goal of describing an HTTP request. We can solve this problem! Let's go back to our original implementation, but assume that instead of *performing* the IO, HTTP.GET *returns* an object describing the request. Purely functional; no state manipulation or IO or any other effects going on here.

    get-followers(name) ->
      HTTP.GET http://twitter.com/$name/followers

Given that, our test can be extremely simple, and only concerned with _values_.

    test get-followers ->
      request = get-followers('radix')
      assert request.method is GET
        and request.url is http://twitter.com/radix/followers

That's really concise and to the point! Writing our implementation this way has other benefits, too: since our function no longer concerns itself with performing IO, we can interpret its result however we want. Different policies can perform the IO in different ways -- concurrently in threads, or using asynchronous IO instead of blocking calls, or -- in the case of our tests, not do IO at all.

This smells like a pretty powerful pattern. Let's explore it some more.

Of course we need to actually _perform_ this IO. The caller would do it, with a general-purpose function:

    main() ->
      request = get-followers('radix')
      result = perform-io(request)
      print json.decode(result)

perform-io will be covered more later.

Right now our get-followers function is not as convenient as it should be. Presumably, the Twitter API returns the followers as a string, with some JSON-encoded data. That's not a very good result for this operation to have; we don't want our users receiving a string, we would like for them to receive, say, a list of strings of usernames. Usually, these kinds of abstractions rely on *performing* the IO, receiving the result, and then further processing it. However, we want to keep the IO separate, so we need a way to specify how to process the result of the IO without actually doing the IO. We can follow the lead of asynchronous systems and use callbacks to improve this abstraction, while leaving it purely functional.

    get-followers(name) ->
      request = HTTP.GET http://twitter.com/$name/followers
      attach callback to request with result ->
        [x['name'] for x in json.decode(result)]

Now, get-followers is returning a composition of the HTTP request and the function to call when the result is available. perform-io will be implemented to invoke callbacks after performing the request they're bound to. Now our main function doesn't need to concern itself with the decoding:

    main() ->
      request = get-followers('radix')
      result = perform-io(request)
      print result

This pattern should allow us to create further pure functions that use get-followers, and combine chains of IO into one big purely functional structure:

    get-first-followers-followers(name):
      "returns the followers of the first follower of the named user"
      request = get-followers(name)
      attach callback to request with result ->
        get-followers(result[0])

Here we've created a callback that returns another IO request. Our perform-io function can be implemented to check if the result of a callback is another "request" object and perform it immediately. That way our main function still only needs to call it once:

    main() ->
      request = get-first-followers-followers(name)
      # here, perform-io will check the return value of any callbacks and
      # immediately recursively perform their IO.
      result = perform-io(request)
      print result

Let's figure out how we could test our new get-first-followers-followers function. Again, we want to test it without actually performing an HTTP request. Ideally, we should not even be concerned that HTTP is involved -- the implementation is taking advantage of the get-followers abstraction for that, so why should our tests need to care about it if our implementation doesn't? What we want to ensure is that:

- the name we pass is used to look up twitter followers
- the first name returned from that lookup is used to look up more twitter followers
- those twitter followers are the ultimate result

Typically, when we want to avoid concerning ourselves with the implementation details of the abstractions that the code under test uses, we mock it out.

    test get-first-followers-followers() ->
      mock out get-followers
      expect a call to get-followers('radix'), returning an IO that immediately resolves to ['jane', 'bob']
      expect a call to get-followers('jane'), returning an IO that immediately resolves to ['bill', 'sue']
      request = get-first-followers-followers('radix')
      result = resolve(request)
      assert result is ['bill', 'sue']

Can we avoid mocking? Not to mention avoiding the other problems with mocking that crop up, especially when testing more complex methods.
