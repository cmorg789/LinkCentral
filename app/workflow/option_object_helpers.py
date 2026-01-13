"""Helpers for converting between OptionObject and dict for JSON serialization."""
from typing import Any, Dict, List, Optional, Set, Tuple

from app.soap.types import (
    OptionObject2015,
    FormObject,
    RowObject,
    FieldObject,
)


def field_to_dict(field: FieldObject) -> Dict[str, Any]:
    """Convert a FieldObject to a dictionary.

    Args:
        field: The FieldObject to convert

    Returns:
        Dictionary representation
    """
    return {
        "FieldNumber": field.FieldNumber,
        "FieldValue": field.FieldValue,
        "Enabled": field.Enabled,
        "Lock": field.Lock,
        "Required": field.Required,
    }


def dict_to_field(data: Dict[str, Any]) -> FieldObject:
    """Convert a dictionary to a FieldObject.

    Args:
        data: Dictionary with field data

    Returns:
        FieldObject instance
    """
    # Use constructor arguments - Spyne ComplexModel doesn't reliably
    # support post-initialization attribute assignment
    return FieldObject(
        FieldNumber=data.get("FieldNumber"),
        FieldValue=data.get("FieldValue"),
        Enabled=data.get("Enabled"),
        Lock=data.get("Lock"),
        Required=data.get("Required"),
    )


def row_to_dict(row: RowObject) -> Dict[str, Any]:
    """Convert a RowObject to a dictionary.

    Args:
        row: The RowObject to convert

    Returns:
        Dictionary representation
    """
    return {
        "RowId": row.RowId,
        "ParentRowId": row.ParentRowId,
        "RowAction": row.RowAction,
        "Fields": [field_to_dict(f) for f in row.Fields] if row.Fields else [],
    }


def dict_to_row(data: Dict[str, Any]) -> RowObject:
    """Convert a dictionary to a RowObject.

    Args:
        data: Dictionary with row data

    Returns:
        RowObject instance
    """
    # Use constructor arguments - Spyne ComplexModel doesn't reliably
    # support post-initialization attribute assignment
    fields_data = data.get("Fields", [])
    return RowObject(
        RowId=data.get("RowId"),
        ParentRowId=data.get("ParentRowId"),
        RowAction=data.get("RowAction"),
        Fields=[dict_to_field(f) for f in fields_data] if fields_data else [],
    )


def form_to_dict(form: FormObject) -> Dict[str, Any]:
    """Convert a FormObject to a dictionary.

    Args:
        form: The FormObject to convert

    Returns:
        Dictionary representation
    """
    return {
        "FormId": form.FormId,
        "MultipleIteration": form.MultipleIteration,
        "CurrentRow": row_to_dict(form.CurrentRow) if form.CurrentRow else None,
        "OtherRows": [row_to_dict(r) for r in form.OtherRows] if form.OtherRows else [],
    }


def dict_to_form(data: Dict[str, Any]) -> FormObject:
    """Convert a dictionary to a FormObject.

    Args:
        data: Dictionary with form data

    Returns:
        FormObject instance
    """
    # Use constructor arguments - Spyne ComplexModel doesn't reliably
    # support post-initialization attribute assignment
    current_row_data = data.get("CurrentRow")
    other_rows_data = data.get("OtherRows", [])

    current_row = dict_to_row(current_row_data) if current_row_data else None

    return FormObject(
        FormId=data.get("FormId"),
        MultipleIteration=data.get("MultipleIteration"),
        CurrentRow=current_row,
        OtherRows=[dict_to_row(r) for r in other_rows_data] if other_rows_data else [],
    )


def option_object_to_dict(obj: OptionObject2015) -> Dict[str, Any]:
    """Convert an OptionObject2015 to a dictionary.

    Args:
        obj: The OptionObject2015 to convert

    Returns:
        Dictionary representation suitable for JSON serialization
    """
    return {
        "EntityID": obj.EntityID,
        "EpisodeNumber": obj.EpisodeNumber,
        "ErrorCode": obj.ErrorCode,
        "ErrorMesg": obj.ErrorMesg,
        "Facility": obj.Facility,
        "NamespaceName": obj.NamespaceName,
        "OptionId": obj.OptionId,
        "OptionStaffId": obj.OptionStaffId,
        "OptionUserId": obj.OptionUserId,
        "ParentNamespace": obj.ParentNamespace,
        "ServerName": obj.ServerName,
        "SystemCode": obj.SystemCode,
        "SessionToken": obj.SessionToken,
        "Forms": [form_to_dict(f) for f in obj.Forms] if obj.Forms else [],
    }


