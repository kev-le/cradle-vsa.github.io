from config import db, ma
from jsonschema import validate
from jsonschema.exceptions import ValidationError
from jsonschema.exceptions import SchemaError
from marshmallow_enum import EnumField
from marshmallow_sqlalchemy import fields
import enum

# To add a table to db, make a new class
# create a migration: flask db migrate
# apply the migration: flask db upgrade

#####################
### ENUMS CLASSES ###
#####################
class RoleEnum(enum.Enum):
    VHT = 'VHT'
    HCW = 'HCW'
    ADMIN = 'ADMIN'
    CHO = 'CHO'

class SexEnum(enum.Enum):
    MALE = 'MALE'
    FEMALE = 'FEMALE'
    OTHER = 'OTHER'

class TrafficLightEnum(enum.Enum):
    NONE = 'NONE'
    GREEN = 'GREEN'
    YELLOW_UP = 'YELLOW_UP'
    YELLOW_DOWN = 'YELLOW_DOWN'
    RED_UP = 'RED_UP'
    RED_DOWN = 'RED_DOWN'


######################
### HELPER CLASSES ###
######################
userRole = db.Table('userrole',
    db.Column('id', db.Integer, primary_key=True),
    
    # FOREIGN KEYS
    db.Column('userId', db.Integer, db.ForeignKey('user.id')),
    db.Column('roleId', db.Integer, db.ForeignKey('role.id'))
)

