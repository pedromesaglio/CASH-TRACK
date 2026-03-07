"""
Test script to debug PDF processing for Clara's credit card statement
"""
import sys
sys.path.insert(0, '/home/pedro/Desktop/cash track/cash-track')

from app.services.pdf_processor import extract_text_from_pdf, extract_closing_date_and_cardholder, extract_consumption_lines

pdf_path = '/home/pedro/Downloads/resumen tarjeta clari marzo 26.pdf'

print("=" * 80)
print("TESTING PDF PROCESSING FOR CLARA")
print("=" * 80)

# Step 1: Extract text
print("\n1. Extracting text from PDF...")
text = extract_text_from_pdf(pdf_path)
print(f"   ✓ Extracted {len(text)} characters")

# Step 2: Extract cardholder name and closing date
print("\n2. Extracting cardholder name and closing date...")
closing_date, cardholder_name = extract_closing_date_and_cardholder(text)
print(f"   Cardholder: {cardholder_name}")
print(f"   Closing date: {closing_date}")

# Step 3: Find consumption lines
print("\n3. Extracting consumption lines...")
consumption_lines = extract_consumption_lines(text, cardholder_name)
print(f"   Found {len(consumption_lines)} transaction lines")

if len(consumption_lines) == 0:
    print("\n❌ ERROR: No consumption lines found!")
    print("\nLet's check what sections contain 'Consumos':")

    for i, line in enumerate(text.split('\n')):
        if 'Consumos' in line or 'CONSUMOS' in line:
            print(f"   Line {i}: {line.strip()}")

    print("\nLet's check if cardholder name appears in text:")
    if cardholder_name:
        name_words = cardholder_name.split()
        for word in name_words:
            count = text.lower().count(word.lower())
            print(f"   '{word}' appears {count} times in text")
else:
    print("\n✓ SUCCESS! Sample transactions:")
    for i, line in enumerate(consumption_lines[:5]):
        print(f"   {i+1}. {line[:100]}")

    if len(consumption_lines) > 5:
        print(f"   ... and {len(consumption_lines) - 5} more")

print("\n" + "=" * 80)
