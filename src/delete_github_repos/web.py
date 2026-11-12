import json
import os
import secrets
import shutil
import subprocess
from typing import Any

from flask import Flask, abort, jsonify, render_template, request, session
from loguru import logger


def _run_gh(*args: str) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(
            ["gh", *args],
            capture_output=True,
            check=False,
            encoding="utf-8",
            text=True,
        )
    except OSError as error:
        raise RuntimeError(f"Nao foi possivel executar o GitHub CLI: {error}") from error


def _command_error(result: subprocess.CompletedProcess[str]) -> str:
    return result.stderr.strip() or result.stdout.strip() or "O comando gh falhou."


def _authenticated_username() -> str | None:
    if shutil.which("gh") is None:
        raise RuntimeError("GitHub CLI (gh) nao encontrado. Instale-o em https://cli.github.com/.")

    status = _run_gh("auth", "status")
    if status.returncode != 0:
        return None

    result = _run_gh("api", "user", "--jq", ".login")
    if result.returncode != 0:
        raise RuntimeError(f"Nao foi possivel identificar a conta autenticada: {_command_error(result)}")

    username = result.stdout.strip()
    if not username:
        raise RuntimeError("O GitHub CLI retornou um nome de usuario vazio.")
    return username


def _repositories(username: str) -> list[dict[str, Any]]:
    result = _run_gh(
        "api",
        "--paginate",
        "--slurp",
        "user/repos?affiliation=owner&per_page=100",
    )
    if result.returncode != 0:
        raise RuntimeError(f"Nao foi possivel listar os repositorios: {_command_error(result)}")

    try:
        pages = json.loads(result.stdout)
    except json.JSONDecodeError as error:
        raise RuntimeError("Resposta inesperada ao listar repositorios.") from error

    if not isinstance(pages, list) or any(not isinstance(page, list) for page in pages):
        raise RuntimeError("Resposta inesperada ao listar repositorios.")

    repositories = []
    for page in pages:
        for repository in page:
            if not isinstance(repository, dict):
                raise RuntimeError("Resposta inesperada ao listar repositorios.")
            owner = repository.get("owner")
            owner_login = owner.get("login") if isinstance(owner, dict) else None
            if not isinstance(owner_login, str) or owner_login.casefold() != username.casefold():
                continue

            name = repository.get("name")
            full_name = repository.get("full_name")
            is_private = repository.get("private")
            if (
                not isinstance(name, str)
                or not isinstance(full_name, str)
                or not isinstance(is_private, bool)
            ):
                raise RuntimeError("Resposta inesperada ao listar repositorios.")
            description = repository.get("description")
            repositories.append(
                {
                    "name": name,
                    "full_name": full_name,
                    "description": description if isinstance(description, str) else "",
                    "private": is_private,
                }
            )

    return sorted(repositories, key=lambda repo: repo["name"].casefold())


def _launch_auth_terminal(*, refresh_only: bool = False) -> None:
    if shutil.which("gh") is None:
        raise RuntimeError("GitHub CLI (gh) nao encontrado. Instale-o em https://cli.github.com/.")

    login_command = "gh auth refresh -h github.com -s delete_repo"
    if not refresh_only:
        login_command = (
            "gh auth login --web --hostname github.com --git-protocol https "
            "&& " + login_command
        )
    try:
        if os.name == "nt":
            subprocess.Popen(
                ["cmd.exe", "/k", login_command],
                creationflags=subprocess.CREATE_NEW_CONSOLE,
            )
        else:
            subprocess.Popen(["sh", "-lc", login_command])
    except OSError as error:
        raise RuntimeError(f"Nao foi possivel abrir o terminal de autenticacao: {error}") from error