def dict_to_option_object(data: Dict[str, Any]) -> OptionObject2015:
    """Convert a dictionary to an OptionObject2015.

    Args:
        data: Dictionary with OptionObject data

    Returns:
        OptionObject2015 instance
    """
    # Use constructor arguments - Spyne ComplexModel doesn't reliably
    # support post-initialization attribute assignment
    forms_data = data.get("Forms", [])

    return OptionObject2015(
        EntityID=data.get("EntityID"),
        EpisodeNumber=data.get("EpisodeNumber"),
        ErrorCode=data.get("ErrorCode", 0.0),
        ErrorMesg=data.get("ErrorMesg"),
        Facility=data.get("Facility"),
        NamespaceName=data.get("NamespaceName"),
        OptionId=data.get("OptionId"),
        OptionStaffId=data.get("OptionStaffId"),
        OptionUserId=data.get("OptionUserId"),
        ParentNamespace=data.get("ParentNamespace"),
        ServerName=data.get("ServerName"),
        SystemCode=data.get("SystemCode"),
        SessionToken=data.get("SessionToken"),
        Forms=[dict_to_form(f) for f in forms_data] if forms_data else [],
    )


def build_delta_dict(
    modified_fields: Set[Tuple[str, str, str]],
    option_object: OptionObject2015,
) -> Dict[str, Any]:
    """Build a dictionary representing only the modified fields.

    This creates a response structure showing only what changed,
    matching the ScriptLink spec for return responses.

    Args:
        modified_fields: Set of (form_id, row_id, field_number) tuples
        option_object: The modified OptionObject2015

    Returns:
        Dictionary with only modified forms/rows/fields
    """
    # Note: Spyne ComplexModel objects return False for bool() even when they
    # contain data, so we must use explicit "is not None" checks throughout.

    if not modified_fields:
        # No modifications - return minimal response structure
        return {
            "EntityID": option_object.EntityID,
            "ErrorCode": option_object.ErrorCode,
            "ErrorMesg": option_object.ErrorMesg,
            "Forms": [],
        }

    # Group modifications by form and row
    modifications: Dict[str, Dict[str, Set[str]]] = {}
    for form_id, row_id, field_number in modified_fields:
        if form_id not in modifications:
            modifications[form_id] = {}
        if row_id not in modifications[form_id]:
            modifications[form_id][row_id] = set()
        modifications[form_id][row_id].add(field_number)

    # Build delta forms
    delta_forms = []

    if option_object.Forms is not None:
        for form in option_object.Forms:
            if form.FormId not in modifications:
                continue

            form_mods = modifications[form.FormId]
            delta_rows = []

            # Check CurrentRow - use "is not None" because Spyne objects are falsy
            if form.CurrentRow is not None and form.CurrentRow.RowId in form_mods:
                modified_field_numbers = form_mods[form.CurrentRow.RowId]
                delta_row = _build_delta_row(form.CurrentRow, modified_field_numbers)
                if delta_row:
                    delta_rows.append(delta_row)

            # Check OtherRows
            if form.OtherRows is not None:
                for row in form.OtherRows:
                    if row.RowId in form_mods:
                        modified_field_numbers = form_mods[row.RowId]
                        delta_row = _build_delta_row(row, modified_field_numbers)
                        if delta_row:
                            delta_rows.append(delta_row)

            if delta_rows:
                delta_form = {
                    "FormId": form.FormId,
                    "MultipleIteration": form.MultipleIteration,
                    "CurrentRow": delta_rows[0] if delta_rows else None,
                    "OtherRows": delta_rows[1:] if len(delta_rows) > 1 else [],
                }
                delta_forms.append(delta_form)

    return {
        "EntityID": option_object.EntityID,
        "ErrorCode": option_object.ErrorCode,
        "ErrorMesg": option_object.ErrorMesg,
        "Forms": delta_forms,
    }


def _build_delta_row(row: RowObject, modified_field_numbers: Set[str]) -> Optional[Dict[str, Any]]:
    """Build a row dictionary containing only modified fields.

    Args:
        row: The original row
        modified_field_numbers: Set of field numbers that were modified

    Returns:
        Dictionary with only modified fields, or None if no fields
    """
    # Note: Spyne ComplexModel objects return False for bool() even when they
    # contain data, so we must use explicit "is None" check.
    if row.Fields is None:
        return None

    modified_fields = []
    for field in row.Fields:
        if field.FieldNumber in modified_field_numbers:
            modified_fields.append(field_to_dict(field))

    if not modified_fields:
        return None

    return {
        "RowId": row.RowId,
        "ParentRowId": row.ParentRowId,
        "RowAction": "EDIT",
        "Fields": modified_fields,
    }
