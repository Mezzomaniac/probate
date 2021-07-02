import datetime

from flask_wtf import FlaskForm
from wtforms import BooleanField, StringField, SubmitField
from wtforms.fields.html5 import EmailField, IntegerField
from wtforms.validators import Optional, Email

class SearchForm(FlaskForm):
    
    dec_first = StringField(
        "What are the deceased person's firstnames?", 
        render_kw={"placeholder": "Deceased's firstnames"})
    dec_sur = StringField(
        "What is the deceased person's surname?", 
        render_kw={"placeholder": "Deceased's surname"})
    dec_strict = BooleanField('Search only for deceased people with this exact combination of firstnames and surname (not case sensitive)')
    party_first = StringField(
        "What are the applicant's/party's firstnames?", 
        render_kw={"placeholder": "Applicant's/party's firstnames"})
    party_sur = StringField(
        "What is the applicant's/party's surname (or corporation's name)?", 
        render_kw={"placeholder": "Applicant's/party's surname"})
    party_strict = BooleanField('Search only for applicants/parties with this exact combination of firstnames and surname (or corporation name) (not case sensitive)')
    start_year = IntegerField(
        "Start year", 
        validators=[Optional()], 
        render_kw={"placeholder": "E.g. 2020"}, 
        default=(datetime.date.today() - datetime.timedelta(weeks=26)).year)
    end_year = IntegerField(
        "End year", 
        validators=[Optional()], 
        render_kw={"placeholder": "E.g.  2021"}, 
        default=datetime.date.today().year)
    email = EmailField(
        'Enter your email address to be notified of any new records matching this search', 
        validators=[Optional(), Email()])
    submit = SubmitField('Search')

class RequestNotificationListForm(FlaskForm):
    email = EmailField(
        'Enter your email address to be sent a list of your active notification requests, with cancellation links.', 
        validators=[Email()])
    submit = SubmitField('Go')

# TODO: enable email notifications of a new grant
