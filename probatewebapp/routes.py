from flask import abort, current_app as app, flash, redirect, render_template, url_for

from .forms import SearchForm
from .database import get_db, close_db
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
        close_db()
    return render_template('home.html', 
    title=title, 
    form=form, 
    last_update=last_update, 
    results=results)

# TODO: page to request re-issue of notification cancellation link

@app.route('/cancel_registration/<token>')
def cancel_registration(token):
    value = processing.verify_token(token, app.config['SECRET_KEY'])
    print(value)
    db = get_db()
    if isinstance(value, int):
        with db:
            db.execute('DELETE FROM notifications WHERE id = ?', (value,))
        flash('Your notification request has been cancelled.')
    elif isinstance(value, str):
        with db:
            db.execute('DELETE FROM notifications WHERE email = ?', (value,))
        flash('All your notification requests have been cancelled.')
    close_db()
    return render_template('cancel_registration.html')

@app.route('/test', methods=['GET', 'POST'])
def test():
    if not app.testing:
        abort(403)
    record = (1, 'themezj@hotmail.com', '', 'gobble', 0, '', '', 0, 2022, 2022, 'PRO', 1, 2022, 'In the estate of Quentin Nelly Gobble', 'Human Ladybird Hybrid')
    #database.Notify(*record)
    #return render_template('test.html', title='Test', last_update=last_update)
    return redirect(url_for('home'))
    
