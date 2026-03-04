"""
Category management service
"""
from database import get_db
from app.utils.constants import CATEGORIES, DEFAULT_CATEGORY_ICONS


def get_all_categories(user_id):
    """Get all categories (default + custom)"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT name, icon FROM custom_categories WHERE user_id = %s ORDER BY name', (user_id,))
    custom_cats = cursor.fetchall()
    conn.close()

    # Combine default categories with custom ones
    all_categories = CATEGORIES.copy()
    for cat in custom_cats:
        if cat['name'] not in all_categories:
            all_categories.append(cat['name'])

    return all_categories


def get_category_icons(user_id):
    """Get icons for all categories"""
    icons = DEFAULT_CATEGORY_ICONS.copy()

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT name, icon FROM custom_categories WHERE user_id = %s', (user_id,))
    custom_cats = cursor.fetchall()
    conn.close()

    # Add custom category icons
    for cat in custom_cats:
        icons[cat['name']] = cat['icon']

    return icons


def get_custom_categories(user_id):
    """Get user's custom categories"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT id, name, icon FROM custom_categories WHERE user_id = %s ORDER BY name', (user_id,))
    custom_categories = cursor.fetchall()
    conn.close()
    return custom_categories
