"""Pythonic wrapper for OptionObject2015 with change tracking."""
from typing import Any, Dict, Iterator, List, Optional, Set, Tuple

from app.soap.types import (
    OptionObject2015,
    FormObject,
    RowObject,
    FieldObject,
    ErrorCodes,
)


class FieldWrapper:
    """Wrapper for a single field with property access.

    Example:
        field = wrapper.fields["123.45"]
        value = field.value
        field.value = "new value"
        field.required = True
        field.enabled = False
        field.locked = True
    """

    def __init__(
        self,
        field_obj: FieldObject,
        form_id: str,
        row_id: str,
        tracker: "OptionObjectWrapper",
    ):
        self._field = field_obj
        self._form_id = form_id
        self._row_id = row_id
        self._tracker = tracker

    @property
    def value(self) -> Optional[str]:
        """Get the field value."""
        return self._field.FieldValue

    @value.setter
    def value(self, val: str) -> None:
        """Set the field value and track the modification."""
        self._field.FieldValue = val
        self._tracker._mark_modified(self._form_id, self._row_id, self._field.FieldNumber)

    @property
    def enabled(self) -> bool:
        """Whether the field is enabled."""
        return self._field.Enabled == "1"

    @enabled.setter
    def enabled(self, val: bool) -> None:
        """Set the enabled state and track the modification."""
        self._field.Enabled = "1" if val else "0"
        self._tracker._mark_modified(self._form_id, self._row_id, self._field.FieldNumber)

    @property
    def required(self) -> bool:
        """Whether the field is required."""
        return self._field.Required == "1"

    @required.setter
    def required(self, val: bool) -> None:
        """Set the required state and track the modification."""
        self._field.Required = "1" if val else "0"
        self._tracker._mark_modified(self._form_id, self._row_id, self._field.FieldNumber)

    @property
    def locked(self) -> bool:
        """Whether the field is locked."""
        return self._field.Lock == "1"

    @locked.setter
    def locked(self, val: bool) -> None:
        """Set the locked state and track the modification."""
        self._field.Lock = "1" if val else "0"
        self._tracker._mark_modified(self._form_id, self._row_id, self._field.FieldNumber)

    def __str__(self) -> str:
        return self.value or ""


class FieldAccessor:
    """Dict-like access to fields by field number.

    Example:
        fields = wrapper.fields
        value = fields["123.45"]         # Get FieldWrapper
        fields["123.45"] = "new value"   # Set value directly
        value = fields.get("123.45", "") # Get with default
    """

    def __init__(self, wrapper: "OptionObjectWrapper"):
        self._wrapper = wrapper

    def _find_field(self, field_number: str) -> Optional[Tuple[FieldObject, str, str]]:
        """Find a field and return (field_obj, form_id, row_id) or None."""
        obj = self._wrapper._obj

        if obj.Forms is None:
            return None

        for form in obj.Forms:
            # Check CurrentRow
            if form.CurrentRow is not None and form.CurrentRow.Fields is not None:
                for field_obj in form.CurrentRow.Fields:
                    if field_obj.FieldNumber == field_number:
                        return (field_obj, form.FormId, form.CurrentRow.RowId)

            # Check OtherRows
            if form.OtherRows is not None:
                for row in form.OtherRows:
                    if row.Fields is not None:
                        for field_obj in row.Fields:
                            if field_obj.FieldNumber == field_number:
                                return (field_obj, form.FormId, row.RowId)

        return None

    def __getitem__(self, field_number: str) -> FieldWrapper:
        """Get a field wrapper by field number.

        Raises KeyError if field not found.
        """
        result = self._find_field(field_number)
        if result is None:
            raise KeyError(f"Field {field_number} not found")
        field_obj, form_id, row_id = result
        return FieldWrapper(field_obj, form_id, row_id, self._wrapper)

    def __setitem__(self, field_number: str, value: str) -> None:
        """Set a field value by field number.

        Raises KeyError if field not found.
        """
        result = self._find_field(field_number)
        if result is None:
            raise KeyError(f"Field {field_number} not found")
        field_obj, form_id, row_id = result
        field_obj.FieldValue = value
        self._wrapper._mark_modified(form_id, row_id, field_number)

    def get(self, field_number: str, default: str = "") -> str:
        """Get a field value with default if not found."""
        result = self._find_field(field_number)
        if result is None:
            return default
        return result[0].FieldValue or default

    def __contains__(self, field_number: str) -> bool:
        """Check if a field exists."""
        return self._find_field(field_number) is not None


