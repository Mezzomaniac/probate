import datetime
from flask_wtf import FlaskForm
from wtforms import BooleanField, StringField, SubmitField
from wtforms.fields.html5 import EmailField, IntegerField
from wtforms.validators import Optional, Email

class SearchForm(FlaskForm):
    
    deceased_firstnames = StringField(
        "What are the deceased person's first names?", 
        render_kw={"placeholder": "Deceased's first names"})
    deceased_surname = StringField(
        "What is the deceased person's surname?", 
        render_kw={"placeholder": "Deceased's surname"})
    deceased_name_strict = BooleanField('Search only for deceased people with this exact combination of first/middle names and surname (not case sensitive)')
    party_firstnames = StringField(
        "What are the applicant's/party's first names?", 
        render_kw={"placeholder": "Applicant's/party's first names"})
    party_surname = StringField(
        "What is the applicant's/party's surname (or corporation's name)?", 
        render_kw={"placeholder": "Applicant's/party's surname"})
    party_name_strict = BooleanField('Search only for applicants/parties with this exact combination of first/middle names and surname (or corporation name) (not case sensitive)')
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

# TODO: enable email notifications of a new matter/grant - careful though if still using check_same_thread=False for the db connection
