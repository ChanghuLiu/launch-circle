"""Generate an operator credential into private local files; never print the secret."""
import argparse
import os
import secrets
from pathlib import Path

from app.services.admin_auth import password_hash


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-env", required=True, type=Path)
    parser.add_argument("--access-file", required=True, type=Path)
    parser.add_argument("--rotate", action="store_true")
    args = parser.parse_args()
    paths = [args.output_env, args.access_file]
    if any(not p.is_absolute() or not p.parent.is_dir() or p.is_symlink() for p in paths):
        parser.error("Use absolute paths with existing directories and no symlinks")
    if args.output_env == args.access_file:
        parser.error("Output files must differ")
    if not args.rotate and any(p.exists() for p in paths):
        parser.error("Refusing to overwrite credentials without --rotate")
    password = secrets.token_urlsafe(32)
    contents = ["ADMIN_PASSWORD_HASH=" + password_hash(password) + "\n",
                "Launch Circle 管理后台\nhttps://launchcircle-api.duckdns.org/admin\n\n"
                + "管理员密码：\n" + password + "\n\n仅供管理员使用，请保管此文件。\n"]
    for path, content in zip(paths, contents, strict=True):
        flags = os.O_WRONLY | os.O_CREAT | os.O_NOFOLLOW
        flags |= os.O_TRUNC if args.rotate else os.O_EXCL
        fd = os.open(path, flags, 0o600)
        os.fchmod(fd, 0o600)
        with os.fdopen(fd, "w") as stream:
            stream.write(content)
    print("Private operator access files created. No password was printed.")


if __name__ == "__main__":
    main()
