#!/usr/bin/env python3

from decimal import Decimal, ROUND_HALF_UP, InvalidOperation, getcontext
from pathlib import Path
from datetime import datetime, date
import json
import urllib.request
import urllib.error

# Presición suficiente para conversiones monetarias cotidianas
getcontext().prec = 28

# Monedas soportadas; puedes agregar o quitar.
SUPPORTED = {
    "USD", "EUR", "MXN", "ARS", "COP", "CLP", "PEN",
    "GBP", "JPY", "BRL", "CAD",
}

# Tasas por defecto: 1 USD equivale a X de la moneda indicada
RATES = {
    "USD": Decimal("1"),
    "EUR": Decimal("0.92"),
    "MXN": Decimal("19.8"),
    "ARS": Decimal("980"),
    "COP": Decimal("3940"),
    "CLP": Decimal("910"),
    "PEN": Decimal("3.75"),
    "GBP": Decimal("0.78"),
    "JPY": Decimal("146.5"),
    "BRL": Decimal("5.1"),
    "CAD": Decimal("1.36"),
}

# Archivo de caché con tasas y control de frecuencia (2/día)
CACHE_PATH = Path(__file__).with_name(".rates_cache.json")


def _today_str() -> str:
    return date.today().isoformat()


def _load_cache():
    if not CACHE_PATH.exists():
        return None
    try:
        with CACHE_PATH.open("r", encoding="utf-8") as fh:
            return json.load(fh)
    except Exception:
        return None


def _save_cache(data: dict) -> None:
    try:
        with CACHE_PATH.open("w", encoding="utf-8") as fh:
            json.dump(data, fh, ensure_ascii=False, indent=2)
    except Exception:
        pass


def _apply_cached_rates():
    cache = _load_cache()
    if not cache:
        return
    rates = cache.get("rates")
    if not isinstance(rates, dict):
        return
    updated = 0
    for code, value in rates.items():
        try:
            if code in SUPPORTED:
                RATES[code] = Decimal(str(value))
                updated += 1
        except Exception:
            pass
    return updated


def listar_monedas():
    cache = _load_cache() or {}
    last_updated = cache.get("last_updated")
    day = cache.get("day")
    fetch_count = cache.get("fetch_count", 0)
    remaining = max(0, 2 - fetch_count) if day == _today_str() else 2

    print("Monedas disponibles (base 1 USD):")
    for code in sorted(RATES.keys()):
        print(f"- {code}: {RATES[code]} por USD")
    if last_updated:
        print(f"\nÚltima actualización API: {last_updated} (UTC)")
        print(f"Actualizaciones restantes hoy: {remaining}")


def normaliza_codigo(codigo: str) -> str:
    return codigo.strip().upper()


def leer_monto(prompt: str) -> Decimal:
    while True:
        raw = input(prompt).strip().replace(",", ".")
        try:
            val = Decimal(raw)
            if val < 0:
                print("El monto no puede ser negativo.")
                continue
            return val
        except InvalidOperation:
            print("Monto inválido. Intenta de nuevo (ej: 1234.56)")


def leer_moneda(prompt: str) -> str:
    while True:
        code = normaliza_codigo(input(prompt))
        if code in RATES:
            return code
        print("Moneda no reconocida. Usa uno de estos códigos:")
        print(", ".join(sorted(RATES.keys())))


def convertir(monto: Decimal, desde: str, hacia: str) -> Decimal:
    if desde == hacia:
        return monto
    # 1 USD = RATES[moneda]
    # monto_en_usd = monto / RATES[desde]
    # monto_en_hacia = monto_en_usd * RATES[hacia]
    usd = monto / RATES[desde]
    result = usd * RATES[hacia]
    return result


def formatea(valor: Decimal, code: str) -> str:
    # Redondear a 2 decimales por defecto para presentación
    q = Decimal("0.01")
    return f"{valor.quantize(q, rounding=ROUND_HALF_UP)} {code}"


def _fetch_rates_from_api(base: str = "USD") -> dict:
    """Obtiene tasas desde una API pública (sin API key).

    Devuelve un dict {code: Decimal} con base 1 USD.
    """
    # Usamos exchangerate.host (gratis, sin API key)
    url = f"https://api.exchangerate.host/latest?base={base}"
    req = urllib.request.Request(url, headers={"User-Agent": "currency-converter/1.0"})
    with urllib.request.urlopen(req, timeout=10) as resp:
        # Parsear JSON usando Decimal para los números
        text = resp.read().decode("utf-8")
        data = json.loads(text, parse_float=Decimal)
    if not isinstance(data, dict) or "rates" not in data:
        raise RuntimeError("Respuesta de API inválida")
    rates = data["rates"]
    out = {"USD": Decimal("1")}
    for code, val in rates.items():
        if not isinstance(val, (int, float, Decimal)):
            try:
                val = Decimal(str(val))
            except Exception:
                continue
        try:
            out[code] = Decimal(val)
        except Exception:
            continue
    return out


