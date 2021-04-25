import datetime
from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField
from wtforms.fields.html5 import IntegerField
from wtforms.validators import Optional

class SearchForm(FlaskForm):
    
    deceased_firstnames = StringField(
        "What are the deceased person's first names?", 
        render_kw={"placeholder": "Deceased's first names"})
    deceased_surname = StringField(
        "What is the deceased person's surname?", 
        render_kw={"placeholder": "Deceased's surname"})
    party_firstnames = StringField(
        "What are the applicant's/party's first names?", 
        render_kw={"placeholder": "Applicant's/party's first names"})
    party_surname = StringField(
        "What is the applicant's/party's surname (or corporation's name)?", 
        render_kw={"placeholder": "Applicant's/party's surname"})
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
    submit = SubmitField('Search')
