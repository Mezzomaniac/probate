from flask_wtf import FlaskForm
from wtforms import FieldList, FormField, StringField, SubmitField
from wtforms.fields.html5 import IntegerField
from wtforms.validators import InputRequired, ValidationError

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
        render_kw={"placeholder": "E.g. 2020", "required": False})
    end_year = IntegerField(
        "End year", 
        render_kw={"placeholder": "E.g.  2021", "required": False})
    submit = SubmitField('Search')
