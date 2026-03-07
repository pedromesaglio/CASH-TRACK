"""Test regex-based transaction parser"""
import sys
sys.path.insert(0, '/home/pedro/Desktop/cash track/cash-track')

from app.services.pdf_processor import parse_transactions_with_regex

# Test with sample transactions from Clara's PDF
sample_transactions = """05-Feb-26 AUTOPISTAS DEL S 960004413131001 000001 1.538,02
20-Feb-26 AUTOPISTAS DEL S 960004413131001 000001 2.796,36
29-Ago-25 SIETE CUMBRES C.06/06 234817 18.166,66
04-Oct-25 BEKA C.05/06 002444 4.166,66
10-Feb-26 CAFETERIA DEL PUERTO USD 4,48 690556 4,48
21-Feb-26 AIRBNB * HM2XNRZ2WH USD 555,27 334013 555,27
13-Feb-26 MERPAGO*LAPLANCHETTA C.01/06 324080 9.400,00
01-Feb-26 MERPAGO*MOSCU 331745 24.000,00"""

print("Testing regex-based parser...")
print("=" * 80)

expenses = parse_transactions_with_regex(sample_transactions)

print(f"\nParsed {len(expenses)} expenses:\n")

for i, exp in enumerate(expenses, 1):
    print(f"{i}. {exp['description']}")
    print(f"   Date: {exp['date']}")
    print(f"   Amount: {exp['currency']} {exp['amount']}")
    print(f"   Installment: {exp['installment_number']}")
    print(f"   Category: {exp['category']}")
    print()

print("=" * 80)
