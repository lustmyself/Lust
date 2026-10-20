import unittest
from unittest.mock import MagicMock, patch

import requests

from launcher.update import github_client
from launcher.update.github_client import GitHubClient


def _redirect(location, code=302):
    response = MagicMock(status_code=code)
    response.headers = {"Location": location}
    return response


class GitHubFallbackTests(unittest.TestCase):
    def test_api_limit_falls_back_to_github_com(self):
        limited = MagicMock()
        limited.raise_for_status.side_effect = requests.HTTPError("403 rate limit exceeded")
        redirect = _redirect("https://github.com/lustmyself/Lust/releases/tag/v1.4.9.30")
        with patch.object(github_client.requests, "get", side_effect=[limited, redirect]):
            release = GitHubClient().get_latest_release()
        client = GitHubClient()
        self.assertEqual(client.get_release_version(release), "v1.4.9.30")
        self.assertEqual(client.get_zip_asset(release)["browser_download_url"],
                         "https://github.com/lustmyself/Lust/releases/download/v1.4.9.30/update_package_1.4.9.30.zip")

    def test_no_release_when_github_com_gives_no_tag(self):
        limited = MagicMock()
        limited.raise_for_status.side_effect = requests.HTTPError("403")
        with patch.object(github_client.requests, "get",
                          side_effect=[limited, _redirect("https://github.com/login", 302)]):
            self.assertIsNone(GitHubClient().get_latest_release())
        with patch.object(github_client.requests, "get",
                          side_effect=[limited, _redirect("", 200)]):
            self.assertIsNone(GitHubClient().get_latest_release())


if __name__ == "__main__":
    unittest.main()
