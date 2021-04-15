from flask_wtf import FlaskForm
from wtforms import FieldList, FormField, StringField, SubmitField
from wtforms.fields.html5 import IntegerField
from wtforms.validators import InputRequired, ValidationError

class SearchForm(FlaskForm):

    deceased_surname = StringField(
        "What is the deceased person's surname?", 
        render_kw={"placeholder": "Deceased's surname"})
    start_year = IntegerField(
        "Start year", 
        render_kw={"placeholder": "Start year"})
    end_year = IntegerField(
        "End year", 
        render_kw={"placeholder": "End year"})
    submit = SubmitField('Search')