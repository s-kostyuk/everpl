# Include standard modules
import unittest
from unittest import mock
import asyncio
import json
import xml

# Include 3rd-party modules
import aiohttp

# Include DPL modules
from dpl.api import ApiGateway
from dpl.api import exceptions
from dpl.api import api_errors

from dpl.api.rest_api import RestApi


class TestRestApiProvider(unittest.TestCase):
    host = "localhost"
    port = 19101
    base_url = "http://{0}:{1}/".format(host, port)

    def setUp(self):
        # create a new event loop
        self.loop = asyncio.new_event_loop()  # type: asyncio.AbstractEventLoop

        # create a mock of ApiGateway
        self.api_gateway_mock = mock.Mock(spec_set=ApiGateway)

        # create an instance of RestApi
        self.rest_api_provider = RestApi(
            self.api_gateway_mock,
            self.loop
        )

        # TODO: Pick a random free port. Check if port is free
        # create rest server on localhost and specified port
        self.loop.run_until_complete(
            self.rest_api_provider.create_server(
                host=self.host, port=self.port
            )
        )

    def tearDown(self):
        # shutdown rest server
        self.loop.run_until_complete(
            self.rest_api_provider.shutdown_server()
        )

        # close old event loop
        self.loop.close()

        # delete links to used objects
        del self.rest_api_provider
        del self.api_gateway_mock

        del self.loop

    def test_root(self):
        test_response_body = {
            "things": "/things/",
            "auth": "/auth",
            "messages": "/messages/",
            "placements": "/placements/"
        }

        async def body():
            async with aiohttp.ClientSession(loop=self.loop) as session:
                async with session.get(self.base_url) as resp:
                    self.assertEqual(resp.status, 200)
                    self.assertEqual(await resp.json(), test_response_body)

        self.loop.run_until_complete(body())

    def test_auth_success(self):
        test_url = self.base_url + 'auth'

        test_token = "asdfghjkl"
        test_request_body = json.dumps({
            "username": "nobody cares",
            "password": "nobody cares"
        })
        test_request_headers = {'content-type': 'application/json'}

        test_response_body = {
            "token": test_token,
            "message": "authorized"
        }

        self.api_gateway_mock.auth = mock.Mock()
        self.api_gateway_mock.auth.return_value = test_token

        async def body():
            async with aiohttp.ClientSession(loop=self.loop) as session:
                async with session.post(test_url, data=test_request_body, headers=test_request_headers) as resp:
                    self.assertEqual(resp.status, 200)
                    self.assertEqual(await resp.json(), test_response_body)

        self.loop.run_until_complete(body())

    def test_auth_options(self):
        test_url = self.base_url + 'auth'
        test_resp_headers = {'Allow': 'POST, HEAD, OPTIONS'}

        async def body():
            async with aiohttp.ClientSession(loop=self.loop) as session:
                async with session.options(test_url) as resp:
                    self.assertEqual(resp.status, 204)
                    self.assertIn(
                        'Allow', resp.headers
                    )
                    self.assertTrue(
                        test_resp_headers['Allow'] == resp.headers['Allow']
                    )

        self.loop.run_until_complete(body())

    def test_auth_content_header_missing(self):
        test_url = self.base_url + 'auth'

        test_request_body = {
            "username": "nobody cares",
            "password": "nobody cares"
        }
        test_request_headers = {}

        test_response_body = api_errors.ERROR_TEMPLATES[1000].to_dict()
        test_response_status = 400

        async def body():
            async with aiohttp.ClientSession(loop=self.loop) as session:
                async with session.post(test_url, data=test_request_body, headers=test_request_headers) as resp:
                    self.assertEqual(resp.status, test_response_status)
                    self.assertEqual(await resp.json(), test_response_body)

        self.loop.run_until_complete(body())

    def test_auth_body_decode_failed(self):
        test_url = self.base_url + 'auth'

        test_request_body = json.dumps({
            "username": "nobody cares",
            "password": "nobody cares"
        })
        test_request_body = "{" + test_request_body  # append an extra bracket and make json invalid
        test_request_headers = {'content-type': 'application/json'}

        test_response_body = api_errors.ERROR_TEMPLATES[1001].to_dict()
        test_response_status = 400

        async def body():
            async with aiohttp.ClientSession(loop=self.loop) as session:
                async with session.post(test_url, data=test_request_body, headers=test_request_headers) as resp:
                    self.assertEqual(resp.status, test_response_status)
                    self.assertEqual(await resp.json(), test_response_body)

        self.loop.run_until_complete(body())

    def test_auth_username_missing(self):
        test_url = self.base_url + 'auth'

        test_request_body = {
            "password": "nobody cares"
        }

        test_response_body = api_errors.ERROR_TEMPLATES[2000].to_dict()
        test_response_status = 400

        async def body():
            async with aiohttp.ClientSession(loop=self.loop) as session:
                async with session.post(test_url, json=test_request_body) as resp:
                    self.assertEqual(resp.status, test_response_status)
                    self.assertEqual(await resp.json(), test_response_body)

        self.loop.run_until_complete(body())

    def test_auth_password_missing(self):
        test_url = self.base_url + 'auth'

        test_request_body = {
            "username": "nobody cares"
        }

        test_response_body = api_errors.ERROR_TEMPLATES[2001].to_dict()
        test_response_status = 400

        async def body():
            async with aiohttp.ClientSession(loop=self.loop) as session:
                async with session.post(test_url, json=test_request_body) as resp:
                    self.assertEqual(resp.status, test_response_status)
                    self.assertEqual(await resp.json(), test_response_body)

        self.loop.run_until_complete(body())

    def test_auth_bad_username_password_combination(self):
        test_url = self.base_url + 'auth'

        test_request_body = {
            "username": "nobody cares",
            "password": "nobody cares"
        }

        def auth_side_effect(*args, **kwargs):
            # FIXME: specify more concrete exception
            raise ValueError()

        test_response_body = api_errors.ERROR_TEMPLATES[2002].to_dict()
        test_response_status = 401

        self.api_gateway_mock.auth = mock.Mock()
        self.api_gateway_mock.auth.side_effect = auth_side_effect

        async def body():
            async with aiohttp.ClientSession(loop=self.loop) as session:
                async with session.post(test_url, json=test_request_body) as resp:
                    self.assertEqual(resp.status, test_response_status)
                    self.assertEqual(await resp.json(), test_response_body)

        self.loop.run_until_complete(body())

    def test_auth_server_error(self):
        test_url = self.base_url + 'auth'

        test_request_body = {
            "username": "nobody cares",
            "password": "nobody cares"
        }

        def auth_side_effect(*args, **kwargs):
            raise Exception()

        test_response_body = api_errors.ERROR_TEMPLATES[1003]
        test_response_status = 500

        self.api_gateway_mock.auth = mock.Mock()
        self.api_gateway_mock.auth.side_effect = auth_side_effect

        async def body():
            async with aiohttp.ClientSession(loop=self.loop) as session:
                async with session.post(test_url, json=test_request_body) as resp:
                    self.assertEqual(resp.status, test_response_status)
                    response_body = await resp.json()

                    self.assertEqual(
                        response_body['error_id'], test_response_body.error_id
                    )

                    self.assertIn('devel_message', response_body)
                    self.assertIn('user_message', response_body)
                    self.assertIn('docs_url', response_body)

        self.loop.run_until_complete(body())

    def test_auth_server_method_not_allowed(self):
        test_url = self.base_url + 'auth'

        test_unsupported_method = 'DELETE'

        test_response_body = api_errors.ERROR_TEMPLATES[1004].to_dict()
        test_response_body["devel_message"] = \
            test_response_body["devel_message"].format(method_name=test_unsupported_method)

        test_response_status = 405

        async def body():
            async with aiohttp.ClientSession(loop=self.loop) as session:
                async with session.request(method=test_unsupported_method, url=test_url) as resp:
                    self.assertEqual(resp.status, test_response_status)
                    response_body = await resp.json()

                    self.assertEqual(
                        response_body, test_response_body
                    )

        self.loop.run_until_complete(body())

    def test_resource_not_found(self):
        test_url = self.base_url + 'asdfghjkllkjhgfdsdfghj'

        test_response_body = api_errors.ERROR_TEMPLATES[1005].to_dict()

        test_response_status = 404

        async def body():
            async with aiohttp.ClientSession(loop=self.loop) as session:
                async with session.get(url=test_url) as resp:
                    self.assertEqual(resp.status, test_response_status)
                    response_body = await resp.json()

                    self.assertEqual(
                        response_body, test_response_body
                    )

        self.loop.run_until_complete(body())

    def test_get_placement(self):
        test_placement_id = 'R1'
        test_url = self.base_url + 'placements/' + test_placement_id
        test_token = "nobody_cares"

        test_headers = {'Authorization': test_token}

        test_placement_mock = {"key1": "nobody cares"}

        self.api_gateway_mock.get_placement = mock.Mock()
        self.api_gateway_mock.get_placement.return_value = test_placement_mock

        test_response_status = 200

        async def body():
            async with aiohttp.ClientSession(loop=self.loop) as session:
                async with session.get(url=test_url, headers=test_headers) as resp:
                    self.assertEqual(resp.status, test_response_status)
                    response_body = await resp.json()

                    self.assertEqual(
                        response_body, test_placement_mock
                    )

        self.loop.run_until_complete(body())

    def test_get_placement_not_found(self):
        test_placement_id = 'R1'
        test_url = self.base_url + 'placements/' + test_placement_id
        test_token = "nobody_cares"

        test_headers = {'Authorization': test_token}

        def get_placement_side_effect(*args, **kwargs):
            raise exceptions.PlacementNotFoundError

        test_response_body = api_errors.ERROR_TEMPLATES[1005].to_dict()

        self.api_gateway_mock.get_placement = mock.Mock()
        self.api_gateway_mock.get_placement.side_effect = get_placement_side_effect

        test_response_status = 404

        async def body():
            async with aiohttp.ClientSession(loop=self.loop) as session:
                async with session.get(url=test_url, headers=test_headers) as resp:
                    self.assertEqual(resp.status, test_response_status)
                    response_body = await resp.json()

                    self.assertEqual(
                        response_body, test_response_body
                    )

        self.loop.run_until_complete(body())

    def test_get_placement_missing_auth_reader(self):
        test_placement_id = 'R1'
        test_url = self.base_url + 'placements/' + test_placement_id

        test_response_status = 401

        test_response_body = api_errors.ERROR_TEMPLATES[2100].to_dict()

        async def body():
            async with aiohttp.ClientSession(loop=self.loop) as session:
                async with session.get(url=test_url) as resp:
                    self.assertEqual(resp.status, test_response_status)
                    response_body = await resp.json()

                    self.assertEqual(
                        response_body, test_response_body
                    )

        self.loop.run_until_complete(body())

    def test_get_placement_invalid_token(self):
        test_placement_id = 'R1'
        test_url = self.base_url + 'placements/' + test_placement_id
        test_token = "nobody_cares"

        test_headers = {'Authorization': test_token}

        def get_placement_side_effect(*args, **kwargs):
            raise exceptions.InvalidTokenError

        test_response_body = api_errors.ERROR_TEMPLATES[2101].to_dict()

        self.api_gateway_mock.get_placement = mock.Mock()
        self.api_gateway_mock.get_placement.side_effect = get_placement_side_effect

        test_response_status = 401

        async def body():
            async with aiohttp.ClientSession(loop=self.loop) as session:
                async with session.get(url=test_url, headers=test_headers) as resp:
                    self.assertEqual(resp.status, test_response_status)
                    response_body = await resp.json()

                    self.assertEqual(
                        response_body, test_response_body
                    )

        self.loop.run_until_complete(body())

    def test_get_placement_token_insufficient_permissions(self):
        test_placement_id = 'R1'
        test_url = self.base_url + 'placements/' + test_placement_id
        test_token = "nobody_cares"

        test_headers = {'Authorization': test_token}

        def get_placement_side_effect(*args, **kwargs):
            raise exceptions.PermissionDeniedForTokenError

        test_response_body = api_errors.ERROR_TEMPLATES[2110].to_dict()

        self.api_gateway_mock.get_placement = mock.Mock()
        self.api_gateway_mock.get_placement.side_effect = get_placement_side_effect

        test_response_status = 403

        async def body():
            async with aiohttp.ClientSession(loop=self.loop) as session:
                async with session.get(url=test_url, headers=test_headers) as resp:
                    self.assertEqual(resp.status, test_response_status)
                    response_body = await resp.json()

                    self.assertEqual(
                        response_body['error_id'], test_response_body['error_id']
                    )

                    self.assertIn('devel_message', response_body)
                    self.assertIn('user_message', response_body)
                    self.assertIn('docs_url', response_body)

        self.loop.run_until_complete(body())

    def test_get_placements(self):
        test_url = self.base_url + 'placements/'
        test_token = "nobody_cares"

        test_headers = {'Authorization': test_token}

        test_placements_mock = [{"key1": "nobody cares"}, {"key1": "nobody cares 2"}]

        self.api_gateway_mock.get_placements = mock.Mock()
        self.api_gateway_mock.get_placements.return_value = test_placements_mock

        test_response_status = 200

        async def body():
            async with aiohttp.ClientSession(loop=self.loop) as session:
                async with session.get(url=test_url, headers=test_headers) as resp:
                    self.assertEqual(resp.status, test_response_status)
                    response_body = await resp.json()

                    self.assertEqual(
                        response_body, {"placements": test_placements_mock}
                    )

        self.loop.run_until_complete(body())

    def test_get_placements_empty(self):
        test_url = self.base_url + 'placements/'
        test_token = "nobody_cares"

        test_headers = {'Authorization': test_token}

        test_placements_mock = []

        self.api_gateway_mock.get_placements = mock.Mock()
        self.api_gateway_mock.get_placements.return_value = test_placements_mock

        test_response_status = 200

        async def body():
            async with aiohttp.ClientSession(loop=self.loop) as session:
                async with session.get(url=test_url, headers=test_headers) as resp:
                    self.assertEqual(resp.status, test_response_status)
                    response_body = await resp.json()

                    self.assertEqual(
                        response_body, {"placements": test_placements_mock}
                    )

        self.loop.run_until_complete(body())

    def test_get_placements_missing_auth_reader(self):
        test_url = self.base_url + 'placements/'

        test_response_status = 401

        test_response_body = api_errors.ERROR_TEMPLATES[2100].to_dict()

        async def body():
            async with aiohttp.ClientSession(loop=self.loop) as session:
                async with session.get(url=test_url) as resp:
                    self.assertEqual(resp.status, test_response_status)
                    response_body = await resp.json()

                    self.assertEqual(
                        response_body, test_response_body
                    )

        self.loop.run_until_complete(body())

    def test_get_placements_invalid_token(self):
        test_url = self.base_url + 'placements/'
        test_token = "nobody_cares"

        test_headers = {'Authorization': test_token}

        def get_placements_side_effect(*args, **kwargs):
            raise exceptions.InvalidTokenError

        test_response_body = api_errors.ERROR_TEMPLATES[2101].to_dict()

        self.api_gateway_mock.get_placements = mock.Mock()
        self.api_gateway_mock.get_placements.side_effect = get_placements_side_effect

        test_response_status = 401

        async def body():
            async with aiohttp.ClientSession(loop=self.loop) as session:
                async with session.get(url=test_url, headers=test_headers) as resp:
                    self.assertEqual(resp.status, test_response_status)
                    response_body = await resp.json()

                    self.assertEqual(
                        response_body, test_response_body
                    )

        self.loop.run_until_complete(body())

    def test_get_placements_token_insufficient_permissions(self):
        test_url = self.base_url + 'placements/'
        test_token = "nobody_cares"

        test_headers = {'Authorization': test_token}

        def get_placements_side_effect(*args, **kwargs):
            raise exceptions.PermissionDeniedForTokenError

        test_response_body = api_errors.ERROR_TEMPLATES[2110].to_dict()

        self.api_gateway_mock.get_placements = mock.Mock()
        self.api_gateway_mock.get_placements.side_effect = get_placements_side_effect

        test_response_status = 403

        async def body():
            async with aiohttp.ClientSession(loop=self.loop) as session:
                async with session.get(url=test_url, headers=test_headers) as resp:
                    self.assertEqual(resp.status, test_response_status)
                    response_body = await resp.json()

                    self.assertEqual(
                        response_body['error_id'], test_response_body['error_id']
                    )

                    self.assertIn('devel_message', response_body)
                    self.assertIn('user_message', response_body)
                    self.assertIn('docs_url', response_body)

        self.loop.run_until_complete(body())

    def test_get_thing(self):
        test_thing_id = 'Th1'
        test_url = self.base_url + 'things/' + test_thing_id
        test_token = "nobody_cares"

        test_headers = {'Authorization': test_token}

        test_placement_mock = {"key1": "nobody cares"}

        self.api_gateway_mock.get_thing = mock.Mock()
        self.api_gateway_mock.get_thing.return_value = test_placement_mock

        test_response_status = 200

        async def body():
            async with aiohttp.ClientSession(loop=self.loop) as session:
                async with session.get(url=test_url, headers=test_headers) as resp:
                    self.assertEqual(resp.status, test_response_status)
                    response_body = await resp.json()

                    self.assertEqual(
                        response_body, test_placement_mock
                    )

        self.loop.run_until_complete(body())

    def test_get_thing_not_found(self):
        test_thing_id = 'Th1'
        test_url = self.base_url + 'things/' + test_thing_id
        test_token = "nobody_cares"

        test_headers = {'Authorization': test_token}

        def get_thing_side_effect(*args, **kwargs):
            raise exceptions.ThingNotFoundError

        test_response_body = api_errors.ERROR_TEMPLATES[1005].to_dict()

        self.api_gateway_mock.get_thing = mock.Mock()
        self.api_gateway_mock.get_thing.side_effect = get_thing_side_effect

        test_response_status = 404

        async def body():
            async with aiohttp.ClientSession(loop=self.loop) as session:
                async with session.get(url=test_url, headers=test_headers) as resp:
                    self.assertEqual(resp.status, test_response_status)
                    response_body = await resp.json()

                    self.assertEqual(
                        response_body, test_response_body
                    )

        self.loop.run_until_complete(body())

    def test_get_thing_missing_auth_reader(self):
        test_thing_id = 'Th1'
        test_url = self.base_url + 'things/' + test_thing_id

        test_response_status = 401

        test_response_body = api_errors.ERROR_TEMPLATES[2100].to_dict()

        async def body():
            async with aiohttp.ClientSession(loop=self.loop) as session:
                async with session.get(url=test_url) as resp:
                    self.assertEqual(resp.status, test_response_status)
                    response_body = await resp.json()

                    self.assertEqual(
                        response_body, test_response_body
                    )

        self.loop.run_until_complete(body())

    def test_get_thing_invalid_token(self):
        test_thing_id = 'Th1'
        test_url = self.base_url + 'things/' + test_thing_id
        test_token = "nobody_cares"

        test_headers = {'Authorization': test_token}

        def get_thing_side_effect(*args, **kwargs):
            raise exceptions.InvalidTokenError

        test_response_body = api_errors.ERROR_TEMPLATES[2101].to_dict()

        self.api_gateway_mock.get_thing = mock.Mock()
        self.api_gateway_mock.get_thing.side_effect = get_thing_side_effect

        test_response_status = 401

        async def body():
            async with aiohttp.ClientSession(loop=self.loop) as session:
                async with session.get(url=test_url, headers=test_headers) as resp:
                    self.assertEqual(resp.status, test_response_status)
                    response_body = await resp.json()

                    self.assertEqual(
                        response_body, test_response_body
                    )

        self.loop.run_until_complete(body())

    def test_get_thing_token_insufficient_permissions(self):
        test_thing_id = 'R1'
        test_url = self.base_url + 'things/' + test_thing_id
        test_token = "nobody_cares"

        test_headers = {'Authorization': test_token}

        def get_thing_side_effect(*args, **kwargs):
            raise exceptions.PermissionDeniedForTokenError

        test_response_body = api_errors.ERROR_TEMPLATES[2110].to_dict()

        self.api_gateway_mock.get_thing = mock.Mock()
        self.api_gateway_mock.get_thing.side_effect = get_thing_side_effect

        test_response_status = 403

        async def body():
            async with aiohttp.ClientSession(loop=self.loop) as session:
                async with session.get(url=test_url, headers=test_headers) as resp:
                    self.assertEqual(resp.status, test_response_status)
                    response_body = await resp.json()

                    self.assertEqual(
                        response_body['error_id'], test_response_body['error_id']
                    )

                    self.assertIn('devel_message', response_body)
                    self.assertIn('user_message', response_body)
                    self.assertIn('docs_url', response_body)

        self.loop.run_until_complete(body())

    def test_get_things(self):
        test_url = self.base_url + 'things/'
        test_token = "nobody_cares"

        test_headers = {'Authorization': test_token}

        test_things_mock = [{"key1": "nobody cares"}, {"key1": "nobody cares 2"}]

        self.api_gateway_mock.get_things = mock.Mock()
        self.api_gateway_mock.get_things.return_value = test_things_mock

        test_response_status = 200

        async def body():
            async with aiohttp.ClientSession(loop=self.loop) as session:
                async with session.get(url=test_url, headers=test_headers) as resp:
                    self.assertEqual(resp.status, test_response_status)
                    response_body = await resp.json()

                    self.assertEqual(
                        response_body, {"things": test_things_mock}
                    )

        self.loop.run_until_complete(body())

    def test_get_things_empty(self):
        test_url = self.base_url + 'things/'
        test_token = "nobody_cares"

        test_headers = {'Authorization': test_token}

        test_things_mock = []

        self.api_gateway_mock.get_things = mock.Mock()
        self.api_gateway_mock.get_things.return_value = test_things_mock

        test_response_status = 200

        async def body():
            async with aiohttp.ClientSession(loop=self.loop) as session:
                async with session.get(url=test_url, headers=test_headers) as resp:
                    self.assertEqual(resp.status, test_response_status)
                    response_body = await resp.json()

                    self.assertEqual(
                        response_body, {"things": test_things_mock}
                    )

        self.loop.run_until_complete(body())

    def test_get_things_missing_auth_reader(self):
        test_url = self.base_url + 'things/'

        test_response_status = 401

        test_response_body = api_errors.ERROR_TEMPLATES[2100].to_dict()

        async def body():
            async with aiohttp.ClientSession(loop=self.loop) as session:
                async with session.get(url=test_url) as resp:
                    self.assertEqual(resp.status, test_response_status)
                    response_body = await resp.json()

                    self.assertEqual(
                        response_body, test_response_body
                    )

        self.loop.run_until_complete(body())

    def test_get_things_invalid_token(self):
        test_url = self.base_url + 'things/'
        test_token = "nobody_cares"

        test_headers = {'Authorization': test_token}

        def get_things_side_effect(*args, **kwargs):
            raise exceptions.InvalidTokenError

        test_response_body = api_errors.ERROR_TEMPLATES[2101].to_dict()

        self.api_gateway_mock.get_things = mock.Mock()
        self.api_gateway_mock.get_things.side_effect = get_things_side_effect

        test_response_status = 401

        async def body():
            async with aiohttp.ClientSession(loop=self.loop) as session:
                async with session.get(url=test_url, headers=test_headers) as resp:
                    self.assertEqual(resp.status, test_response_status)
                    response_body = await resp.json()

                    self.assertEqual(
                        response_body, test_response_body
                    )

        self.loop.run_until_complete(body())

    def test_get_things_token_insufficient_permissions(self):
        test_url = self.base_url + 'things/'
        test_token = "nobody_cares"

        test_headers = {'Authorization': test_token}

        def get_things_side_effect(*args, **kwargs):
            raise exceptions.PermissionDeniedForTokenError

        test_response_body = api_errors.ERROR_TEMPLATES[2110].to_dict()

        self.api_gateway_mock.get_things = mock.Mock()
        self.api_gateway_mock.get_things.side_effect = get_things_side_effect

        test_response_status = 403

        async def body():
            async with aiohttp.ClientSession(loop=self.loop) as session:
                async with session.get(url=test_url, headers=test_headers) as resp:
                    self.assertEqual(resp.status, test_response_status)
                    response_body = await resp.json()

                    self.assertEqual(
                        response_body['error_id'], test_response_body['error_id']
                    )

                    self.assertIn('devel_message', response_body)
                    self.assertIn('user_message', response_body)
                    self.assertIn('docs_url', response_body)

        self.loop.run_until_complete(body())

    def test_get_things_filter_by_placement(self):
        test_url = self.base_url + 'things/'
        test_token = "nobody_cares"

        test_headers = {'Authorization': test_token}
        test_params = {'placement': "R1"}

        test_things_mock = [{"placement": "R1"}, {"placement": "R2"}]

        assert test_params['placement'] == test_things_mock[0]['placement']

        self.api_gateway_mock.get_things = mock.Mock()
        self.api_gateway_mock.get_things.return_value = test_things_mock

        test_response_status = 200

        async def body():
            async with aiohttp.ClientSession(loop=self.loop) as session:
                async with session.get(url=test_url, headers=test_headers, params=test_params) as resp:
                    self.assertEqual(resp.status, test_response_status)
                    response_body = await resp.json()

                    self.assertEqual(
                        response_body, {"things": [test_things_mock[0]]}
                    )

        self.loop.run_until_complete(body())

    def test_get_things_filter_by_type(self):
        test_url = self.base_url + 'things/'
        test_token = "nobody_cares"

        test_headers = {'Authorization': test_token}
        test_params = {'type': "t2"}

        test_things_mock = [{"type": "t1"}, {"type": "t2"}]

        assert test_params['type'] == test_things_mock[1]['type']

        self.api_gateway_mock.get_things = mock.Mock()
        self.api_gateway_mock.get_things.return_value = test_things_mock

        test_response_status = 200

        async def body():
            async with aiohttp.ClientSession(loop=self.loop) as session:
                async with session.get(url=test_url, headers=test_headers, params=test_params) as resp:
                    self.assertEqual(resp.status, test_response_status)
                    response_body = await resp.json()

                    self.assertEqual(
                        response_body, {"things": [test_things_mock[1]]}
                    )

        self.loop.run_until_complete(body())

    def test_get_things_filter_by_missing_field(self):
        test_url = self.base_url + 'things/'
        test_token = "nobody_cares"

        test_headers = {'Authorization': test_token}
        test_params = {'something_new': "t2"}

        test_things_mock = [{"type": "t1"}, {"type": "t2"}]

        self.api_gateway_mock.get_things = mock.Mock()
        self.api_gateway_mock.get_things.return_value = test_things_mock

        test_response_status = 200

        async def body():
            async with aiohttp.ClientSession(loop=self.loop) as session:
                async with session.get(url=test_url, headers=test_headers, params=test_params) as resp:
                    self.assertEqual(resp.status, test_response_status)
                    response_body = await resp.json()

                    self.assertEqual(
                        response_body, {"things": test_things_mock}
                    )

        self.loop.run_until_complete(body())

if __name__ == '__main__':
    unittest.main()