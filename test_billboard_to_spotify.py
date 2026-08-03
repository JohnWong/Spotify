import unittest
from contextlib import redirect_stdout
from io import StringIO
from unittest.mock import Mock, patch

import billboard_to_spotify


class FixedPlaylistTest(unittest.TestCase):
    def test_update_uses_fixed_playlist_without_lookup_or_creation(self):
        calls = []

        class FakeBillboardToSpotify:
            def __init__(self, **kwargs):
                pass

            def request_user_authorization(self):
                calls.append(("authorize",))

            def song_uris(self):
                return ["spotify:track:test"]

            def update_playlist_description(self, endpoint):
                calls.append(("describe", endpoint))

            def clear_playlist(self, endpoint, snapshot_id):
                calls.append(("clear", endpoint, snapshot_id))

            def adding_playlist(self, endpoint, songs):
                calls.append(("add", endpoint, songs))

        expected_endpoint = (
            "https://api.spotify.com/v1/playlists/"
            "6M13zytAhM5hCLn4YZ5znR/tracks"
        )

        with patch.object(
            billboard_to_spotify,
            "BillboardToSpotify",
            FakeBillboardToSpotify,
        ):
            billboard_to_spotify.updateBillboard(
                "user", "secret", "client", "redirect"
            )

        self.assertEqual(
            calls,
            [
                ("authorize",),
                ("describe", expected_endpoint),
                ("clear", expected_endpoint, None),
                ("add", expected_endpoint, ["spotify:track:test"]),
            ],
        )

    def test_refresh_does_not_print_access_token(self):
        spotify = billboard_to_spotify.BillboardToSpotify(
            "user", "client", "secret", "redirect"
        )
        response = Mock(status_code=200)
        response.json.return_value = {
            "access_token": "sensitive-access-token",
            "refresh_token": "new-refresh-token",
        }
        output = StringIO()

        with (
            patch.object(billboard_to_spotify, "read_refresh_token", return_value="old"),
            patch.object(billboard_to_spotify, "write_refresh_token"),
            patch.object(billboard_to_spotify.requests, "post", return_value=response),
            redirect_stdout(output),
        ):
            spotify.request_user_authorization()

        self.assertNotIn("sensitive-access-token", output.getvalue())


if __name__ == "__main__":
    unittest.main()
