import whois
from datetime import datetime
from typing import Optional, List
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor, as_completed


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
    Проверяет домен через WHOIS.
    """
    try:
        w = whois.whois(domain)

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
                error="Дата не найдена"
            )

        days_left = (expiry_date - datetime.now()).days

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
            error=str(e)[:50]
        )


def check_domains_batch(domains: List[str], warning_days: int = 31, max_workers: int = 10) -> List[DomainInfo]:
    """
    Проверяет несколько доменов параллельно (до 10 одновременно).
    """
    results = []
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(check_domain, d, warning_days): d for d in domains}
        for future in as_completed(futures):
            results.append(future.result())

    # Сортируем по порядку входных доменов
    domain_order = {d: i for i, d in enumerate(domains)}
    results.sort(key=lambda x: domain_order.get(x.domain, 999))
    return results


def format_domain_info(info: DomainInfo) -> str:
    """Форматирует информацию о домене."""
    if info.error:
        return f"❌ {info.domain}\n   Ошибка: {info.error}"

    if info.expiry_date is None:
        return f"⚠️ {info.domain}\n   Дата не определена"

    expiry_str = info.expiry_date.strftime("%d.%m.%Y")

    if info.is_expiring_soon:
        emoji = "🔴"
        status = f"ИСТЕКАЕТ ЧЕРЕЗ {info.days_left} дн!"
    elif info.days_left <= 60:
        emoji = "🟡"
        status = f"Осталось {info.days_left} дн"
    else:
        emoji = "🟢"
        status = f"Осталось {info.days_left} дн"

    result = f"{emoji} {info.domain}\n"
    result += f"   Истекает: {expiry_str}\n"
    result += f"   Статус: {status}"

    if info.registrar:
        result += f"\n   Регистратор: {info.registrar}"

    return result
