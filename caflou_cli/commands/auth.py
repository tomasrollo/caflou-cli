import datetime
import os
import sys
import time
from typing import Optional

import typer

from caflou_cli import api
from caflou_cli.config import load_config, save_config
from caflou_cli.output import error

app = typer.Typer(help="Authentication commands.")


@app.command("login")
def auth_login(
    email: Optional[str] = typer.Option(
        None, "--email", "-e",
        help="Email address.",
        envvar=["CAFLOU_EMAIL", "CAFLOU_USERNAME"],
    ),
    password: Optional[str] = typer.Option(
        None, "--password", "-p",
        help="Password.",
        envvar="CAFLOU_PASSWORD",
    ),
    account: Optional[str] = typer.Option(
        None, "--account",
        help="Set this account as default (name or partial ID).",
    ),
) -> None:
    """Authenticate and save credentials to ~/.config/caflou-cli/config.json."""
    if not email:
        email = typer.prompt("Email")
    if not password:
        password = typer.prompt("Password", hide_input=True)

    typer.echo("Logging in...")
    token_data = api.login(email, password)
    token = token_data["access_token"]
    expires_at = token_data.get("expires_at")

    accounts = api.get_accounts(token)

    default_account_id: Optional[str] = None

    if account:
        for a in accounts:
            if a["id"] == account or account.lower() in a["name"].lower():
                default_account_id = a["id"]
                break
        if not default_account_id:
            error(f"Account '{account}' not found. Available: {', '.join(a['name'] for a in accounts)}")
    elif len(accounts) == 1:
        default_account_id = accounts[0]["id"]
        typer.echo(f"Account: {accounts[0]['name']}")
    else:
        typer.echo("Available accounts:")
        for i, a in enumerate(accounts, 1):
            typer.echo(f"  {i}. {a['name']} ({a['id']})")

        if sys.stdin.isatty():
            choice = typer.prompt("Select default account", default="1")
            try:
                idx = int(choice) - 1
                default_account_id = accounts[idx]["id"]
            except (ValueError, IndexError):
                error("Invalid selection.")
        else:
            default_account_id = accounts[0]["id"]
            typer.echo(
                f"Non-interactive: using first account '{accounts[0]['name']}'",
                err=True,
            )

    save_config({
        "token": token,
        "token_expires_at": expires_at,
        "default_account_id": default_account_id,
        "accounts": accounts,
    })

    selected = next((a for a in accounts if a["id"] == default_account_id), {})
    typer.echo(f"Logged in. Default account: {selected.get('name', default_account_id)}")


@app.command("whoami")
def auth_whoami() -> None:
    """Show current authentication state."""
    config = load_config()
    token = os.environ.get("CAFLOU_TOKEN") or config.get("token")

    if not token:
        typer.echo("Not logged in.")
        raise typer.Exit(2)

    expires_at = config.get("token_expires_at")
    if expires_at and expires_at < time.time():
        typer.echo("Token expired. Run 'caflou auth login'.")
        raise typer.Exit(2)

    default_account_id = (
        os.environ.get("CAFLOU_ACCOUNT_ID") or config.get("default_account_id")
    )
    accounts = config.get("accounts", [])
    default_account = next((a for a in accounts if a["id"] == default_account_id), None)

    token_source = "env" if os.environ.get("CAFLOU_TOKEN") else "config"
    typer.echo(f"token:           set (from {token_source})")
    if expires_at:
        exp_dt = datetime.datetime.fromtimestamp(expires_at)
        typer.echo(f"token_expires:   {exp_dt.strftime('%Y-%m-%d %H:%M')}")
    typer.echo(
        f"default_account: {default_account['name'] if default_account else default_account_id or 'not set'}"
    )
    if accounts:
        typer.echo(f"accounts:        {', '.join(a['name'] for a in accounts)}")
