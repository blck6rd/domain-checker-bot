import aiohttp
import asyncio
from datetime import datetime
from typing import Optional, List
from dataclasses import dataclass


@dataclass
class DomainInfo:
    domain: str
    expiry_date: Optional[datetime]
    days_left: Optional[int]
    registrar: Optional[str]
    is_expiring_soon: bool
    error: Optional[str] = None


async def check_domain_async(domain: str, warning_days: int = 31, session: aiohttp.ClientSession = None) -> DomainInfo:
    """
    Проверяет домен через htmlweb.ru API.
    """
    url = f"http://htmlweb.ru/analiz/api.php?whois&url={domain}&json"

    close_session = False
    if session is None:
        session = aiohttp.ClientSession()
        close_session = True

    try:
        async with session.get(url, timeout=aiohttp.ClientTimeout(total=15)) as response:
            if response.status != 200:
                return DomainInfo(
                    domain=domain,
                    expiry_date=None,
                    days_left=None,
                    registrar=None,
                    is_expiring_soon=False,
                    error=f"HTTP {response.status}"
                )

            data = await response.json(content_type=None)

        # Дата истечения в поле "paid" (формат DD.MM.YYYY)
        paid_date = data.get("paid")

        if not paid_date:
            return DomainInfo(
                domain=domain,
                expiry_date=None,
                days_left=None,
                registrar=data.get("registrar"),
                is_expiring_soon=False,
                error="Дата не найдена"
            )

        # Парсим дату
        try:
            expiry_date = datetime.strptime(paid_date, "%d.%m.%Y")
        except ValueError:
            try:
                expiry_date = datetime.strptime(paid_date, "%Y-%m-%d")
            except ValueError:
                return DomainInfo(
                    domain=domain,
                    expiry_date=None,
                    days_left=None,
                    registrar=data.get("registrar"),
                    is_expiring_soon=False,
                    error=f"Формат даты: {paid_date}"
                )

        days_left = (expiry_date - datetime.now()).days

        return DomainInfo(
            domain=domain,
            expiry_date=expiry_date,
            days_left=days_left,
            registrar=data.get("registrar"),
            is_expiring_soon=days_left < warning_days
        )

    except asyncio.TimeoutError:
        return DomainInfo(
            domain=domain,
            expiry_date=None,
            days_left=None,
            registrar=None,
            is_expiring_soon=False,
            error="Таймаут"
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
    finally:
        if close_session:
            await session.close()


async def check_domains_batch(domains: List[str], warning_days: int = 31) -> List[DomainInfo]:
    """
    Проверяет несколько доменов параллельно.
    """
    async with aiohttp.ClientSession() as session:
        tasks = [check_domain_async(d, warning_days, session) for d in domains]
        return await asyncio.gather(*tasks)


def check_domain(domain: str, warning_days: int = 31) -> DomainInfo:
    """Синхронная обёртка."""
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # Если уже в async контексте
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(asyncio.run, check_domain_async(domain, warning_days))
                return future.result()
        else:
            return loop.run_until_complete(check_domain_async(domain, warning_days))
    except RuntimeError:
        return asyncio.run(check_domain_async(domain, warning_days))


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
