"""Tests for `graphql_requests` package."""

import json
import httpretty
import pytest
from requests.auth import AuthBase
from graphql_requests import GraphQLSession

TEST_URI = "http://fvmdolr.ac.za"


class TokenAuth(AuthBase):
    def __init__(self, token):
        self._token = token

    def __call__(self, r):
        r.headers["Authorization"] = "Token " + self._token
        return r


def test_map_requires_variables_and_files():
    """
    If there is a map argument, there must be a variables and files argument as well.
    """

    session = GraphQLSession(TEST_URI)
    with pytest.raises(ValueError):
        session.query(query_string="some query", file_map={"a": "b"})
    with pytest.raises(ValueError):
        session.query(
            query_string="some query", file_map={"a": "b"}, variables={"c": "d"}
        )
    with pytest.raises(ValueError):
        session.query(query_string="some query", file_map={"a": "b"}, files={"c": "d"})


def test_files_requires_variables_and_file_map():
    """
    If there is a files argument, there must be a variables and map argument as well.
    """

    session = GraphQLSession(TEST_URI)
    with pytest.raises(ValueError):
        session.query(query_string="some query", files={"a": "b"})
    with pytest.raises(ValueError):
        session.query(query_string="some query", files={"a": "b"}, variables={"c": "d"})
    with pytest.raises(ValueError):
        session.query(query_string="some query", files={"a": "b"}, file_map={"c": "d"})


def test_file_map_keys_are_file_keys():
    """
    The keys of the file map and the files directory are consistent with each other.
    """

    variables = {"proposal": None, "block": None, "target": None}
    files = {"0": ("a", "b", "text/plain"), "1": ("c", "d", "text/plain")}
    file_map = {"1": ["variables.proposal"], "2": ["variables.block"]}

    session = GraphQLSession(TEST_URI)
    with pytest.raises(ValueError) as excinfo:
        session.query(
            "query { block { id } }",
            variables=variables,
            file_map=file_map,
            files=files,
        )
    assert "same keys" in str(excinfo.value)


def test_incomplete_file_details_are_handled():
    """
    Incomplete details in the files dictionary are handled with sa human-friendly error
    message.
    """

    session = GraphQLSession(TEST_URI)
    variables = {"proposal": None}
    files = {"0": ("a", "b")}
    file_map = {"0": ["variables.proposal"]}
    with pytest.raises(ValueError) as excinfo:
        session.query(
            "query { block { id } }",
            variables=variables,
            file_map=file_map,
            files=files,
        )
    assert "3-tuple" in str(excinfo.value)


@httpretty.activate
def test_simple_query_works():
    """
    A query with just a query string works as expected.
    """

    query_string = """query hello($name: String!) {
    greet(name: $name) {
        response
    }
}"""

    def request_callback(request, uri, response_headers):
        assert request.headers["CONTENT-TYPE"] == "application/json"
        payload = json.loads(request.body)
        assert payload["query"] == query_string
        assert "variables" not in payload

        return [200, response_headers, "fake response"]

    httpretty.register_uri(httpretty.POST, TEST_URI, body=request_callback)

    session = GraphQLSession(TEST_URI)
    session.query(query_string)


@httpretty.activate
def test_query_with_variables_works():
    """
    A query with  a query string and variables works as expected.
    """

    query_string = """query hello($name: String!) {
    greet(name: $name) {
        response
    }
}"""
    variables = {"name": "John Doe"}

    def request_callback(request, uri, response_headers):
        assert request.headers["CONTENT-TYPE"] == "application/json"
        payload = json.loads(request.body)
        assert payload["query"] == query_string
        assert payload["variables"] == variables

        return [200, response_headers, "fake response"]

    httpretty.register_uri(httpretty.POST, TEST_URI, body=request_callback)

    session = GraphQLSession(TEST_URI)
    session.query(query_string, variables=variables)


@httpretty.activate
def test_query_with_files_works():
    """
    A query with with file upload works as expected.
    """

    query_string = """query hello($name: String!, $message: Upload!) {
    greet(name: $name, message: $message) {
        welcome
    }
}"""
    variables = {"name": "John Doe"}
    file_map = {"0": "[variables.message]"}
    files = {"0": ("message.txt", "Welcome to the event!", "text/plain")}

    def request_callback(request, uri, response_headers):
        assert "multipart/form-data; boundary=" in request.headers["CONTENT-TYPE"]
        body = request.body.decode("utf-8")
        assert 'name="operations"' in body
        assert "greet(name: $name, message: $message)" in body
        assert 'name="map"' in body
        assert '"0":' in body
        assert 'name="0"' in body
        assert 'filename="message.txt"' in body
        assert "content-type: text/plain" in body.lower()
        assert "Welcome to the event!" in body

        return [200, response_headers, "fake response"]

    httpretty.register_uri(httpretty.POST, TEST_URI, body=request_callback)

    session = GraphQLSession(TEST_URI)
    session.query(query_string, variables=variables, file_map=file_map, files=files)


@httpretty.activate
def test_call_http_verbs_with_url():
    """
    HTTP Verb methods (get, post, ...) automatically add the session URI.
    """

    http_methods = {
        "get": httpretty.GET,
        "post": httpretty.POST,
        "put": httpretty.PUT,
        "patch": httpretty.PATCH,
        "delete": httpretty.DELETE,
        "options": httpretty.OPTIONS,
        "head": httpretty.HEAD,
    }

    def request_callback(request, uri, response_headers):
        expected_host = TEST_URI.split("://")[1]
        assert request.headers["HOST"] == expected_host
        return [200, response_headers, "some content"]

    session = GraphQLSession(TEST_URI)
    for http_verb in http_methods:
        httpretty.register_uri(http_methods[http_verb], TEST_URI, body=request_callback)
        getattr(session, http_verb)()


@httpretty.activate
def test_authentication_support():
    """
    Authentication can be added in the same way it would be added to a Requests session.
    """

    def request_callback(request, uri, response_headers):
        assert request.headers["AUTHORIZATION"] == "Token sometoken"
        return [200, response_headers, "some content"]

    httpretty.register_uri(httpretty.POST, TEST_URI, body=request_callback)

    session = GraphQLSession(TEST_URI)
    session.auth = TokenAuth("sometoken")

    session.query("query { greet }")
