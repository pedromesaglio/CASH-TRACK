"""
Web scraper for getting USD/ARS exchange rate (Dolar MEP) from Argentine sources
"""
import requests

def get_dollar_mep_rate():
    """
    Get dolar MEP rate from dolarapi.com
    Returns: float with the sell rate, or None if failed
    """
    try:
        # Primary source: dolarapi.com (more reliable and updated)
        url = "https://dolarapi.com/v1/dolares/bolsa"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }

        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()

        data = response.json()

        # Get the "venta" (sell) price
        venta = data.get('venta')
        if venta:
            return float(venta)

        return None

    except Exception as e:
        print(f"Error getting dollar MEP rate from dolarapi.com: {e}")
        return None


def get_dollar_blue_rate():
    """
    Get dolar blue rate as fallback from dolarapi.com
    Returns: float with the sell rate, or None if failed
    """
    try:
        url = "https://dolarapi.com/v1/dolares/blue"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }

        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()

        data = response.json()

        # Get the "venta" (sell) price
        venta = data.get('venta')
        if venta:
            return float(venta)

        return None

    except Exception as e:
        print(f"Error getting dollar blue rate: {e}")
        return None


def get_dollar_rate_with_fallback():
    """
    Try to get dollar MEP rate, if it fails, try blue rate
    If both fail, return a default value
    Returns: float with exchange rate
    """
    # Try MEP rate first (your preferred rate)
    rate = get_dollar_mep_rate()
    if rate:
        print(f"✅ Dólar MEP obtenido: ${rate:.2f}")
        return rate

    # Fallback to blue rate
    rate = get_dollar_blue_rate()
    if rate:
        print(f"⚠️ Dólar MEP no disponible. Usando Dólar Blue: ${rate:.2f}")
        return rate

    # Last fallback: use a default value
    default_rate = 1465.0  # Update this periodically (MEP típicamente ~1400-1500)
    print(f"⚠️ No se pudo obtener cotización. Usando valor por defecto: ${default_rate:.2f}")
    return default_rate


if __name__ == "__main__":
    # Test the scraper
    print("Testing Dollar Scraper (MEP)...")
    print("-" * 50)

    mep_rate = get_dollar_mep_rate()
    if mep_rate:
        print(f"Dólar MEP (Bolsa): ${mep_rate:.2f}")
    else:
        print("❌ Failed to get Dólar MEP")

    blue_rate = get_dollar_blue_rate()
    if blue_rate:
        print(f"Dólar Blue (fallback): ${blue_rate:.2f}")
    else:
        print("❌ Failed to get Dólar Blue")

    print("-" * 50)
    print(f"Final rate (with fallback): ${get_dollar_rate_with_fallback():.2f}")
