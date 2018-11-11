# GraphQL Requests

While standard GraphQL does not include a type for uploading files, the proposed [Multipart Request Spec](https://github.com/jaydenseric/graphql-multipart-request-spec) adds an Upload type. Various implementations exist for this spec. For example, the [graphene-file-upload](https://github.com/lmcgartland/graphene-file-upload) package implements the spec for Flask and Django.

The GraphQL Requests package provides a thin wrapper around a [Requests](http://docs.python-requests.org/en/master/) session for facilitating GraphQL queries with and without a file upload.

## Installing

graphql_requests can be installed with pip:

```bash
pip install graphql_requests
```

## Usage

The following code can be used with the test server from [https://github.com/saltastro/graphql_requests_test_server.git](https://github.com/saltastro/graphql_requests_test_server.git).

You instantiate a graphql_requests session by calling its constructor with the URI to use for the GraphQL queries.

```python
from graphql_requests import GraphQLSession

session = GraphQLSession('http://localhost:4000/')
```

The session exposes all the functionality of a [Requests session](http://docs.python-requests.org/en/master/user/advanced/#session-objects). However, contrary to their counterparts in a Requests session, methods corresponding to an HTTP verb (i.e. get, post etc.) do not accept a URI as their first argument, as they use the one passed when creating the session instance. So the following would be valid.

```python
query_string = query = '''query {
    user(id: "0cc32455-b51e-4930-8b49-398d87576af6") {
        name
    }
}'''
session.post(json={'query': query_string})
```

Usually there should be no need for using these methods, though, as graphql_requests has its own `query` method specifically for making GraphQL requests. The previous example can be rewritten to use this method.

```python
session.query(query_string)
```

The query method returns a Requests [Response](http://docs.python-requests.org/en/master/api/#requests.Response) instance. Here is how you could get the JSON object returned by the server.

```python
res = session.query(query_string)
print(res.json())
``` 

If your query contains variables, you need to pass these as a dictionary of variable names and values.

```python
query_string = '''query user($id: ID!) {
    user(id: $id) {
        name
    }
}'''
variables = {
    'id': '0cc32455-b51e-4930-8b49-398d87576af6'
}
session.query(query_string=query_string, variables=variables)
```

In case you want to upload files, a file map and a files dictionary are required as well. The map links unique identifiers to variables of type Upload. The files dictionary links the same identifiers to 3-tuples with the following items:

* The filename.
* The file content. You can pass this in any form that is handled by the `files` attribute of the `post` method in the Requests library.]
* The content type. This should be a valid MIME type such as `'text.plain'` or `'application.zip'`.

For example, the creation of a user with a CV might look as follows.

```python
filepath = '/path/to/cv.pdf'
with open(filepath, 'rb') as f:
    query_string = '''mutation createUser($name: String!, $cv: Upload!) {
        createUser(name: $name, cv: $cv) {
            id
        }
    }'''
    variables = {
       'name': 'John Doe',
       'cv': None
    }
    file_map = {
        '0': ['variables.cv']
    }
    files = {
        '0': ('cv.pdf', f, 'application/pdf')
    }
    session.query(
        query_string=query_string,
        variables=variables,
        file_map=file_map,
        files=files
    )
```

## Authentication

You can add support for authentication in the same way you would [add it to a Requests session](http://docs.python-requests.org/en/master/user/advanced/#custom-authentication).

As an example, let us add token based authentication to our GraphQL queries. For this we need a class implementing the authentication logic.

```python
from requests.auth import AuthBase

class TokenAuth(AuthBase):
    def __init__(self, token):
        self._token = token
    
    def __call__(self, r):
        r.headers['Authorization'] = 'Token ' + self._token
        return r
```

An instance of this class can then be assigned to the session's `auth` property.

```python
session.auth =  TokenAuth('4c7b223d-ca67-4fd7-809f-f0fae71fb6d6')
```

Any further queries will then have an Authorization header with the token.