class OptionObjectWrapper:
    """Pythonic wrapper for OptionObject2015 with change tracking and diff support.

    Example:
        wrapper = OptionObjectWrapper(option_object)

        # Field access
        value = wrapper.fields.get("123.45", "")
        wrapper.fields["123.45"] = "new value"
        wrapper.fields["123.45"].required = True

        # Metadata
        entity_id = wrapper.entity_id
        facility = wrapper.facility

        # Error responses
        wrapper.set_error("Validation failed")
        wrapper.set_alert("Record updated")

        # Get diff of changes (for logging/debugging)
        diff = wrapper.get_diff()

        # Build response with only changes
        response = wrapper.build_response()
    """

    def __init__(self, spyne_obj: OptionObject2015):
        self._obj = spyne_obj
        self._modified_fields: Set[Tuple[str, str, str]] = set()  # (form_id, row_id, field_number)
        self._fields = FieldAccessor(self)
        # Capture initial state for diff
        self._initial_snapshot = self._capture_snapshot()

    def _mark_modified(self, form_id: str, row_id: str, field_number: str) -> None:
        """Track a field modification."""
        self._modified_fields.add((form_id, row_id, field_number))

    def _capture_snapshot(self) -> Dict[Tuple[str, str, str], Dict[str, Any]]:
        """Capture current state of all fields for diff comparison.

        Returns:
            Dict mapping (form_id, row_id, field_number) to {value, enabled, required, locked}
        """
        snapshot = {}

        if self._obj.Forms is None:
            return snapshot

        for form in self._obj.Forms:
            if form.CurrentRow is not None and form.CurrentRow.Fields is not None:
                for field in form.CurrentRow.Fields:
                    key = (form.FormId, form.CurrentRow.RowId, field.FieldNumber)
                    snapshot[key] = {
                        "value": field.FieldValue,
                        "enabled": field.Enabled,
                        "required": field.Required,
                        "locked": field.Lock,
                    }

            if form.OtherRows is not None:
                for row in form.OtherRows:
                    if row.Fields is not None:
                        for field in row.Fields:
                            key = (form.FormId, row.RowId, field.FieldNumber)
                            snapshot[key] = {
                                "value": field.FieldValue,
                                "enabled": field.Enabled,
                                "required": field.Required,
                                "locked": field.Lock,
                            }

        return snapshot

    def get_diff(self) -> Dict[str, Dict[str, Any]]:
        """Get differences between initial and current state.

        Returns:
            Dict mapping field_number to changes:
            {
                "123.45": {
                    "value": {"old": "foo", "new": "bar"},
                    "required": {"old": "0", "new": "1"}
                }
            }
        """
        diff = {}
        current = self._capture_snapshot()

        # Check all fields that existed initially
        for key, old_state in self._initial_snapshot.items():
            new_state = current.get(key, {})
            field_changes = {}

            for prop in ["value", "enabled", "required", "locked"]:
                old_val = old_state.get(prop)
                new_val = new_state.get(prop)
                if old_val != new_val:
                    field_changes[prop] = {"old": old_val, "new": new_val}

            if field_changes:
                # Use field_number as the display key
                field_number = key[2]
                diff[field_number] = field_changes

        return diff

    @property
    def fields(self) -> FieldAccessor:
        """Access fields by field number."""
        return self._fields

    def unwrap(self) -> OptionObject2015:
        """Get the underlying OptionObject2015 for return from scripts.

        Call this when returning from a script to get the raw Spyne object.

        Example:
            def run(ctx: ScriptContext) -> OptionObject2015:
                ctx.option_object.fields["123.45"] = "processed"
                return ctx.option_object.unwrap()
        """
        return self._obj

    # Metadata properties
    @property
    def entity_id(self) -> Optional[str]:
        """Patient/Entity ID."""
        return self._obj.EntityID

    @property
    def episode_number(self) -> Optional[float]:
        """Episode number."""
        return self._obj.EpisodeNumber

    @property
    def facility(self) -> Optional[str]:
        """Facility code."""
        return self._obj.Facility

    @property
    def option_user_id(self) -> Optional[str]:
        """Current user ID."""
        return self._obj.OptionUserId

    @property
    def option_staff_id(self) -> Optional[str]:
        """Current staff ID."""
        return self._obj.OptionStaffId

    @property
    def option_id(self) -> Optional[str]:
        """Option ID."""
        return self._obj.OptionId

    @property
    def system_code(self) -> Optional[str]:
        """System code."""
        return self._obj.SystemCode

    @property
    def server_name(self) -> Optional[str]:
        """Server name."""
        return self._obj.ServerName

    @property
    def namespace_name(self) -> Optional[str]:
        """Namespace name."""
        return self._obj.NamespaceName

    @property
    def parent_namespace(self) -> Optional[str]:
        """Parent namespace."""
        return self._obj.ParentNamespace

    @property
    def session_token(self) -> Optional[str]:
        """Session token."""
        return self._obj.SessionToken

    # Error response methods
    def set_error(self, message: str, code: float = ErrorCodes.ERROR) -> None:
        """Set error response that blocks form submission.

        Args:
            message: Error message to display
            code: Error code (default: ERROR which blocks submission)
        """
        self._obj.ErrorCode = code
        self._obj.ErrorMesg = message

    def set_alert(self, message: str) -> None:
        """Show informational alert popup without blocking."""
        self._obj.ErrorCode = ErrorCodes.ALERT
        self._obj.ErrorMesg = message

    def open_url(self, url: str) -> None:
        """Open URL in browser."""
        self._obj.ErrorCode = ErrorCodes.URL
        self._obj.ErrorMesg = url

    def open_form(self, form_id: str) -> None:
        """Open a form by ID."""
        self._obj.ErrorCode = ErrorCodes.OPEN_FORM
        self._obj.ErrorMesg = form_id

    def no_changes(self) -> OptionObject2015:
        """Return a response with no modifications.

        Discards any tracked field changes and returns empty forms.
        """
        self._modified_fields.clear()
        return self.build_response()

    # Response building
    def build_response(self) -> OptionObject2015:
        """Build minimal response with only modified forms/rows/fields.

        Returns OptionObject2015 ready for SOAP response.
        Per ScriptLink spec, response should only contain modified data.
        """
        response = OptionObject2015()

        # Copy all metadata
        response.EntityID = self._obj.EntityID
        response.EpisodeNumber = self._obj.EpisodeNumber
        response.ErrorCode = self._obj.ErrorCode
        response.ErrorMesg = self._obj.ErrorMesg
        response.Facility = self._obj.Facility
        response.NamespaceName = self._obj.NamespaceName
        response.OptionId = self._obj.OptionId
        response.OptionStaffId = self._obj.OptionStaffId
        response.OptionUserId = self._obj.OptionUserId
        response.ParentNamespace = self._obj.ParentNamespace
        response.ServerName = self._obj.ServerName
        response.SystemCode = self._obj.SystemCode
        response.SessionToken = self._obj.SessionToken

        # If no modifications, return empty forms
        if not self._modified_fields:
            response.Forms = []
            return response

        # Build forms with only modified rows/fields
        response.Forms = []

        if self._obj.Forms is None:
            return response

        for form in self._obj.Forms:
            # Get modifications in this form
            form_mods = {(row_id, field_num) for (fid, row_id, field_num) in self._modified_fields if fid == form.FormId}

            if not form_mods:
                continue

            # Build response form
            resp_form = FormObject()
            resp_form.FormId = form.FormId
            resp_form.MultipleIteration = form.MultipleIteration

            # Get modified row IDs
            modified_row_ids = {row_id for (row_id, _) in form_mods}

            # Build CurrentRow if modified
            if form.CurrentRow is not None and form.CurrentRow.RowId in modified_row_ids:
                resp_form.CurrentRow = self._build_row_response(
                    form.CurrentRow,
                    {field_num for (row_id, field_num) in form_mods if row_id == form.CurrentRow.RowId}
                )

            # Build OtherRows if any modified
            if form.OtherRows is not None:
                other_rows = []
                for row in form.OtherRows:
                    if row.RowId in modified_row_ids:
                        other_rows.append(self._build_row_response(
                            row,
                            {field_num for (row_id, field_num) in form_mods if row_id == row.RowId}
                        ))
                if other_rows:
                    resp_form.OtherRows = other_rows

            response.Forms.append(resp_form)

        return response

    def _build_row_response(self, row: RowObject, modified_field_nums: Set[str]) -> RowObject:
        """Build a row with only modified fields."""
        resp_row = RowObject()
        resp_row.RowId = row.RowId
        resp_row.ParentRowId = row.ParentRowId
        resp_row.RowAction = "EDIT"  # Mark as edited

        if row.Fields is not None:
            resp_row.Fields = [
                self._copy_field(f) for f in row.Fields
                if f.FieldNumber in modified_field_nums
            ]

        return resp_row

    def _copy_field(self, field: FieldObject) -> FieldObject:
        """Create a copy of a field object."""
        new_field = FieldObject()
        new_field.FieldNumber = field.FieldNumber
        new_field.FieldValue = field.FieldValue
        new_field.Enabled = field.Enabled
        new_field.Lock = field.Lock
        new_field.Required = field.Required
        return new_field

    def get_changes(self) -> Dict[str, Any]:
        """Return dict of all changes for debugging/logging."""
        return {
            "modified_fields": [list(f) for f in self._modified_fields],
            "error_code": self._obj.ErrorCode,
            "error_message": self._obj.ErrorMesg,
        }

    def to_dict(self) -> Dict[str, Any]:
        """Convert the OptionObject to a dictionary for debugging/logging."""
        data = {
            "EntityID": self._obj.EntityID,
            "EpisodeNumber": self._obj.EpisodeNumber,
            "ErrorCode": self._obj.ErrorCode,
            "ErrorMesg": self._obj.ErrorMesg,
            "Facility": self._obj.Facility,
            "NamespaceName": self._obj.NamespaceName,
            "OptionId": self._obj.OptionId,
            "OptionStaffId": self._obj.OptionStaffId,
            "OptionUserId": self._obj.OptionUserId,
            "ParentNamespace": self._obj.ParentNamespace,
            "ServerName": self._obj.ServerName,
            "SystemCode": self._obj.SystemCode,
            "Forms": [],
        }

        if self._obj.Forms is not None:
            for form in self._obj.Forms:
                form_data = {
                    "FormId": form.FormId,
                    "MultipleIteration": form.MultipleIteration,
                    "CurrentRow": self._row_to_dict(form.CurrentRow) if form.CurrentRow is not None else None,
                    "OtherRows": [self._row_to_dict(r) for r in (form.OtherRows or [])],
                }
                data["Forms"].append(form_data)

        return data

    def _row_to_dict(self, row: RowObject) -> Dict[str, Any]:
        """Convert a row to dictionary."""
        fields = []
        if row.Fields is not None:
            for f in row.Fields:
                fields.append({
                    "FieldNumber": f.FieldNumber,
                    "FieldValue": f.FieldValue,
                    "Enabled": f.Enabled,
                    "Lock": f.Lock,
                    "Required": f.Required,
                })

        return {
            "RowId": row.RowId,
            "ParentRowId": row.ParentRowId,
            "RowAction": row.RowAction,
            "Fields": fields,
        }


