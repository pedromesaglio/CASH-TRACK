"""
PDF processing service for extracting expenses from credit card statements
Uses OpenAI GPT-4o-mini for intelligent parsing
"""
import pdfplumber
import re
import json
from datetime import datetime
import os
import requests

# Use direct API call instead of SDK to avoid version compatibility issues
def call_openai_api(messages, model="gpt-4o-mini", temperature=0.1, max_tokens=5000):
    """Call OpenAI API directly using requests - avoids SDK version issues"""
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        raise ValueError("OPENAI_API_KEY not set")

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }

    data = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens
    }

    response = requests.post(
        "https://api.openai.com/v1/chat/completions",
        headers=headers,
        json=data,
        timeout=60
    )

    response.raise_for_status()
    return response.json()


def extract_text_from_pdf(filepath):
    """Extract text from PDF file"""
    text = ""
    with pdfplumber.open(filepath) as pdf:
        for page in pdf.pages:
            text += page.extract_text() + "\n"
    return text


def extract_closing_date_and_cardholder(text):
    """
    Extract closing date and cardholder name from BBVA PDF
    Returns: (closing_date, cardholder_name)
    """
    closing_date = None
    cardholder_name = None

    # Extract cardholder name (appears near the beginning, after "Resumen")
    for idx, line in enumerate(text.split('\n')):
        # Look for name pattern (usually appears before address, after "Resumen")
        # In BBVA format: name appears as "LASTNAME FIRSTNAME" in capitals
        if idx < 50 and re.match(r'^[A-Z\s]{10,}$', line.strip()) and len(line.strip().split()) >= 2:
            potential_name = line.strip()
            # Validate it's a name (not a title or other text)
            if potential_name not in ['RESUMEN', 'PREMIUM WORLD', 'VISA', 'TARJETAS DE CREDITO'] and 'BBVA' not in potential_name:
                cardholder_name = potential_name
                break

    # Extract closing date - look for the actual date value after "CIERRE ACTUAL"
    for idx, line in enumerate(text.split('\n')):
        # Look for "CIERRE ACTUAL" line
        if 'CIERRE ACTUAL' in line:
            # The date is usually in the next line or same line
            # Format: 26-Feb-26
            lines_to_check = [line] + text.split('\n')[idx+1:idx+3]
            for check_line in lines_to_check:
                match = re.search(r'(\d{2})-([A-Za-z]{3})-(\d{2})', check_line)
                if match:
                    day = match.group(1)
                    month_abbr = match.group(2)
                    year = match.group(3)

                    # Convert Spanish month abbreviation to number
                    months = {
                        'Ene': '01', 'Feb': '02', 'Mar': '03', 'Abr': '04',
                        'May': '05', 'Jun': '06', 'Jul': '07', 'Ago': '08',
                        'Sep': '09', 'Oct': '10', 'Nov': '11', 'Dic': '12'
                    }
                    month = months.get(month_abbr, '01')

                    # Assume 20XX for year
                    full_year = f"20{year}"
                    closing_date = f"{full_year}-{month}-{day}"
                    break

            if closing_date:
                break

    # If no closing date found, use today
    if not closing_date:
        closing_date = datetime.now().strftime('%Y-%m-%d')

    return closing_date, cardholder_name


def extract_consumption_lines(text, cardholder_name):
    """
    Extract transaction lines from the cardholder's consumption sections
    """
    lines = text.split('\n')
    consumption_lines = []
    in_consumption_section = False

    for line in lines:
        # Start section if it contains "Consumos" and at least part of the cardholder's name
        if 'Consumos' in line and cardholder_name:
            # Split name into parts (e.g., "MESAGLIO CLARA" -> ["MESAGLIO", "CLARA"])
            name_words = cardholder_name.split()
            # Check if line contains at least the first or last name
            if any(word.lower() in line.lower() for word in name_words):
                in_consumption_section = True
                continue

        # Stop at total or other sections
        if any(keyword in line for keyword in ['TOTAL CONSUMOS', 'Impuestos', 'Legales y avisos', 'SALDO ACTUAL', 'Sus pagos']):
            in_consumption_section = False
            continue

        # Capture transaction lines (excluding BONIF discounts which are already included)
        if in_consumption_section and line.strip():
            # Match lines starting with date pattern, but skip standalone BONIF lines
            if re.match(r'^\d{2}-[A-Za-z]{3}-\d{2}', line):
                # Skip if it's only a bonification line (those are already included in the main transaction)
                if not line.startswith('BONIF'):
                    consumption_lines.append(line.strip())

    return consumption_lines