supervises = db.Table('supervises',
    db.Column('choId', db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'), index=True),
    db.Column('vhtId', db.Integer, db.ForeignKey('user.id', ondelete='CASCADE')),
    db.UniqueConstraint('choId', 'vhtId', name='unique_supervise')
)

#####################
### MODEL CLASSES ###
#####################
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    firstName = db.Column(db.String(25))
    username = db.Column(db.String(64), index=True, unique=True)
    email = db.Column(db.String(120), index=True, unique=True)
    password = db.Column(db.String(128))

    # FOREIGN KEYS
    healthFacilityName = db.Column(db.String(50), db.ForeignKey('healthfacility.healthFacilityName'), nullable=True)

    # RELATIONSHIPS
    healthFacility = db.relationship('HealthFacility', backref=db.backref('users', lazy=True))
    roleIds = db.relationship('Role', secondary=userRole, backref=db.backref('users', lazy=True))
    referrals = db.relationship('Referral', backref=db.backref('users', lazy=True))
    vhtList = db.relationship('User',
                              secondary = supervises,
                              primaryjoin = id==supervises.c.choId,
                              secondaryjoin = id==supervises.c.vhtId)

    def __repr__(self):
        return '<User {}>'.format(self.username)

class Role(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.Enum(RoleEnum), nullable=False)

class Referral(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    dateReferred = db.Column(db.String(100), nullable=False) 
    comment = db.Column(db.Text)
    actionTaken = db.Column(db.Text)

    # FOREIGN KEYS
    userId = db.Column(db.Integer, db.ForeignKey('user.id'))
    patientId = db.Column(db.String(50), db.ForeignKey('patient.patientId'))

    referralHealthFacilityName = db.Column(db.String(50), db.ForeignKey('healthfacility.healthFacilityName'))
    readingId = db.Column(db.String(50), db.ForeignKey('reading.readingId'))
    followUpId = db.Column(db.Integer, db.ForeignKey('followup.id'))

    # RELATIONSHIPS
    healthFacility = db.relationship('HealthFacility', backref=db.backref('referrals', lazy=True))
    reading = db.relationship('Reading', backref=db.backref('referral', lazy=True, uselist=False))
    followUp = db.relationship('FollowUp', backref=db.backref('referral', lazy=True, uselist=False, cascade="save-update"))
    

class HealthFacility(db.Model):
    __tablename__ = 'healthfacility'
    healthFacilityName = db.Column(db.String(50), primary_key=True)


class Patient(db.Model):
    patientId = db.Column(db.String(50), primary_key=True)
    patientName = db.Column(db.String(50))
    patientAge = db.Column(db.Integer, nullable=False)
    patientSex = db.Column(db.Enum(SexEnum), nullable=False)
    isPregnant = db.Column(db.Boolean)
    gestationalAgeUnit = db.Column(db.String(50))
    gestationalAgeValue = db.Column(db.String(20))
    medicalHistory = db.Column(db.Text)
    drugHistory = db.Column(db.Text)
    zone = db.Column(db.String(20))
    tank = db.Column(db.String(20))
    block = db.Column(db.String(20))

    villageNumber = db.Column(db.String(50))
    # FOREIGN KEYS
    # villageNumber = db.Column(db.String(50), db.ForeignKey('village.villageNumber'))

    # RELATIONSHIPS
    # village = db.relationship('Village', backref=db.backref('patients', lazy=True))

    def as_dict(self):
        return {c.name: str(getattr(self, c.name)) for c in self.__table__.columns}


class Reading(db.Model):
    readingId = db.Column(db.String(50), primary_key=True)
    bpSystolic = db.Column(db.Integer)
    bpDiastolic = db.Column(db.Integer)
    heartRateBPM = db.Column(db.Integer)
    symptoms = db.Column(db.Text)
    trafficLightStatus = db.Column(db.Enum(TrafficLightEnum))

    # date ex: 2019-09-25T19:00:16.683-07:00[America/Vancouver]
    dateLastSaved = db.Column(db.String(100)) 
    dateTimeTaken = db.Column(db.String(100))
    dateUploadedToServer = db.Column(db.String(100))
    dateRecheckVitalsNeeded = db.Column(db.String(100))

    gpsLocationOfReading = db.Column(db.String(50))
    retestOfPreviousReadingIds = db.Column(db.String(100))
    isFlaggedForFollowup = db.Column(db.Boolean)
    appVersion = db.Column(db.String(50))
    deviceInfo = db.Column(db.String(50))
    totalOcrSeconds = db.Column(db.Float)
    manuallyChangeOcrResults = db.Column(db.Integer)
    temporaryFlags = db.Column(db.Integer)
    userHasSelectedNoSymptoms = db.Column(db.Boolean)

    # FOREIGN KEYS
    userId = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='SET NULL'), nullable=True)

    # @hybrid_property
    def getTrafficLight(self):
        RED_SYSTOLIC = 160
        RED_DIASTOLIC = 110
        YELLOW_SYSTOLIC = 140
        YELLOW_DIASTOLIC = 90
        SHOCK_HIGH = 1.7
        SHOCK_MEDIUM = 0.9

        if self.bpSystolic == None or self.bpDiastolic == None or self.heartRateBPM == None:
            return TrafficLightEnum.NONE.name
        
        shockIndex = self.heartRateBPM / self.bpSystolic

        isBpVeryHigh = (self.bpSystolic >= RED_SYSTOLIC) or (self.bpDiastolic >= RED_DIASTOLIC)
        isBpHigh = (self.bpSystolic >= YELLOW_SYSTOLIC) or (self.bpDiastolic >= YELLOW_DIASTOLIC)
        isSevereShock = (shockIndex >= SHOCK_HIGH)
        isShock = (shockIndex >= SHOCK_MEDIUM)

        if isSevereShock:
            trafficLight = TrafficLightEnum.RED_DOWN.name
        elif isBpVeryHigh:
            trafficLight = TrafficLightEnum.RED_UP.name
        elif isShock:
            trafficLight = TrafficLightEnum.YELLOW_DOWN.name
        elif isBpHigh:
            trafficLight = TrafficLightEnum.YELLOW_UP.name
        else:
            trafficLight = TrafficLightEnum.GREEN.name

        return trafficLight

    def __init__(self, userId, patientId, readingId, bpSystolic,
                 bpDiastolic,heartRateBPM,symptoms,
                 trafficLightStatus=None,dateLastSaved=None,
                 dateTimeTaken=None,dateUploadedToServer=None,
                 dateRecheckVitalsNeeded=None, gpsLocationOfReading=None,
                 retestOfPreviousReadingIds=None, isFlaggedForFollowup=None, appVersion=None,
                 deviceInfo=None, totalOcrSeconds=None, manuallyChangeOcrResults=None,
                 temporaryFlags=None, userHasSelectedNoSymptoms=None):
        self.userId = userId     
        self.patientId = patientId
        self.readingId = readingId
        self.bpSystolic = bpSystolic
        self.bpDiastolic = bpDiastolic
        self.heartRateBPM = heartRateBPM
        self.symptoms = symptoms
        self.trafficLightStatus = self.getTrafficLight()
        self.dateTimeTaken = dateTimeTaken
        self.dateLastSaved = dateLastSaved
        self.dateUploadedToServer = dateUploadedToServer
        self.dateRecheckVitalsNeeded = dateRecheckVitalsNeeded
        self.gpsLocationOfReading = gpsLocationOfReading
        self.retestOfPreviousReadingIds = retestOfPreviousReadingIds
        self.isFlaggedForFollowup = isFlaggedForFollowup
        self.appVersion = appVersion
        self.deviceInfo = deviceInfo
        self.totalOcrSeconds = totalOcrSeconds
        self.manuallyChangeOcrResults = manuallyChangeOcrResults
        self.temporaryFlags = temporaryFlags
        self.userHasSelectedNoSymptoms = userHasSelectedNoSymptoms


    # FOREIGN KEYS
    patientId = db.Column(db.String(50), db.ForeignKey('patient.patientId'), nullable=False)

    # RELATIONSHIPS
    patient = db.relationship('Patient', backref=db.backref('readings', lazy=True))


