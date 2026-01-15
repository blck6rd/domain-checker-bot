import whois
from datetime import datetime, timedelta
from typing import Optional
from dataclasses import dataclass


@dataclass
class DomainInfo:
    domain: str
    expiry_date: Optional[datetime]
    days_left: Optional[int]
    registrar: Optional[str]
    is_expiring_soon: bool
    error: Optional[str] = None


def check_domain(domain: str, warning_days: int = 31) -> DomainInfo:
    """
    Проверяет домен через WHOIS и возвращает информацию о нём.

    Args:
        domain: доменное имя для проверки
        warning_days: порог дней для предупреждения об истечении

    Returns:
        DomainInfo с данными о домене
    """
    try:
        w = whois.whois(domain)

        # Получаем дату истечения
        expiry_date = w.expiration_date

        # Иногда возвращается список дат
        if isinstance(expiry_date, list):
            expiry_date = expiry_date[0]

        if expiry_date is None:
            return DomainInfo(
                domain=domain,
                expiry_date=None,
                days_left=None,
                registrar=w.registrar,
                is_expiring_soon=False,
                error="Не удалось получить дату истечения"
            )

        # Вычисляем оставшиеся дни
        now = datetime.now()
        days_left = (expiry_date - now).days

        return DomainInfo(
            domain=domain,
            expiry_date=expiry_date,
            days_left=days_left,
            registrar=w.registrar,
            is_expiring_soon=days_left < warning_days
        )

    except Exception as e:
        return DomainInfo(
            domain=domain,
            expiry_date=None,
            days_left=None,
            registrar=None,
            is_expiring_soon=False,
            error=str(e)
        )


def format_domain_info(info: DomainInfo) -> str:
    """Форматирует информацию о домене для отображения."""
    if info.error:
        return f"❌ {info.domain}\n   Ошибка: {info.error}"

    if info.expiry_date is None:
        return f"⚠️ {info.domain}\n   Дата истечения не определена"

    expiry_str = info.expiry_date.strftime("%d.%m.%Y")

    if info.is_expiring_soon:
        emoji = "🔴"
        status = f"ИСТЕКАЕТ ЧЕРЕЗ {info.days_left} дней!"
    elif info.days_left <= 60:
        emoji = "🟡"
        status = f"Осталось {info.days_left} дней"
    else:
        emoji = "🟢"
        status = f"Осталось {info.days_left} дней"

    result = f"{emoji} {info.domain}\n"
    result += f"   Истекает: {expiry_str}\n"
    result += f"   Статус: {status}"

    if info.registrar:
        result += f"\n   Регистратор: {info.registrar}"

    return result