def parse_transactions_with_openai(transactions_text):
    """
    Parse transactions using OpenAI GPT-4o-mini - works with ANY credit card format
    (BBVA, Santander, Galicia, Visa, Mastercard, American Express, etc.)
    Returns list of expense dictionaries
    """
    try:
        # DEBUG: Log the text being sent to OpenAI
        print("=" * 80)
        print("TEXTO ENVIADO A OPENAI:")
        print(transactions_text)
        print("=" * 80)

        prompt = f"""Sos un experto en análisis de resúmenes de tarjetas de crédito de CUALQUIER banco argentino e internacional.

Analizá CADA transacción de consumo en este texto y devolvé ÚNICAMENTE un JSON array.

TEXTO DEL RESUMEN:
{transactions_text}

FORMATO TÍPICO DE LÍNEA:
DD-MMM-YY DESCRIPCION [MONEDA MONTO] [CUPÓN] MONTO_FINAL

CASOS ESPECIALES - PESOS URUGUAYOS (UYU) - MUY IMPORTANTE:
Cuando una línea contiene "UYU", el formato es:
"DESCRIPCION  UYU  650,00  895542  16,90"
         ↑          ↑       ↑       ↑
    comercio   moneda UYU  cupón   ESTE ES EL MONTO CORRECTO EN USD

REGLAS PARA UYU:
1. Si ves "UYU" en la línea, la transacción es en DÓLARES (USD), NO en pesos argentinos
2. El monto en UYU (ej: 650,00) NO es el monto final - ignoralo
3. Buscá el número que está DESPUÉS del cupón de 6 dígitos - ese es el monto en USD
4. Ejemplo: "PANADERIA BAIPA UYU 987,71 228504 25,68"
   - NO uses 987.71
   - SÍ usá 25.68
   - currency = "USD"

Para CADA transacción de consumo que encuentres, extraé:
- date: YYYY-MM-DD (convertí cualquier formato: DD-MMM-YY, DD/MM/YYYY, etc.)
- description: nombre del comercio/establecimiento (limpio, sin códigos ni números de cupón)
- amount: monto como número decimal (ej: 1234.56)
  * Convertí "1.234,56" → 1234.56
  * Convertí "1,234.56" → 1234.56
  * Si es negativo o bonificación, hacelo positivo
  * **PARA UYU: usá el número DESPUÉS del cupón de 6 dígitos, NO el número después de "UYU"**
- currency:
  * Si la línea contiene "UYU" → "USD" (sí, USD, no ARS!)
  * Si ves "USD" explícitamente → "USD"
  * En cualquier otro caso → "ARS"
- installment_number: "X/Y" si tiene cuotas (ej: "cuota 3/6", "C.03/06" → "3/6"), null si no tiene
- category: Alimentación, Transporte, Salud, Entretenimiento, Servicios, Educación, Ropa, Otros
- payment_method: "Tarjeta de Crédito"

IMPORTANTE:
- Ignorá totales, subtotales, saldos, intereses, impuestos, cargos financieros
- Solo incluí transacciones de consumo reales en comercios
- Si no estás seguro de algo, usá valores por defecto (ARS, Otros, null)
- NO inventes datos

Devolvé SOLO el JSON array sin texto adicional:
[{{"date":"2025-12-04","description":"SUPERMERCADO CARREFOUR","amount":4334.38,"currency":"ARS","category":"Alimentación","payment_method":"Tarjeta de Crédito","installment_number":null}}]"""

        response = call_openai_api(
            messages=[
                {"role": "system", "content": "Sos un experto extrayendo transacciones de resúmenes de tarjetas. Devolvés SOLO JSON válido, nada más."},
                {"role": "user", "content": prompt}
            ],
            model="gpt-4o-mini",
            temperature=0.1,
            max_tokens=5000
        )

        ai_response = response['choices'][0]['message']['content'].strip()

        # DEBUG: Log OpenAI response
        print("=" * 80)
        print("RESPUESTA DE OPENAI:")
        print(ai_response)
        print("=" * 80)

        # Remove markdown code blocks
        ai_response = re.sub(r'```json\s*', '', ai_response)
        ai_response = re.sub(r'```\s*', '', ai_response)
        ai_response = ai_response.strip()

        expenses = json.loads(ai_response)

        # Validate and clean up
        validated_expenses = []
        for expense in expenses:
            required_keys = ['date', 'description', 'amount', 'category', 'payment_method', 'currency']
            if all(key in expense for key in required_keys):
                # Ensure amount is float and positive
                expense['amount'] = abs(float(expense['amount']))
                expense['currency'] = expense['currency'].upper()
                if 'installment_number' not in expense:
                    expense['installment_number'] = None
                validated_expenses.append(expense)

        return validated_expenses

    except Exception as e:
        print(f"⚠️ OpenAI parsing failed: {e}. Falling back to regex...")
        # Fallback to regex parsing if OpenAI fails
        return parse_transactions_with_regex(transactions_text)


