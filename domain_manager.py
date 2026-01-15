import json
import os
from typing import List, Optional, Dict, Tuple
from config import DOMAINS_FILE


class DomainManager:
    """Менеджер для работы с JSON хранилищем доменов и аккаунтов."""

    def __init__(self, file_path: str = DOMAINS_FILE):
        self.file_path = file_path
        self._ensure_file_exists()

    def _ensure_file_exists(self):
        """Создаёт файл если его нет."""
        if not os.path.exists(self.file_path):
            self._save_data({"accounts": {}})

    def _load_data(self) -> dict:
        """Загружает данные из JSON файла."""
        try:
            with open(self.file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            return {"accounts": {}}

    def _save_data(self, data: dict):
        """Сохраняет данные в JSON файл."""
        with open(self.file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def get_all_accounts(self) -> Dict[str, List[str]]:
        """Возвращает все аккаунты с доменами."""
        data = self._load_data()
        return data.get("accounts", {})

    def get_all_domains(self) -> List[str]:
        """Возвращает все домены (плоский список)."""
        accounts = self.get_all_accounts()
        domains = []
        for account_domains in accounts.values():
            domains.extend(account_domains)
        return domains

    def get_domains_by_account(self, account: str) -> List[str]:
        """Возвращает домены конкретного аккаунта."""
        accounts = self.get_all_accounts()
        return accounts.get(account, [])

    def find_domain(self, domain: str) -> Optional[str]:
        """
        Ищет домен и возвращает аккаунт, к которому он принадлежит.

        Returns:
            email аккаунта или None если не найден
        """
        domain = domain.lower().strip()
        accounts = self.get_all_accounts()

        for account, domains in accounts.items():
            if domain in [d.lower() for d in domains]:
                return account
        return None

    def search_domains(self, query: str) -> List[Tuple[str, str]]:
        """
        Ищет домены по частичному совпадению.

        Returns:
            Список кортежей (домен, аккаунт)
        """
        query = query.lower().strip()
        results = []
        accounts = self.get_all_accounts()

        for account, domains in accounts.items():
            for domain in domains:
                if query in domain.lower():
                    results.append((domain, account))
        return results

    def add_domain(self, domain: str, account: str = None) -> Tuple[bool, str]:
        """
        Добавляет домен к аккаунту.
        Если аккаунт не указан, добавляет к первому аккаунту.
        """
        domain = domain.lower().strip()

        if not domain or '.' not in domain:
            return False, "Некорректный формат домена"

        data = self._load_data()
        accounts = data.get("accounts", {})

        # Проверяем, не существует ли домен
        existing = self.find_domain(domain)
        if existing:
            return False, f"Домен {domain} уже существует в {existing}"

        # Если аккаунт не указан, берём первый
        if not account:
            if not accounts:
                return False, "Нет аккаунтов. Сначала создайте аккаунт."
            account = list(accounts.keys())[0]

        if account not in accounts:
            accounts[account] = []

        accounts[account].append(domain)
        data["accounts"] = accounts
        self._save_data(data)
        return True, f"Домен {domain} добавлен к {account}"

    def remove_domain(self, domain: str) -> Tuple[bool, str]:
        """Удаляет домен из любого аккаунта."""
        domain = domain.lower().strip()

        data = self._load_data()
        accounts = data.get("accounts", {})

        for account, domains in accounts.items():
            domains_lower = [d.lower() for d in domains]
            if domain in domains_lower:
                idx = domains_lower.index(domain)
                removed = domains.pop(idx)
                data["accounts"] = accounts
                self._save_data(data)
                return True, f"Домен {removed} удалён из {account}"

        return False, f"Домен {domain} не найден"

    def update_domain(self, old_domain: str, new_domain: str) -> Tuple[bool, str]:
        """Переименовывает домен."""
        old_domain = old_domain.lower().strip()
        new_domain = new_domain.lower().strip()

        if not new_domain or '.' not in new_domain:
            return False, "Некорректный формат нового домена"

        # Проверяем, не существует ли новый домен
        if self.find_domain(new_domain):
            return False, f"Домен {new_domain} уже существует"

        data = self._load_data()
        accounts = data.get("accounts", {})

        for account, domains in accounts.items():
            domains_lower = [d.lower() for d in domains]
            if old_domain in domains_lower:
                idx = domains_lower.index(old_domain)
                domains[idx] = new_domain
                data["accounts"] = accounts
                self._save_data(data)
                return True, f"Домен {old_domain} изменён на {new_domain}"

        return False, f"Домен {old_domain} не найден"

    def add_account(self, account: str) -> Tuple[bool, str]:
        """Добавляет новый аккаунт."""
        account = account.strip()

        data = self._load_data()
        accounts = data.get("accounts", {})

        if account in accounts:
            return False, f"Аккаунт {account} уже существует"

        accounts[account] = []
        data["accounts"] = accounts
        self._save_data(data)
        return True, f"Аккаунт {account} добавлен"

    def remove_account(self, account: str) -> Tuple[bool, str]:
        """Удаляет аккаунт со всеми доменами."""
        data = self._load_data()
        accounts = data.get("accounts", {})

        if account not in accounts:
            return False, f"Аккаунт {account} не найден"

        domain_count = len(accounts[account])
        del accounts[account]
        data["accounts"] = accounts
        self._save_data(data)
        return True, f"Аккаунт {account} удалён ({domain_count} доменов)"

    def get_accounts_list(self) -> List[str]:
        """Возвращает список аккаунтов."""
        return list(self.get_all_accounts().keys())

    def get_domains_count(self) -> int:
        """Возвращает общее количество доменов."""
        return len(self.get_all_domains())

    def get_accounts_count(self) -> int:
        """Возвращает количество аккаунтов."""
        return len(self.get_all_accounts())

    def get_stats(self) -> Dict:
        """Возвращает статистику."""
        accounts = self.get_all_accounts()
        return {
            "accounts_count": len(accounts),
            "domains_count": sum(len(d) for d in accounts.values()),
            "accounts": {acc: len(domains) for acc, domains in accounts.items()}
        }
