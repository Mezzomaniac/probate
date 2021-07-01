from collections import namedtuple

fieldnames = 'type number year title deceased_name flags'
Matter = namedtuple('Matter', fieldnames)

fieldnames = 'party_name type number year'
Party = namedtuple('Party', fieldnames)

NotificationField = namedtuple('NotificationField', 'description value')
        
class Notification:
    
    def __init__(self, 
        id, 
        email, 
        dec_first, 
        dec_sur, 
        dec_strict, 
        party_first, 
        party_sur, 
        party_strict, 
        start_year, 
        end_year, 
        matter_type=None, 
        number=None, 
        year=None, 
        title=None, 
        party_name=None
        ):
        
        self.id = id
        self.email = email
        self.dec_first = NotificationField("Deceased's firstnames", dec_first or '[None]')
        self.dec_sur = NotificationField("Deceased's surname", dec_sur or '[None]')
        self.dec_strict = NotificationField("Deceased's names strict", bool(dec_strict))
        self.party_first = NotificationField("Applicant's/party's firstnames", party_first or '[None]')
        self.party_sur = NotificationField("Applicant's/party's surname", party_sur or '[None]')
        self.party_strict = NotificationField("Applicant's/party's names strict", bool(party_strict))
        self.start_year = NotificationField("Start year", start_year)
        self.end_year = NotificationField("End year", end_year)
        self.file_no = NotificationField("File number", f'{matter_type} {number}/{year}')
        self.title = NotificationField("Title", title)
        self.party_name = NotificationField("Party", party_name.title()) if party_name else party_name
        self.parameters = [self.dec_first, self.dec_sur, self.dec_strict, self.party_first, self.party_sur, self.party_strict, self.start_year, self.end_year]
        self.result = [self.file_no, self.title, self.party_name]
    
    def __repr__(self):
        attrs = "id, email, dec_first, dec_sur, dec_strict, party_first, party_sur, party_strict, start_year, end_year, file_no, title, party_name".split(', ')
        return f"Notification({', '.join(str(getattr(self, attr)) for attr in attrs)}"
    
    def __str__(self):
        return f'Notification({self.id}, {self.email}, {self.result})'