def create_app() -> Flask:
    app = Flask(__name__, template_folder="templates", static_folder="static")
    app.secret_key = secrets.token_hex(32)
    app.config.update(
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Strict",
        MAX_CONTENT_LENGTH=1024 * 1024,
    )

    @app.before_request
    def protect_local_app() -> None:
        host = request.host.partition(":")[0].strip("[]").lower()
        if request.remote_addr not in {"127.0.0.1", "::1"} or host not in {
            "127.0.0.1",
            "localhost",
        }:
            abort(403)

        if request.method in {"POST", "PUT", "PATCH", "DELETE"}:
            token = session.get("csrf_token", "")
            supplied_token = request.headers.get("X-CSRF-Token", "")
            if not token or not secrets.compare_digest(token, supplied_token):
                abort(403)

    @app.get("/")
    def index():
        token = session.setdefault("csrf_token", secrets.token_urlsafe(32))
        return render_template("index.html", csrf_token=token)

    @app.get("/api/auth/status")
    def auth_status():
        try:
            username = _authenticated_username()
        except RuntimeError as error:
            logger.error("Erro ao verificar autenticacao: {}", error)
            return jsonify(authenticated=False, error=str(error)), 503
        return jsonify(authenticated=username is not None, username=username)

    @app.post("/api/auth/start")
    def auth_start():
        try:
            _launch_auth_terminal()
        except RuntimeError as error:
            logger.error("Erro ao iniciar autenticacao: {}", error)
            return jsonify(error=str(error)), 503
        return jsonify(
            message=(
                "Conclua gh auth login no terminal aberto. O comando de autorizacao "
                "delete_repo sera solicitado em seguida."
            )
        )

    @app.post("/api/auth/refresh")
    def auth_refresh():
        try:
            _launch_auth_terminal(refresh_only=True)
        except RuntimeError as error:
            logger.error("Erro ao atualizar permissao de exclusao: {}", error)
            return jsonify(error=str(error)), 503
        return jsonify(
            message=(
                "Conclua gh auth refresh no terminal aberto e autorize o escopo "
                "delete_repo."
            )
        )

    @app.get("/api/repositories")
    def list_repositories():
        try:
            username = _authenticated_username()
            if username is None:
                return jsonify(error="Autentique-se com o GitHub CLI para continuar."), 401
            repositories = _repositories(username)
        except RuntimeError as error:
            logger.error("Erro ao listar repositorios: {}", error)
            return jsonify(error=str(error)), 502
        return jsonify(username=username, repositories=repositories)

    @app.post("/api/repositories/delete")
    def delete_repositories():
        try:
            username = _authenticated_username()
            if username is None:
                return jsonify(error="Autentique-se com o GitHub CLI para continuar."), 401
            payload = request.get_json(silent=True)
            selected = payload.get("repositories") if isinstance(payload, dict) else None
            if (
                not isinstance(selected, list)
                or not selected
                or any(not isinstance(name, str) for name in selected)
            ):
                return jsonify(error="Selecione ao menos um repositorio valido."), 400
            if len({name.casefold() for name in selected}) != len(selected):
                return jsonify(error="A selecao contem repositorios duplicados."), 400

            personal_repositories = _repositories(username)
            available = {repo["full_name"].casefold(): repo["full_name"] for repo in personal_repositories}
            requested = []
            for name in selected:
                parts = name.split("/")
                if (
                    len(parts) != 2
                    or parts[0].casefold() != username.casefold()
                    or name.casefold() not in available
                ):
                    return jsonify(error=f"Repositorio pessoal invalido: {name}."), 400
                requested.append(available[name.casefold()])
        except RuntimeError as error:
            logger.error("Erro ao validar repositorios para exclusao: {}", error)
            return jsonify(error=str(error)), 502

        deleted = []
        failures = []
        for full_name in requested:
            result = _run_gh("api", "--method", "DELETE", f"repos/{full_name}")
            if result.returncode == 0:
                deleted.append(full_name)
            else:
                message = _command_error(result)
                logger.error("Erro ao excluir {}: {}", full_name, message)
                failures.append({"repository": full_name, "error": message})

        return jsonify(deleted=deleted, failures=failures)

    return app
