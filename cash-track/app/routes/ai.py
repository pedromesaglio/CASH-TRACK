from flask import Blueprint, jsonify, request, session
from datetime import datetime
from database import get_db
from functools import wraps
import os
from openai import OpenAI

# Initialize OpenAI client (lazy initialization)
def get_openai_client():
    """Get or create OpenAI client"""
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        raise ValueError("OPENAI_API_KEY not set")
    return OpenAI(api_key=api_key)

# Create blueprint
ai_bp = Blueprint('ai', __name__, url_prefix='/ai')

def login_required(f):
    """Decorator to require login"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return jsonify({'error': 'Authentication required'}), 401
        return f(*args, **kwargs)
    return decorated_function

@ai_bp.route('/chat', methods=['POST'])
@login_required
def ai_chat():
    """Chat with AI financial assistant"""
    try:
        data = request.get_json()
        user_message = data.get('message', '')

        if not user_message:
            return jsonify({'error': 'No message provided'}), 400

        # Get user's financial data
        conn = get_db()
        cursor = conn.cursor()
        user_id = session['user_id']

        # Get total expenses and income
        cursor.execute('SELECT COALESCE(SUM(amount), 0) as total FROM expenses WHERE user_id = %s', (user_id,))
        total_expenses = cursor.fetchone()['total']

        cursor.execute('SELECT COALESCE(SUM(amount), 0) as total FROM income WHERE user_id = %s', (user_id,))
        total_income = cursor.fetchone()['total']

        # Get expenses by category
        cursor.execute('''
            SELECT category, SUM(amount) as total
            FROM expenses
            WHERE user_id = %s
            GROUP BY category
            ORDER BY total DESC
        ''', (user_id,))
        expenses_by_category = cursor.fetchall()

        # Get recent transactions
        cursor.execute('SELECT * FROM expenses WHERE user_id = %s ORDER BY date DESC LIMIT 5', (user_id,))%s
        recent_expenses = cursor.fetchall()

        conn.close()

        # Prepare context for AI
        context = f"""Eres un asesor financiero personal profesional pero cercano llamado "FinanceBot".
Tu objetivo es ayudar a personas a manejar mejor sus finanzas personales con consejos expertos pero accesibles.
Hablas en español de forma amigable y clara, combinando conocimiento profesional con un trato cercano.

Brindás consejos profesionales sobre:
- Optimización de gastos cotidianos (alimentación, transporte, entretenimiento)
- Planificación financiera personal
- Estrategias de ahorro realistas
- Gestión de presupuesto personal
- Balance entre calidad de vida y ahorro

Usá un lenguaje claro y profesional, pero evitá tecnicismos innecesarios. Tratá a la persona con respeto y cercanía.

Datos financieros personales:
- Total de ingresos: ${total_income:,.2f} ARS
- Total de gastos: ${total_expenses:,.2f} ARS
- Balance: ${total_income - total_expenses:,.2f} ARS

Tus gastos por categoría:
"""
        for cat in expenses_by_category:
            context += f"- {cat['category']}: ${cat['total']:,.2f} ARS\n"

        context += "\nTus últimos gastos:\n"
        for exp in recent_expenses:
            context += f"- {exp['date']}: {exp['description']} (${exp['amount']:,.2f}) - {exp['category']}\n"

        # Call OpenAI API
        client = get_openai_client()
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": context},
                {"role": "user", "content": user_message}
            ],
            temperature=0.7,
            max_tokens=1000
        )

        ai_response = response.choices[0].message.content

        return jsonify({
            'response': ai_response,
            'success': True
        })

    except Exception as e:
        return jsonify({
            'error': str(e),
            'success': False
        }), 500

@ai_bp.route('/analyze', methods=['GET'])
@login_required
def ai_analyze():
    """Get AI analysis of spending patterns"""
    try:
        conn = get_db()
        cursor = conn.cursor()
        user_id = session['user_id']

        # Get comprehensive financial data
        cursor.execute('SELECT COALESCE(SUM(amount), 0) as total FROM expenses WHERE user_id = %s', (user_id,))
        total_expenses = cursor.fetchone()['total']

        cursor.execute('SELECT COALESCE(SUM(amount), 0) as total FROM income WHERE user_id = %s', (user_id,))
        total_income = cursor.fetchone()['total']

        cursor.execute('''
            SELECT category, SUM(amount) as total
            FROM expenses
            WHERE user_id = %s
            GROUP BY category
            ORDER BY total DESC
        ''', (user_id,))
        expenses_by_category = cursor.fetchall()

        conn.close()

        # Prepare analysis prompt
        prompt = f"""Analizá estas finanzas personales y brindá un análisis profesional pero claro (3-4 puntos clave):

Ingresos: ${total_income:,.2f} ARS
Gastos: ${total_expenses:,.2f} ARS
Balance: ${total_income - total_expenses:,.2f} ARS