def parse_transactions_with_regex(transactions_text):
    """
    Parse transactions using regex patterns (fallback when OpenAI fails)
    Works only with BBVA format: DD-MMM-YY DESCRIPTION [C.XX/YY] [USD AMOUNT] COUPON FINAL_AMOUNT
    Returns list of expense dictionaries
    """
    expenses = []
    lines = transactions_text.strip().split('\n')

    for line in lines:
        if not line.strip():
            continue

        try:
            # Extract date (DD-MMM-YY)
            date_match = re.match(r'(\d{2})-([A-Za-z]{3})-(\d{2})', line)
            if not date_match:
                continue

            day = date_match.group(1)
            month_abbr = date_match.group(2)
            year = date_match.group(3)

            # Convert month abbreviation to number
            months = {
                'Ene': '01', 'Feb': '02', 'Mar': '03', 'Abr': '04',
                'May': '05', 'Jun': '06', 'Jul': '07', 'Ago': '08',
                'Sep': '09', 'Oct': '10', 'Nov': '11', 'Dic': '12',
                'Jan': '01', 'Apr': '04', 'Aug': '08', 'Dec': '12'  # English variants
            }
            month = months.get(month_abbr, '01')
            full_year = f"20{year}"
            date_str = f"{full_year}-{month}-{day}"

            # Remove the date from the line for easier parsing
            line_without_date = line[date_match.end():].strip()

            # Extract installment number (C.XX/YY)
            installment_number = None
            installment_match = re.search(r'C\.(\d{2})/(\d{2})', line_without_date)
            if installment_match:
                current = installment_match.group(1).lstrip('0') or '0'
                total = installment_match.group(2).lstrip('0') or '0'
                installment_number = f"{current}/{total}"
                line_without_date = line_without_date[:installment_match.start()] + line_without_date[installment_match.end():]

            # Detect currency and extract amount
            currency = "ARS"
            amount = 0.0

            # Check for USD
            usd_match = re.search(r'USD\s+([\d.,]+)', line_without_date)
            if usd_match:
                currency = "USD"
                amount_str = usd_match.group(1)
            else:
                # Check for UYU (Uruguayan pesos)
                uyu_match = re.search(r'UYU\s+([\d.,]+)', line_without_date)
                if uyu_match:
                    currency = "ARS"  # Convert to ARS for consistency
                    amount_str = uyu_match.group(1)
                    # UYU to ARS rough conversion (1 UYU ≈ 25 ARS)
                    amount_str = str(float(amount_str.replace('.', '').replace(',', '.')) * 25)
                else:
                    # ARS - get last number in the line
                    amounts = re.findall(r'([\d.]+,\d{2})', line_without_date)
                    if amounts:
                        amount_str = amounts[-1]
                    else:
                        continue

            # Convert amount string to float
            amount_str = amount_str.replace('.', '').replace(',', '.')
            amount = abs(float(amount_str))

            # Extract description (everything between date and numbers/codes)
            # Remove coupon numbers (6-digit numbers)
            desc_line = re.sub(r'\b\d{6,}\b', '', line_without_date)
            # Remove installment info if present
            desc_line = re.sub(r'C\.\d{2}/\d{2}', '', desc_line)
            # Remove USD/UYU and amounts
            desc_line = re.sub(r'(USD|UYU)\s*[\d.,]+', '', desc_line)
            desc_line = re.sub(r'[\d.]+,\d{2}', '', desc_line)
            # Clean up
            description = ' '.join(desc_line.split()).strip()

            if not description:
                description = "Consumo"

            # Categorize based on keywords
            description_lower = description.lower()
            if any(keyword in description_lower for keyword in ['autopista', 'peaje', 'nafta', 'ypf', 'shell', 'axion']):
                category = "Transporte"
            elif any(keyword in description_lower for keyword in ['carrefour', 'super', 'mercado', 'devoto', 'dia']):
                category = "Alimentación"
            elif any(keyword in description_lower for keyword in ['hospital', 'farmacia', 'medic', 'salud', 'doctor']):
                category = "Salud"
            elif any(keyword in description_lower for keyword in ['cine', 'teatro', 'show', 'netflix', 'spotify']):
                category = "Entretenimiento"
            elif any(keyword in description_lower for keyword in ['sancor', 'seguro', 'galeno', 'osde']):
                category = "Servicios"
            elif any(keyword in description_lower for keyword in ['easy', 'sinteplast', 'pintureria', 'ferreteria']):
                category = "Otros"
            elif any(keyword in description_lower for keyword in ['merpago', 'mercado']):
                category = "Otros"
            else:
                category = "Otros"

            expense = {
                'date': date_str,
                'description': description,
                'amount': amount,
                'currency': currency,
                'installment_number': installment_number,
                'category': category,
                'payment_method': 'Tarjeta de Crédito'
            }

            expenses.append(expense)

        except Exception as e:
            print(f"Error parsing line '{line}': {e}")
            continue

    return expenses


