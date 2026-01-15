import json
import os
from typing import List, Optional
from config import DOMAINS_FILE


class DomainManager:
    """Менеджер для работы с JSON хранилищем доменов."""

    def __init__(self, file_path: str = DOMAINS_FILE):
        self.file_path = file_path
        self._ensure_file_exists()

    def _ensure_file_exists(self):
        """Создаёт файл если его нет."""
        if not os.path.exists(self.file_path):
            self._save_domains([])

    def _load_data(self) -> dict:
        """Загружает данные из JSON файла."""
        try:
            with open(self.file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            return {"domains": []}

    def _save_data(self, data: dict):
        """Сохраняет данные в JSON файл."""
        with open(self.file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def _save_domains(self, domains: List[str]):
        """Сохраняет список доменов."""
        self._save_data({"domains": domains})

    def get_all_domains(self) -> List[str]:
        """Возвращает все домены."""
        data = self._load_data()
        return data.get("domains", [])

    def add_domain(self, domain: str) -> tuple[bool, str]:
        """
        Добавляет домен.

        Returns:
            (успех, сообщение)
        """
        domain = domain.lower().strip()

        # Базовая валидация
        if not domain or '.' not in domain:
            return False, "Некорректный формат домена"

        domains = self.get_all_domains()

        if domain in domains:
            return False, f"Домен {domain} уже существует"

        domains.append(domain)
        self._save_domains(domains)
        return True, f"Домен {domain} добавлен"

    def remove_domain(self, domain: str) -> tuple[bool, str]:
        """
        Удаляет домен.

        Returns:
            (успех, сообщение)
        """
        domain = domain.lower().strip()
        domains = self.get_all_domains()

        if domain not in domains:
            return False, f"Домен {domain} не найден"

        domains.remove(domain)
        self._save_domains(domains)
        return True, f"Домен {domain} удалён"

    def update_domain(self, old_domain: str, new_domain: str) -> tuple[bool, str]:
        """
        Обновляет (переименовывает) домен.

        Returns:
            (успех, сообщение)
        """
        old_domain = old_domain.lower().strip()
        new_domain = new_domain.lower().strip()

        if not new_domain or '.' not in new_domain:
            return False, "Некорректный формат нового домена"

        domains = self.get_all_domains()

        if old_domain not in domains:
            return False, f"Домен {old_domain} не найден"

        if new_domain in domains:
            return False, f"Домен {new_domain} уже существует"

        index = domains.index(old_domain)
        domains[index] = new_domain
        self._save_domains(domains)
        return True, f"Домен {old_domain} изменён на {new_domain}"

    def domain_exists(self, domain: str) -> bool:
        """Проверяет существование домена."""
        return domain.lower().strip() in self.get_all_domains()

    def get_domains_count(self) -> int:
        """Возвращает количество доменов."""
        return len(self.get_all_domains())
