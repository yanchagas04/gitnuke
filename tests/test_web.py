import json
import subprocess
import unittest
from unittest.mock import patch

from gitnuke.web import _launch_auth_terminal, _repositories, create_app


class WebAppTests(unittest.TestCase):
    def setUp(self):
        self.app = create_app()
        self.app.config["TESTING"] = True
        self.client = self.app.test_client()
        self.client.get("/")
        with self.client.session_transaction() as browser_session:
            self.csrf_token = browser_session["csrf_token"]

    def post_json(self, url, payload):
        return self.client.post(
            url,
            json=payload,
            headers={"X-CSRF-Token": self.csrf_token},
        )

    def test_interface_and_assets_are_served(self):
        page = self.client.get("/")
        javascript = self.client.get("/static/app.js")
        stylesheet = self.client.get("/static/style.css")

        self.assertEqual(page.status_code, 200)
        page_html = page.get_data(as_text=True)
        self.assertIn("Excluir repositórios do GitHub", page_html)
        self.assertIn('id="theme-toggle"', page_html)
        self.assertEqual(javascript.status_code, 200)
        self.assertIn("localStorage.setItem(\"theme\"", javascript.get_data(as_text=True))
        self.assertEqual(stylesheet.status_code, 200)
        self.assertIn(':root[data-theme="dark"]', stylesheet.get_data(as_text=True))
        javascript.close()
        stylesheet.close()

    def test_auth_status_reports_current_account(self):
        with (
            patch("gitnuke.web._authenticated_username", return_value="octocat"),
            patch("gitnuke.web._repositories", return_value=[]),
        ):
            response = self.client.get("/api/auth/status")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json, {"authenticated": True, "username": "octocat"})

    def test_auth_commands_are_started_in_terminal(self):
        with (
            patch("gitnuke.web.shutil.which", return_value="gh"),
            patch("gitnuke.web.subprocess.Popen") as popen,
        ):
            _launch_auth_terminal()

        command = popen.call_args.args[0][-1]
        self.assertIn("gh auth login --web", command)
        self.assertIn("gh auth refresh -h github.com -s delete_repo", command)

    def test_permission_refresh_opens_terminal(self):
        with (
            patch("gitnuke.web.shutil.which", return_value="gh"),
            patch("gitnuke.web.subprocess.Popen"),
        ):
            response = self.post_json("/api/auth/refresh", {})

        self.assertEqual(response.status_code, 200)
        self.assertIn("delete_repo", response.json["message"])

    def test_repository_response_includes_only_personal_repositories(self):
        pages = [
            [
                {
                    "name": "zebra",
                    "full_name": "octocat/zebra",
                    "description": None,
                    "private": False,
                    "owner": {"login": "octocat"},
                },
                {
                    "name": "team",
                    "full_name": "octo-org/team",
                    "description": "Organization repository",
                    "private": True,
                    "owner": {"login": "octo-org"},
                },
            ],
            [
                {
                    "name": "alpha",
                    "full_name": "octocat/alpha",
                    "description": "Personal repository",
                    "private": True,
                    "owner": {"login": "octocat"},
                }
            ],
        ]
        completed = subprocess.CompletedProcess([], 0, json.dumps(pages), "")
        with patch("gitnuke.web._run_gh", return_value=completed):
            repositories = _repositories("octocat")

        self.assertEqual([repo["name"] for repo in repositories], ["alpha", "zebra"])
        self.assertTrue(repositories[0]["private"])
        self.assertEqual(repositories[1]["description"], "")

    def test_repository_list_returns_personal_repository_details(self):
        repositories = [
            {
                "name": "project",
                "full_name": "octocat/project",
                "description": "A demo",
                "private": True,
            }
        ]
        with (
            patch("gitnuke.web._authenticated_username", return_value="octocat"),
            patch("gitnuke.web._repositories", return_value=repositories),
        ):
            response = self.client.get("/api/repositories")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json["username"], "octocat")
        self.assertEqual(response.json["repositories"], repositories)

    def test_delete_requires_csrf_token(self):
        response = self.client.post(
            "/api/repositories/delete",
            json={"repositories": ["octocat/project"]},
        )

        self.assertEqual(response.status_code, 403)

    def test_delete_rejects_repositories_not_owned_by_user(self):
        repositories = [
            {
                "name": "project",
                "full_name": "octocat/project",
                "description": "",
                "private": False,
            }
        ]
        with (
            patch("gitnuke.web._authenticated_username", return_value="octocat"),
            patch("gitnuke.web._repositories", return_value=repositories),
            patch("gitnuke.web._run_gh") as run_gh,
        ):
            response = self.post_json(
                "/api/repositories/delete",
                {"repositories": ["other/project"]},
            )

        self.assertEqual(response.status_code, 400)
        run_gh.assert_not_called()

    def test_delete_only_runs_for_validated_selection(self):
        repositories = [
            {
                "name": "project",
                "full_name": "octocat/project",
                "description": "",
                "private": False,
            }
        ]
        with (
            patch("gitnuke.web._authenticated_username", return_value="octocat"),
            patch("gitnuke.web._repositories", return_value=repositories),
            patch(
                "gitnuke.web._run_gh",
                return_value=subprocess.CompletedProcess([], 0, "", ""),
            ) as run_gh,
        ):
            response = self.post_json(
                "/api/repositories/delete",
                {"repositories": ["octocat/project"]},
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json, {"deleted": ["octocat/project"], "failures": []})
        run_gh.assert_called_once_with(
            "api", "--method", "DELETE", "repos/octocat/project"
        )


if __name__ == "__main__":
    unittest.main()