def process_pdf_expenses(filepath, user_id, chunk_size=10):
    """
    Main function to process PDF and extract expenses
    Yields progress updates as dictionaries
    """
    try:
        # Step 1: Extract text
        yield {'progress': 10, 'message': 'Extrayendo texto del PDF...'}
        text = extract_text_from_pdf(filepath)

        # Step 2: Extract closing date and cardholder
        closing_date, cardholder_name = extract_closing_date_and_cardholder(text)

        if cardholder_name:
            yield {'progress': 15, 'message': f'Titular: {cardholder_name} | Cierre: {closing_date}'}
        else:
            yield {'progress': 15, 'message': f'Fecha de cierre: {closing_date}'}

        # Step 3: Find transactions
        yield {'progress': 20, 'message': 'Identificando transacciones del titular...'}
        consumption_lines = extract_consumption_lines(text, cardholder_name)

        total_lines = len(consumption_lines)
        yield {'progress': 30, 'message': f'Encontradas {total_lines} transacciones. Procesando con IA...'}

        # Process in chunks
        all_expenses = []
        total_chunks = (total_lines - 1) // chunk_size + 1 if total_lines > 0 else 1

        for chunk_idx in range(0, total_lines, chunk_size):
            current_chunk = (chunk_idx // chunk_size) + 1
            chunk = consumption_lines[chunk_idx:chunk_idx + chunk_size]

            progress = 30 + int((current_chunk / total_chunks) * 50)
            yield {'progress': progress, 'message': f'Procesando grupo {current_chunk} de {total_chunks}...'}

            transactions_text = '\n'.join(chunk)
            chunk_expenses = parse_transactions_with_openai(transactions_text)
            all_expenses.extend(chunk_expenses)

        # Step 4: Insert into database
        yield {'progress': 85, 'message': f'Guardando {len(all_expenses)} gastos en la base de datos...'}

        from database import get_db
        conn = get_db()
        cursor = conn.cursor()
        inserted_count = 0

        for expense in all_expenses:
            try:
                # Use closing_date instead of original transaction date
                cursor.execute('''
                    INSERT INTO expenses (user_id, date, category, description, payment_method, amount, currency, installment_number)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                ''', (user_id, closing_date, expense['category'],
                      expense['description'], expense['payment_method'], expense['amount'],
                      expense.get('currency', 'ARS'), expense.get('installment_number')))
                inserted_count += 1
            except Exception as e:
                print(f"Error insertando gasto: {e}")
                continue

        conn.commit()
        conn.close()

        # Step 5: Complete
        yield {'progress': 100, 'message': f'¡Completado! {inserted_count} gastos importados.', 'complete': True, 'count': inserted_count}

    except Exception as e:
        yield {'error': str(e)}