Distribución de gastos:
"""
        for cat in expenses_by_category:
            percentage = (cat['total'] / total_expenses * 100) if total_expenses > 0 else 0
            prompt += f"- {cat['category']}: ${cat['total']:,.2f} ARS ({percentage:.1f}%)\n"

        prompt += "\nProporcioná insights profesionales sobre:\n1. Evaluación de la situación financiera actual\n2. Categorías con mayor impacto en el presupuesto\n3. Recomendaciones concretas para optimizar gastos\n4. Oportunidades de mejora en los hábitos financieros\n\nUsá un tono profesional pero accesible y claro."

        response = ollama.chat(
            model='llama3.2',
            messages=[
                {'role': 'system', 'content': 'Eres un asesor financiero profesional especializado en finanzas personales. Brindás análisis expertos de forma clara y accesible. Usás lenguaje profesional pero cercano, evitando jerga compleja innecesaria.'},
                {'role': 'user', 'content': prompt}
            ]
        )

        return jsonify({
            'analysis': response['message']['content'],
            'success': True
        })

    except Exception as e:
        return jsonify({
            'error': str(e),
            'success': False
        }), 500

@ai_bp.route('/suggest-category', methods=['POST'])
@login_required
def ai_suggest_category():
    """Suggest category for expense using AI"""
    try:
        data = request.get_json()
        description = data.get('description', '')

        if not description:
            return jsonify({'error': 'No description provided'}), 400

        # Get user's past categorizations for learning
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT description, category
            FROM expenses
            WHERE user_id = %s
            ORDER BY created_at DESC
            LIMIT 20
        ''', (session['user_id'],))
        past_expenses = cursor.fetchall()
        conn.close()

        # Prepare context with user's history
        context = "Eres un asistente especializado en categorización de gastos personales. Basándote en el historial de categorizaciones del usuario, sugiere la categoría más apropiada de forma precisa.\n\n"
        context += "Categorías disponibles: Alimentación, Transporte, Salud, Entretenimiento, Servicios, Educación, Ropa, Otros\n\n"
        context += "Historial de categorizaciones:\n"

        for exp in past_expenses:
            context += f"- '{exp['description']}' → {exp['category']}\n"

        prompt = f"Para el gasto: '{description}', ¿qué categoría corresponde%s Respondé SOLO con el nombre de la categoría, sin explicaciones adicionales."

        response = ollama.chat(
            model='llama3.2',
            messages=[
                {'role': 'system', 'content': context},
                {'role': 'user', 'content': prompt}
            ]
        )

        suggested_category = response['message']['content'].strip()

        return jsonify({
            'category': suggested_category,
            'success': True
        })

    except Exception as e:
        return jsonify({
            'error': str(e),
            'success': False
        }), 500

@ai_bp.route('/predict-expenses', methods=['GET'])
@login_required
def ai_predict_expenses():
    """Predict future expenses and provide alerts"""
    try:
        conn = get_db()
        cursor = conn.cursor()
        user_id = session['user_id']

        # Get monthly expenses for the last 3 months
        cursor.execute('''
            SELECT TO_CHAR(date, 'YYYY-MM') as month, SUM(amount) as total
            FROM expenses
            WHERE user_id = %s
            GROUP BY month
            ORDER BY month DESC
            LIMIT 3
        ''', (user_id,))
        monthly_data = cursor.fetchall()

        # Get current month expenses
        current_month = datetime.now().strftime('%Y-%m')
        cursor.execute('''
            SELECT COALESCE(SUM(amount), 0) as total
            FROM expenses
            WHERE user_id = %s AND TO_CHAR(date, 'YYYY-MM') = %s
        ''', (user_id, current_month))
        current_month_total = cursor.fetchone()['total']

        # Get expenses by category this month
        cursor.execute('''
            SELECT category, SUM(amount) as total
            FROM expenses
            WHERE user_id = %s AND TO_CHAR(date, 'YYYY-MM') = %s
            GROUP BY category
            ORDER BY total DESC
        ''', (user_id, current_month))
        current_categories = cursor.fetchall()

        conn.close()

        # Prepare prediction prompt
        prompt = f"""Analizá el patrón de gastos mensuales y brindá una predicción profesional para el mes actual:

Gastos de los últimos 3 meses:
"""
        for month_data in monthly_data:
            prompt += f"- {month_data['month']}: ${month_data['total']:,.2f} ARS\n"

        prompt += f"\nGastos acumulados del mes actual ({current_month}): ${current_month_total:,.2f} ARS\n\n"
        prompt += "Distribución por categoría este mes:\n"
        for cat in current_categories:
            prompt += f"- {cat['category']}: ${cat['total']:,.2f} ARS\n"

        prompt += "\n\nProporcioná:\n1. Proyección de gasto total para fin de mes\n2. Análisis de variaciones o gastos atípicos\n3. Recomendaciones para el resto del mes\n4. Comparativa con meses anteriores\n\nUsá un lenguaje profesional pero accesible."

        response = ollama.chat(
            model='llama3.2',
            messages=[
                {'role': 'system', 'content': 'Eres un analista financiero especializado en predicción de gastos personales. Brindás proyecciones y recomendaciones profesionales de forma clara y útil. Usás un tono experto pero accesible.'},
                {'role': 'user', 'content': prompt}
            ]
        )

        return jsonify({
            'prediction': response['message']['content'],
            'current_total': current_month_total,
            'success': True
        })

    except Exception as e:
        return jsonify({
            'error': str(e),
            'success': False
        }), 500

@ai_bp.route('/monthly-summary', methods=['GET'])
@login_required
def ai_monthly_summary():
    """Generate AI-powered monthly summary"""
    try:
        year = request.args.get('year', datetime.now().year, type=int)
        month = request.args.get('month', datetime.now().month, type=int)

        conn = get_db()
        cursor = conn.cursor()
        user_id = session['user_id']

        # Get month data
        cursor.execute('''
            SELECT COALESCE(SUM(amount), 0) as total
            FROM expenses
            WHERE user_id = %s AND EXTRACT(YEAR FROM date)::text = %s AND TO_CHAR(date, 'MM') = %s
        ''', (user_id, str(year), f'{month:02d}'))
        total_expenses = cursor.fetchone()['total']

        cursor.execute('''
            SELECT COALESCE(SUM(amount), 0) as total
            FROM income
            WHERE user_id = %s AND EXTRACT(YEAR FROM date)::text = %s AND TO_CHAR(date, 'MM') = %s
        ''', (user_id, str(year), f'{month:02d}'))
        total_income = cursor.fetchone()['total']

        cursor.execute('''
            SELECT category, SUM(amount) as total, COUNT(*) as count
            FROM expenses
            WHERE user_id = %s AND EXTRACT(YEAR FROM date)::text = %s AND TO_CHAR(date, 'MM') = %s
            GROUP BY category
            ORDER BY total DESC
        ''', (user_id, str(year), f'{month:02d}'))
        expenses_by_category = cursor.fetchall()

        # Get top expenses
        cursor.execute('''
            SELECT description, amount, category, date
            FROM expenses
            WHERE user_id = %s AND EXTRACT(YEAR FROM date)::text = %s AND TO_CHAR(date, 'MM') = %s
            ORDER BY amount DESC
            LIMIT 5
        ''', (user_id, str(year), f'{month:02d}'))
        top_expenses = cursor.fetchall()

        # Get previous month for comparison
        prev_month = month - 1 if month > 1 else 12
        prev_year = year if month > 1 else year - 1

        cursor.execute('''
            SELECT COALESCE(SUM(amount), 0) as total
            FROM expenses
            WHERE user_id = %s AND EXTRACT(YEAR FROM date)::text = %s AND TO_CHAR(date, 'MM') = %s
        ''', (user_id, str(prev_year), f'{prev_month:02d}'))
        prev_month_expenses = cursor.fetchone()['total']

        conn.close()

        # Prepare summary prompt
        month_names = ['Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio',
                       'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre']

        prompt = f"""Generá un resumen financiero profesional pero motivador para {month_names[month-1]} {year}:

RESUMEN FINANCIERO DEL MES:
- Ingresos: ${total_income:,.2f} ARS
- Gastos: ${total_expenses:,.2f} ARS
- Balance: ${total_income - total_expenses:,.2f} ARS
- Gastos mes anterior: ${prev_month_expenses:,.2f} ARS
- Variación: ${total_expenses - prev_month_expenses:,.2f} ARS ({((total_expenses - prev_month_expenses) / prev_month_expenses * 100) if prev_month_expenses > 0 else 0:.1f}%)

DISTRIBUCIÓN DE GASTOS:
"""
        for cat in expenses_by_category:
            percentage = (cat['total'] / total_expenses * 100) if total_expenses > 0 else 0
            prompt += f"- {cat['category']}: ${cat['total']:,.2f} ARS ({percentage:.1f}%) - {cat['count']} transacciones\n"

        prompt += "\nPRINCIPALES GASTOS DEL MES:\n"
        for exp in top_expenses:
            prompt += f"- {exp['date']}: {exp['description']} - ${exp['amount']:,.2f} ({exp['category']})\n"

        prompt += "\n\nGenerá un resumen que incluya:\n1. Título profesional y motivador\n2. Análisis de la situación financiera del mes\n3. Análisis de categorías principales\n4. Comparativa con mes anterior\n5. Aspectos positivos y áreas de mejora\n6. Recomendaciones estratégicas para el próximo mes\n\nUsá un tono profesional pero cercano y motivador."

        response = ollama.chat(
            model='llama3.2',
            messages=[
                {'role': 'system', 'content': 'Eres un asesor financiero profesional que genera resúmenes mensuales detallados y motivadores. Combinás análisis experto con un tono cercano y alentador. Usás lenguaje profesional pero accesible.'},
                {'role': 'user', 'content': prompt}
            ]
        )

        return jsonify({
            'summary': response['message']['content'],
            'data': {
                'total_income': total_income,
                'total_expenses': total_expenses,
                'balance': total_income - total_expenses,
                'month': month_names[month-1],
                'year': year
            },
            'success': True
        })

    except Exception as e:
        return jsonify({
            'error': str(e),
            'success': False
        }), 500
