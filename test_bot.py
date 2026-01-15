#!/usr/bin/env python3
"""
Тестовый скрипт для проверки работы модулей без Telegram.
"""

import sys
import os

# Добавляем путь к модулям
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from whois_checker import check_domain, format_domain_info
from domain_manager import DomainManager


def test_whois_checker():
    """Тестирует WHOIS проверку."""
    print("=" * 50)
    print("ТЕСТ WHOIS ПРОВЕРКИ")
    print("=" * 50)

    test_domains = ["google.com", "github.com", "example.com"]

    for domain in test_domains:
        print(f"\nПроверяю {domain}...")
        info = check_domain(domain)
        print(format_domain_info(info))


def test_domain_manager():
    """Тестирует менеджер доменов."""
    print("\n" + "=" * 50)
    print("ТЕСТ МЕНЕДЖЕРА ДОМЕНОВ")
    print("=" * 50)

    # Используем тестовый файл
    test_file = "test_domains.json"
    manager = DomainManager(test_file)

    # Очищаем
    manager._save_domains([])

    print("\n1. Добавление доменов:")
    print(manager.add_domain("test1.com"))
    print(manager.add_domain("test2.com"))
    print(manager.add_domain("test1.com"))  # Дубликат

    print("\n2. Список доменов:")
    print(manager.get_all_domains())

    print("\n3. Редактирование:")
    print(manager.update_domain("test1.com", "test1-new.com"))

    print("\n4. После редактирования:")
    print(manager.get_all_domains())

    print("\n5. Удаление:")
    print(manager.remove_domain("test2.com"))

    print("\n6. Финальный список:")
    print(manager.get_all_domains())

    # Удаляем тестовый файл
    if os.path.exists(test_file):
        os.remove(test_file)
        print("\nТестовый файл удалён")


def test_config():
    """Проверяет конфигурацию."""
    print("\n" + "=" * 50)
    print("ПРОВЕРКА КОНФИГУРАЦИИ")
    print("=" * 50)

    from config import BOT_TOKEN, DOMAINS_FILE, EXPIRY_WARNING_DAYS

    print(f"Файл доменов: {DOMAINS_FILE}")
    print(f"Порог предупреждения: {EXPIRY_WARNING_DAYS} дней")

    if BOT_TOKEN == "YOUR_BOT_TOKEN_HERE":
        print("⚠️  Токен бота НЕ установлен!")
        print("   Установите: export TELEGRAM_BOT_TOKEN='ваш_токен'")
    else:
        print("✅ Токен бота установлен")


def main():
    print("ТЕСТИРОВАНИЕ DOMAIN CHECKER BOT")
    print("=" * 50)

    test_config()
    test_domain_manager()
    test_whois_checker()

    print("\n" + "=" * 50)
    print("ТЕСТИРОВАНИЕ ЗАВЕРШЕНО")
    print("=" * 50)


if __name__ == "__main__":
    main()
