"""SOAP type definitions for OptionObject2015 structure.

These types mirror the myAvatar ScriptLink WSDL definitions exactly,
including the Base class inheritance pattern.
"""
from spyne import ComplexModel, Unicode, Double, Boolean, Array


# Target namespace must match Netsmart's expected namespace
TNS = "http://tempuri.org/"


class FieldObjectBase(ComplexModel):
    """Base class for FieldObject."""
    __namespace__ = TNS
    _type_info = [
        ('Enabled', Unicode),
        ('FieldNumber', Unicode),
        ('FieldValue', Unicode),
        ('Lock', Unicode),
        ('Required', Unicode),
    ]


class FieldObject(FieldObjectBase):
    """Represents a single field on a form."""
    __namespace__ = TNS


# Create the array type with the correct name
ArrayOfFieldObject = Array(FieldObject, type_name='ArrayOfFieldObject')


class RowObjectBase(ComplexModel):
    """Base class for RowObject."""
    __namespace__ = TNS
    _type_info = [
        ('Fields', ArrayOfFieldObject.customize(nillable=True)),
        ('ParentRowId', Unicode),
        ('RowAction', Unicode),
        ('RowId', Unicode),
    ]


class RowObject(RowObjectBase):
    """Represents a row of fields in a form."""
    __namespace__ = TNS


ArrayOfRowObject = Array(RowObject, type_name='ArrayOfRowObject')


class FormObjectBase(ComplexModel):
    """Base class for FormObject."""
    __namespace__ = TNS
    _type_info = [
        ('CurrentRow', RowObject),
        ('FormId', Unicode),
        ('MultipleIteration', Boolean),
        ('OtherRows', ArrayOfRowObject.customize(nillable=True)),
    ]


class FormObject(FormObjectBase):
    """Represents a form containing rows of data."""
    __namespace__ = TNS


ArrayOfFormObject = Array(FormObject, type_name='ArrayOfFormObject')


class OptionObjectBase(ComplexModel):
    """Base class for OptionObject types."""
    __namespace__ = TNS
    _type_info = [
        ('EntityID', Unicode),
        ('EpisodeNumber', Double),
        ('ErrorCode', Double),
        ('ErrorMesg', Unicode),
        ('Facility', Unicode),
        ('Forms', ArrayOfFormObject.customize(nillable=True)),
        ('NamespaceName', Unicode),
        ('OptionId', Unicode),
        ('OptionStaffId', Unicode),
        ('OptionUserId', Unicode),
        ('ParentNamespace', Unicode),
        ('ServerName', Unicode),
        ('SystemCode', Unicode),
        ('SessionToken', Unicode),
    ]


class OptionObject2015(OptionObjectBase):
    """Root data structure for ScriptLink communication.

    This is the primary object sent from myAvatar to the ScriptLink service
    and returned after modifications.
    """
    __namespace__ = TNS


# Error code constants for clarity
class ErrorCodes:
    """Error code constants matching myAvatar behavior."""

    NONE = 0  # Success - no message displayed
    ERROR = 1  # Error message - blocks form submission
    OK_CANCEL = 2  # Message with OK/Cancel buttons
    ALERT = 3  # Informational alert popup
    CONFIRM = 4 # Yes/No confirmation dialog
    URL = 5  # Opens URL in ErrorMesg field
    OPEN_FORM = 6  # Opens form specified in ErrorMesg