def from_dict(data: Dict[str, Any]) -> OptionObject2015:
    """Reconstruct OptionObject2015 from dictionary (reverse of to_dict()).

    Used for loading JSON fixtures in testing.

    Args:
        data: Dictionary with structure matching to_dict() output

    Returns:
        Fully populated OptionObject2015 instance

    Example:
        with open("fixture.json") as f:
            data = json.load(f)
        option_object = from_dict(data)
    """
    obj = OptionObject2015()

    # Copy metadata fields
    obj.EntityID = data.get("EntityID")
    obj.EpisodeNumber = data.get("EpisodeNumber")
    obj.ErrorCode = data.get("ErrorCode", 0.0)
    obj.ErrorMesg = data.get("ErrorMesg")
    obj.Facility = data.get("Facility")
    obj.NamespaceName = data.get("NamespaceName")
    obj.OptionId = data.get("OptionId")
    obj.OptionStaffId = data.get("OptionStaffId")
    obj.OptionUserId = data.get("OptionUserId")
    obj.ParentNamespace = data.get("ParentNamespace")
    obj.ServerName = data.get("ServerName")
    obj.SystemCode = data.get("SystemCode")
    obj.SessionToken = data.get("SessionToken")

    # Reconstruct Forms
    forms_data = data.get("Forms", [])
    if forms_data:
        obj.Forms = [_dict_to_form(f) for f in forms_data]
    else:
        obj.Forms = []

    return obj


