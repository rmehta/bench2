import shutil
from pathlib import Path

import pymysql

from bench_cli.config.mariadb_config import MariaDBConfig
from bench_cli.platform import get_package_manager, is_macos
from bench_cli.utils import run_command

_MACOS_SOCKET_CANDIDATES = ["/tmp/mysql.sock", "/usr/local/var/mysql/mysql.sock"]
_LINUX_SOCKET_CANDIDATES = ["/var/run/mysqld/mysqld.sock", "/run/mysqld/mysqld.sock"]


class MariaDBManager:
    def __init__(self, config: MariaDBConfig) -> None:
        self.config = config

    def is_installed(self) -> bool:
        return bool(shutil.which("mysqld") or shutil.which("mariadbd"))

    def install(self) -> None:
        if self.is_installed():
            return
        package_manager = get_package_manager()
        package = self._brew_package() if is_macos() else self._apt_package()
        package_manager.install(package)

    def _brew_package(self) -> str:
        if self.config.version:
            return f"mariadb@{self.config.version}"
        return "mariadb"

    def _apt_package(self) -> str:
        if self.config.version:
            return f"mariadb-server-{self.config.version}"
        return "mariadb-server"

    def is_running(self) -> bool:
        try:
            connection = self._connect()
            connection.close()
            return True
        except Exception:
            return False

    def start(self) -> None:
        if is_macos():
            run_command(["brew", "services", "start", self._brew_package()])
        else:
            run_command(["sudo", "systemctl", "start", "mariadb"])

    def create_database(self, db_name: str) -> None:
        connection = self._connect()
        with connection.cursor() as cursor:
            cursor.execute(f"CREATE DATABASE IF NOT EXISTS `{db_name}`")
        connection.close()

    def create_user(self, username: str, password: str, db_name: str) -> None:
        connection = self._connect()
        with connection.cursor() as cursor:
            cursor.execute(
                "CREATE USER IF NOT EXISTS %s@'localhost' IDENTIFIED BY %s",
                (username, password),
            )
            cursor.execute(
                f"GRANT ALL PRIVILEGES ON `{db_name}`.* TO %s@'localhost'",
                (username,),
            )
            cursor.execute("FLUSH PRIVILEGES")
        connection.close()

    def _detect_socket(self) -> str:
        if self.config.socket_path:
            return self.config.socket_path
        candidates = _MACOS_SOCKET_CANDIDATES if is_macos() else _LINUX_SOCKET_CANDIDATES
        for path in candidates:
            if Path(path).exists():
                return path
        return ""

    def _connect(self) -> pymysql.Connection:
        socket_path = self._detect_socket()
        if socket_path:
            return pymysql.connect(
                unix_socket=socket_path,
                user=self.config.admin_user,
                password=self.config.root_password or None,
            )
        return pymysql.connect(
            host=self.config.host,
            port=self.config.port,
            user=self.config.admin_user,
            password=self.config.root_password,
        )
