"""
Admin Blueprint - User management
"""
from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from database import get_db
from app.utils.decorators import admin_required

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')


@admin_bp.route('/users')
@admin_required
def admin_users():
    """Admin panel - manage users"""
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute('''
        SELECT id, username, role, created_at,
               (SELECT COUNT(*) FROM expenses WHERE user_id = users.id) as expense_count,
               (SELECT COUNT(*) FROM income WHERE user_id = users.id) as income_count
        FROM users
        ORDER BY created_at DESC
    ''')
    users = cursor.fetchall()
    conn.close()

    return render_template('admin_users.html', users=users)


@admin_bp.route('/users/change_role/<int:user_id>', methods=['POST'])
@admin_required
def admin_change_role(user_id):
    """Change user role"""
    new_role = request.form.get('role')

    if new_role not in ['user', 'admin']:
        flash('Rol inválido', 'danger')
        return redirect(url_for('admin.admin_users'))

    conn = get_db()
    cursor = conn.cursor()

    # Prevent changing your own role
    if user_id == session['user_id']:
        flash('No puedes cambiar tu propio rol', 'warning')
        conn.close()
        return redirect(url_for('admin.admin_users'))

    cursor.execute('UPDATE users SET role = %s WHERE id = %s', (new_role, user_id))
    conn.commit()
    conn.close()

    flash(f'Rol actualizado exitosamente', 'success')
    return redirect(url_for('admin.admin_users'))


@admin_bp.route('/users/delete/<int:user_id>', methods=['POST'])
@admin_required
def admin_delete_user(user_id):
    """Delete user and all their data"""
    # Prevent deleting yourself
    if user_id == session['user_id']:
        flash('No puedes eliminar tu propia cuenta', 'warning')
        return redirect(url_for('admin.admin_users'))

    conn = get_db()
    cursor = conn.cursor()

    # Delete user's data (cascade will happen with foreign keys)
    cursor.execute('DELETE FROM expenses WHERE user_id = %s', (user_id,))
    cursor.execute('DELETE FROM income WHERE user_id = %s', (user_id,))
    cursor.execute('DELETE FROM investments WHERE user_id = %s', (user_id,))
    cursor.execute('DELETE FROM custom_categories WHERE user_id = %s', (user_id,))
    cursor.execute('DELETE FROM users WHERE id = %s', (user_id,))

    conn.commit()
    conn.close()

    flash('Usuario eliminado exitosamente', 'success')
    return redirect(url_for('admin.admin_users'))
