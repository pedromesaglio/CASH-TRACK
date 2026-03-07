"""
PDF processing service for extracting expenses from credit card statements
"""
import pdfplumber
import re
import json
import ollama
from datetime import datetime


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

    # Extract closing date
    for line in text.split('\n'):
        # Look for "CIERRE ACTUAL" line
        if 'CIERRE ACTUAL' in line:
            # Try to find a date in format DD-MMM-YY
            match = re.search(r'(\d{2})-([A-Za-z]{3})-(\d{2})', line)
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


def parse_transactions_with_ai(transactions_text):
    """
    Parse transactions using Ollama AI
    Returns list of expense dictionaries
    """
    prompt = f"""Sos un experto en análisis de resúmenes de tarjetas de crédito BBVA Argentina.

Analizá CADA LÍNEA del siguiente listado de transacciones y devolvé ÚNICAMENTE un JSON array.

Transacciones:
{transactions_text}

Formato de cada línea:
FECHA DESCRIPCIÓN [C.XX/YY si tiene cuotas] [USD MONTO_USD] NRO_CUPON MONTO_PESOS [DÓLARES si es USD]

Para CADA transacción extraé:
- fecha: YYYY-MM-DD (año 2026 si dice "26", 2025 si dice "25", 2024 si dice "24")
- description: comercio/descripción (limpio, sin números de cupón ni códigos)
- amount: monto NUMÉRICO
  * Si el monto tiene formato "1.234,56" convertilo a 1234.56
  * Si es negativo (descuento/bonificación) devolvelo como positivo
  * NUNCA uses comas ni puntos como separadores de miles, solo punto decimal
  * Ejemplos: "4.334,38" → 4334.38, "35.000,00" → 35000.00, "555,27" → 555.27
- currency: Detectar moneda siguiendo estas reglas ESTRICTAS:
  * Si aparece "USD" seguido de un número (ej: "USD 4,48" o "USD 555,27") → "USD" y usar ese monto
  * Si NO aparece "USD" → "ARS" y usar el último número de la línea
  * Monedas alternativas: "UYU" (pesos uruguayos) → convertir a "ARS" aproximado
- installment_number: Extraer cuota ACTUAL de "C.XX/YY"
  * "C.01/06" → "1/6" (primera cuota de 6)
  * "C.03/03" → "3/3" (tercera cuota de 3)
  * "C.06/06" → "6/6" (última cuota de 6)
  * Si NO tiene "C.XX/YY" → null
- category: Alimentación, Transporte, Salud, Entretenimiento, Servicios, Educación, Ropa, Otros
- payment_method: "Tarjeta de Crédito"

EJEMPLOS:
1. "10-Feb-26 CAFETERIA DEL PUERTO USD 4,48 690556 4,48"
   → {{"date":"2026-02-10","description":"CAFETERIA DEL PUERTO","amount":4.48,"currency":"USD","installment_number":null}}

2. "29-Ago-25 SIETE CUMBRES C.06/06 234817 18.166,66"
   → {{"date":"2025-08-29","description":"SIETE CUMBRES","amount":18166.66,"currency":"ARS","installment_number":"6/6"}}

3. "13-Feb-26 MERPAGO*LAPLANCHETTA C.01/06 324080 9.400,00"
   → {{"date":"2026-02-13","description":"MERPAGO*LAPLANCHETTA","amount":9400.00,"currency":"ARS","installment_number":"1/6"}}

4. "05-Feb-26 AUTOPISTAS DEL S 960004413131001 000001 1.538,02"
   → {{"date":"2026-02-05","description":"AUTOPISTAS DEL S","amount":1538.02,"currency":"ARS","installment_number":null}}

Devolvé SOLO el JSON array sin texto adicional:
[{{"date":"2026-02-10","description":"CAFETERIA DEL PUERTO","amount":4.48,"currency":"USD","category":"Alimentación","payment_method":"Tarjeta de Crédito","installment_number":null}}]
"""

    try:
        response = ollama.chat(
            model='mistral:7b',
            messages=[
                {'role': 'system', 'content': 'Devolvés SOLO JSON válido sin texto adicional.'},
                {'role': 'user', 'content': prompt}
            ],
            options={
                'num_predict': 5000,
                'temperature': 0.1
            }
        )

        ai_response = response['message']['content'].strip()
        ai_response = re.sub(r'```json\s*', '', ai_response)
        ai_response = re.sub(r'```\s*', '', ai_response)
        ai_response = ai_response.strip()

        expenses = json.loads(ai_response)

        # Validate and normalize expenses
        valid_expenses = []
        for expense in expenses:
            required_keys = ['date', 'description', 'amount', 'category', 'payment_method', 'currency']
            if all(key in expense for key in required_keys):
                # Convert amount to float, handling both formats
                amount_str = str(expense['amount'])
                # Remove currency symbols and whitespace
                amount_str = amount_str.replace('$', '').replace('ARS', '').replace('USD', '').strip()
                # Handle Argentine format (1.234,56) and US format (1234.56)
                if ',' in amount_str and '.' in amount_str:
                    # Argentine format: 1.234,56 -> remove dots, replace comma with dot
                    amount_str = amount_str.replace('.', '').replace(',', '.')
                elif ',' in amount_str:
                    # Only comma: could be decimal separator
                    amount_str = amount_str.replace(',', '.')

                try:
                    expense['amount'] = abs(float(amount_str))  # Use abs to handle negative amounts
                    expense['currency'] = expense['currency'].upper()
                    if 'installment_number' not in expense:
                        expense['installment_number'] = None
                    valid_expenses.append(expense)
                except ValueError as e:
                    print(f"Error converting amount '{expense['amount']}' for expense: {expense.get('description', 'unknown')}: {e}")
                    continue

        return valid_expenses

    except json.JSONDecodeError as e:
        print(f"❌ JSON Error: {e}")
        print(f"AI Response was: {ai_response[:500]}")
        return []
    except Exception as e:
        print(f"❌ Error processing with AI: {e}")
        import traceback
        traceback.print_exc()
        return []


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
            chunk_expenses = parse_transactions_with_ai(transactions_text)
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