def _dict_to_form(data: Dict[str, Any]) -> FormObject:
    """Convert dictionary to FormObject."""
    form = FormObject()
    form.FormId = data.get("FormId")
    form.MultipleIteration = data.get("MultipleIteration", False)

    # Reconstruct CurrentRow
    current_row_data = data.get("CurrentRow")
    if current_row_data is not None:
        form.CurrentRow = _dict_to_row(current_row_data)

    # Reconstruct OtherRows
    other_rows_data = data.get("OtherRows", [])
    if other_rows_data:
        form.OtherRows = [_dict_to_row(r) for r in other_rows_data]

    return form


def _dict_to_row(data: Dict[str, Any]) -> RowObject:
    """Convert dictionary to RowObject."""
    row = RowObject()
    row.RowId = data.get("RowId")
    row.ParentRowId = data.get("ParentRowId")
    row.RowAction = data.get("RowAction")

    # Reconstruct Fields
    fields_data = data.get("Fields", [])
    if fields_data:
        row.Fields = [_dict_to_field(f) for f in fields_data]

    return row


def _dict_to_field(data: Dict[str, Any]) -> FieldObject:
    """Convert dictionary to FieldObject."""
    field = FieldObject()
    field.FieldNumber = data.get("FieldNumber")
    field.FieldValue = data.get("FieldValue")
    field.Enabled = data.get("Enabled", "1")
    field.Lock = data.get("Lock", "0")
    field.Required = data.get("Required", "0")
    return field
