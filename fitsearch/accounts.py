import argparse
import getpass
import os
from pathlib import Path

from .auth import AuthDB, Principal
from .runtime import ProfileStores


def data_directory() -> Path:
    return Path(os.getenv("FITSEARCH_DATA", Path.home() / ".local/share/fitsearch"))


def ask_password(confirm: bool = True) -> str:
    password = getpass.getpass("Mot de passe : ")
    if confirm and password != getpass.getpass("Confirmation : "):
        raise ValueError("Les mots de passe ne correspondent pas")
    return password


def main():
    parser = argparse.ArgumentParser(description="Gestion locale des comptes FitSearch")
    sub = parser.add_subparsers(dest="command", required=True)
    create = sub.add_parser("create")
    create.add_argument("username")
    create.add_argument("--role", choices=("admin", "user"), default="user")
    password = sub.add_parser("password")
    password.add_argument("username")
    sub.add_parser("list")
    args = parser.parse_args()

    data = data_directory()
    auth = AuthDB(data / "auth.db")
    try:
        if args.command == "create":
            identifier = auth.create_user(args.username, ask_password(), args.role)
            principal = Principal(identifier, auth.normalize_username(args.username), args.role)
            if args.role == "admin" and auth.count_users() == 1:
                ProfileStores(data, True).migrate_legacy_profile(principal)
                print("Données historiques attribuées au premier administrateur.")
            print(f"Compte {principal.username} créé avec le rôle {principal.role}.")
        elif args.command == "password":
            users = {item["username"]: item for item in auth.list_users()}
            username = auth.normalize_username(args.username)
            if username not in users:
                raise ValueError("Compte inconnu")
            auth.set_password(users[username]["id"], ask_password())
            print(f"Mot de passe de {username} remplacé ; sessions révoquées.")
        else:
            for item in auth.list_users():
                state = "actif" if item["enabled"] else "désactivé"
                print(f"{item['id']:>4}  {item['username']:<40} {item['role']:<5} {state}")
    except ValueError as exc:
        parser.error(str(exc))


if __name__ == "__main__":
    main()