class FollowUp(db.Model):
    __tablename__ = 'followup'
    id = db.Column(db.Integer, primary_key=True)
    followUpAction = db.Column(db.Text)
    diagnosis = db.Column(db.Text)
    treatment = db.Column(db.Text)
    dateAssessed = db.Column(db.String(100), nullable=False)
    healthcareWorkerId = db.Column(db.ForeignKey(User.id), nullable=False)

    # reading = db.relationship('Reading', backref=db.backref('referral', lazy=True, uselist=False))
    healthcareWorker = db.relationship(User, backref=db.backref('followups', lazy=True))


class Village(db.Model):
    villageNumber = db.Column(db.String(50), primary_key=True)
    zoneNumber    = db.Column(db.String(50))


######################
###    SCHEMAS     ###
######################

class UserSchema(ma.ModelSchema):
    class Meta:
        include_fk = True
        model = User

class PatientSchema(ma.ModelSchema):
    patientSex = EnumField(SexEnum, by_value=True)
    class Meta:
        include_fk = True
        model = Patient

class ReadingSchema(ma.ModelSchema):
    trafficLightStatus = EnumField(TrafficLightEnum, by_value=True)
    class Meta:
        include_fk = True
        model = Reading
    
class RoleSchema(ma.ModelSchema):
    class Meta:
        include_fk = True
        model = Role

class HealthFacilitySchema(ma.ModelSchema):
    class Meta:
        include_fk = True
        model = HealthFacility

class FollowUpSchema(ma.ModelSchema):
    healthcareWorker = fields.Nested(UserSchema)
    class Meta:
        include_fk = True
        model = FollowUp

class ReferralSchema(ma.ModelSchema):
    followUp = fields.Nested(FollowUpSchema)
    class Meta:
        include_fk = True
        model = Referral

user_schema = {
    "type": "object",
    "properties": {
        "username": {
            "type": "string",
        },
        "email": {
            "type": "string",
            "format": "email"
        },
        "firstName": {
            "type": "string",
        },
        "role": {
            "type": "string",
        },
        "healthFacilityName": {
            "type": "string",
        },
        "password": {
            "type": "string",
            "minLength": 5
        },
    },
    "required": ["email", "password"],
    "additionalProperties": False
}


def validate_user(data):
    try:
        validate(data, user_schema)
    except ValidationError as e:
        return {'ok': False, 'message': e}
    except SchemaError as e:
        return {'ok': False, 'message': e}
    return {'ok': True, 'data': data}
