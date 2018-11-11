import json
from requests import Session


class GraphQLSession:
    """
    A HTTP request session for GraphQL queries.

    A `Session` instance exposes all methods abd properties of a `Session` instance from
    the `requests` library. In addition, it offers a method `graphql_query` for GraphQL
    queries.

    The URL endpoint used for HTTP requests uis set in the constructor and should not be
    changed afterwards. If you call any of the methods corresponding to an HTTP verb
    (i.e. `get`, `post` etc.) you must not pass an URL.

    For example, a simple GET request would look as follows.

    ..code-block:: python

        from graphql_requests import GraphQLSession

        session = GraphQLSession('http://localhost:5000/graphql')
        session.get()

    There usually should be no need to use these HTTP verb methods, though.

    Parameters
    ----------
    uri : str
        URL for the GraphQL queries.

    """

    _HTTP_VERBS = ["get", "post", "put", "patch", "delete", "options", "head"]

    def __init__(self, uri):
        self._uri = uri
        self._session = Session()

    def __getattr__(self, item):
        """
        Use the attribute of the `requests` session with the same attribute name. In
        case of an HTTP vern, make sure that the method is called with the correct URL.

        Parameters
        ----------
        item : str
            Attribute name.

        Returns
        -------
        object
            The attribute.

        """
        # sanity check: does the attribute exist?
        if not hasattr(self._session, item):
            raise AttributeError(
                "The Session class has no attribute '{attr}'".format(attr=item)
            )

        # use this session's URL for the HTTP request
        if item in GraphQLSession._HTTP_VERBS:

            def f(*args, **kwargs):
                return getattr(self._session, item)(self._uri, *args, **kwargs)

            return f

        # just delegate to the requests session
        return getattr(self._session, item)

    def query(self, query_string, variables=None, file_map=None, files=None):
        """
        Send a GraphQL request.

        If the GraphQL query uses no variables, only a query string needs to be given.
        For queries with variables you also need to provide the variables and, in case
        you are uploading files, the file map and files as well.

        Usage
        -----

        ..code-block:: python

            data = open('data_file.csv'
            query_string = '''mutation uploadWeatherData($town: String, $data: Upload) {
                uploadWeatherData(town: $town, data: $data) {
                    ok
                }
            }'''
            variables = {
                town: 'Sutherland',
                data: None
            }
            file_map: {
                '0': ['variables.data']
            }
            files = {
                '0': ('weather.csv', data, 'text/csv')
            }
            session.query(
                query_string=query_string,
                variables=variables,
                file_map=file_map,
                files=files
            )

        Parameters
        ----------
        query_string : str
            GraphQL query string.
        variables : dict
            Dictionary of `'name': 'value'`. For files the value should be `None`.
        file_map : dict
            Dictionary of `'name': operations-path`. An operations path generally is of
            the form `'variables.f` if `$f` is a scalar file variable or `variables.f.n`
            (with an array index `n`) if `$f` is an array of files.
        files : dict
            Dictionary of `'name': file-tuple`. `file-tuple` is a 3-tuple (`(file-name,
            fileobj, content-type)`). The names must be the same as those in the
            `file_map` dictionary.

        Returns
        -------
        Response
            The server response.

        """
        # sanity check: have all required arguments been supplied?
        if file_map:
            if not variables or not files:
                raise ValueError(
                    "The file_map argument requires the variables and files arguments"
                )
        if files:
            if not variables or not file_map:
                raise ValueError(
                    "The files argument requires the variables and file_map arguments"
                )

        # sanity check: are the files and the file map consistent?
        if file_map and files:
            file_map_keys = set(file_map.keys())
            file_keys = set(files.keys())
            if file_map_keys != file_keys:
                raise ValueError(
                    "The file map and the files dictionary must have the same keys"
                )

        # sanity check: are the file values complete?
        if files:
            for value in files.values():
                if len(value) != 3:
                    raise ValueError('The values of the files directory must be '
                                     '3-tuples with the filename, the file object and '
                                     'the content type')

        # query without file upload
        if not files or len(files) == 0:
            payload = {'query': query_string}
            if variables:
                payload['variables'] = variables

            return self._session.post(self._uri, json=payload)

        # query with file upload
        operations = {
            'query': query_string,
            'variables': variables
        }
        data = {
            'operations': json.dumps(operations),
            'map': json.dumps(file_map)
        }
        file_data = {key: files[key] for key in files.keys()}

        return self._session.post(self._uri, data=data, files=file_data)

    @property
    def auth(self):
        return self._session.auth

    @auth.setter
    def auth(self, auth):
        self._session.auth = auth

