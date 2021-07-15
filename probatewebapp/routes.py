from flask import abort, current_app as app, flash, g, redirect, render_template, url_for

from .forms import SearchForm, RequestNotificationListForm
from .database import get_db#, close_db
from .models import Notification
from . import processing


@app.route('/', methods=['GET', 'POST'])
def home():
    title = 'Home'
    form = SearchForm()
    last_update = app.config['LAST_UPDATE']
    results = None
    if form.validate_on_submit():
        title = 'Search results'
        search_parameters = processing.standardize_search_parameters(**form.data)
        db = get_db()
        results = processing.search(db, search_parameters)
        email = form.data['email'].strip()
        if email:
            flash(f'A notification email will be sent to {email} if any matters/parties match this search.')
            processing.register(db, search_parameters, email)
        #close_db()
    return render_template('home.html', 
    title=title, 
    form=form, 
    last_update=last_update, 
    results=results)

@app.route('/manage_registration', methods=['GET', 'POST'])
def manage_registration():
    form = RequestNotificationListForm()
    if form.validate_on_submit():
        email = form.data['email'].strip()
        db = get_db()
        command = "SELECT id, email, dec_first, dec_sur, dec_strict, party_first, party_sur, party_strict, start_year, end_year FROM party_notification_requests WHERE email = ?"
        party_notification_requests = [Notification(*party_notification_request) for party_notification_request in db.execute(command, (email,))]
        secret_key = app.config['SECRET_KEY']
        id_tokens = {party_notification_request.id: processing.create_token(party_notification_request.id, secret_key) for party_notification_request in party_notification_requests}
        email_token = processing.create_token(email, secret_key)
        processing.send_message(email, 
            'Notifications List', 
            'list', 
            notification_requests=party_notification_requests, 
            id_tokens=id_tokens, 
            email_token=email_token)
        #close_db()
        flash('The email has been sent.')
    return render_template('manage_registration.html', title='Manage registration', form=form)

@app.route('/cancel_registration/<token>')
def cancel_registration(token):
    value = processing.verify_token(token, app.config['SECRET_KEY'])
    print(value)
    db = get_db()
    if isinstance(value, int):
        with db:
            db.execute('DELETE FROM party_notification_requests WHERE id = ?', (value,))
        flash('Your notification request has been cancelled.')
    elif isinstance(value, str):
        with db:
            db.execute('DELETE FROM party_notification_requests WHERE email = ?', (value,))
        flash('All your notification requests have been cancelled.')
    #close_db()
    return render_template('cancel_registration.html', title='Cancel registration')

@app.errorhandler(404)
def not_found_error(error):
    return render_template('404.html'), 404
    
@app.errorhandler(500)
def internal_error(error):
    print(error)
    if 'db' in g:
        g.db.rollback()
        close_db()
    return render_template('500.html'), 500

@app.route('/test', methods=['GET', 'POST'])
def test():
    if not app.testing:
        abort(403)
    #record = (1, 'themezj@hotmail.com', '', 'gobble', 0, '', '', 0, 2022, 2022, 'PRO', 1, 2022, 'In the estate of Quentin Nelly Gobble', 'Human Ladybird Hybrid')
    #database.Notify(*record)
    return render_template('t.html', title='Test', last_update=last_update)
    return redirect(url_for('home'))
