from flask import abort, flash, redirect, render_template, url_for

from . import app
try:
    from . import db
except ImportError:
    from ._tests import db
from .forms import SearchForm
from . import processing


@app.route('/', methods=['GET', 'POST'])
def home():
    form = SearchForm()
    try:
        last_update = db.execute("SELECT time FROM events WHERE event = 'last_update'").fetchone()[0]
    except TypeError:
        last_update = None
    results = None
    email = None
    if form.validate_on_submit():
        search_parameters = processing.standardize_search_parameters(**form.data)
        results = processing.search(db, search_parameters)
        email = form.data['email'].strip()
        if email:
            flash(f'A notification email will be sent to {email} if any matters/parties match this search.')
            processing.register(db, search_parameters, email)
    return render_template('home.html', 
    title='Home', 
    form=form, 
    last_update=last_update, 
    results=results, 
    email=email)

# TODO: page to request re-issue of notification cancellation link

@app.route('/cancel_notification/<token>')
def cancel_notification(token):
    token = processing.verify_token(token)
    print(token)
    if isinstance(token, int):
        with db:
            db.execute('DELETE FROM notifications WHERE id = ?', (token,))
        flash('Your notification request has been cancelled.')
    elif isinstance(token, str):
        with db:
            db.execute('DELETE FROM notifications WHERE email = ?', (token,))
        flash('All your notification requests have been cancelled.')
    return redirect(url_for('home'))

@app.route('/test', methods=['GET', 'POST'])
def test():
    if not app.config['TESTING']:
        abort(403)
    try:
        last_update = db.execute("SELECT time FROM events WHERE event = 'last_update'").fetchone()[0]
    except TypeError:
        last_update = None
    #return render_template('test.html', title='Test', last_update=last_update)
    return redirect(url_for('home'))
    