def actualizar_tasas_api(max_updates_per_day: int = 2) -> bool:
    """Actualiza tasas desde Internet respetando un máximo diario.

    Retorna True si se actualizaron, False si no (por límite o error).
    """
    cache = _load_cache() or {}
    today = _today_str()
    if cache.get("day") == today and cache.get("fetch_count", 0) >= max_updates_per_day:
        print("Has alcanzado el límite de 2 actualizaciones hoy.")
        return False
    try:
        all_rates = _fetch_rates_from_api("USD")
    except (urllib.error.URLError, urllib.error.HTTPError) as e:
        print(f"No se pudo conectar a la API: {e}")
        return False
    except Exception as e:
        print(f"Error al obtener tasas: {e}")
        return False

    # Aplicar solo las monedas soportadas para mantener la UI controlada
    updated = 0
    for code in SUPPORTED:
        if code in all_rates:
            RATES[code] = Decimal(all_rates[code])
            updated += 1
    # Persistir en caché
    new_count = 1
    if cache.get("day") == today:
        new_count = int(cache.get("fetch_count", 0)) + 1
    cache_data = {
        "last_updated": datetime.utcnow().isoformat(timespec="seconds") + "Z",
        "day": today,
        "fetch_count": new_count,
        "rates": {k: str(RATES[k]) for k in RATES},
    }
    _save_cache(cache_data)

    print(f"Tasas actualizadas desde la API. Monedas actualizadas: {updated}")
    print(f"Restantes hoy: {max(0, max_updates_per_day - new_count)}")
    return True


def actualizar_tasa():
    listar_monedas()
    code = leer_moneda("\nCódigo de moneda a actualizar: ")
    while True:
        raw = input(
            f"Nueva tasa para {code} (unidades de {code} por 1 USD): "
        ).strip().replace(",", ".")
        try:
            val = Decimal(raw)
            if val <= 0:
                print("La tasa debe ser mayor que 0.")
                continue
            RATES[code] = val
            print(f"Tasa actualizada: 1 USD = {val} {code}")
            return
        except InvalidOperation:
            print("Valor inválido. Intenta de nuevo (ej: 3.75)")


def flujo_conversion():
    listar_monedas()
    print("")
    monto = leer_monto("Monto a convertir: ")
    desde = leer_moneda("Desde (código): ")
    hacia = leer_moneda("Hacia (código): ")
    resultado = convertir(monto, desde, hacia)
    print("")
    print(f"{formatea(monto, desde)} = {formatea(resultado, hacia)}")


def menu():
    print("Conversor de Monedas (tasas vía API + caché)")
    print("- Límite: hasta 2 actualizaciones por día.")
    while True:
        print("\nOpciones:")
        print("1) Convertir monto")
        print("2) Listar monedas y tasas")
        print("3) Actualizar tasas desde Internet (máx 2/día)")
        print("4) Actualizar una tasa manualmente")
        print("5) Salir")
        op = input("Selecciona una opción (1-5): ").strip()
        if op == "1":
            try:
                flujo_conversion()
            except Exception as e:
                print(f"Ocurrió un error: {e}")
        elif op == "2":
            listar_monedas()
        elif op == "3":
            actualizar_tasas_api()
        elif op == "4":
            actualizar_tasa()
        elif op == "5":
            print("Hasta luego 👋")
            break
        else:
            print("Opción inválida. Intenta de nuevo.")


if __name__ == "__main__":
    # Cargar tasas desde caché si existe
    _apply_cached_rates()

    # Intentar una actualización automática si quedan cupos hoy
    try:
        cache = _load_cache() or {}
        today = _today_str()
        fetch_count = cache.get("fetch_count", 0) if cache.get("day") == today else 0
        remaining = max(0, 2 - int(fetch_count))
        if remaining > 0:
            print("Intentando actualización automática desde la API...")
            actualizar_tasas_api()
    except Exception:
        # No interrumpir el inicio del programa por fallos de red o caché
        pass

    menu()
