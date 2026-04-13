"""Example script template.

Copy this file and rename to match your ScriptLink parameter.
E.g., MY_VALIDATION.py for parameter "MY_VALIDATION"

The script will be discovered automatically at runtime - no restart needed.

Testing locally:
    python -m app.scriptlink test MY_VALIDATION data/missing_scripts/MY_VALIDATION_2026-01-16.json
    python -m app.scriptlink test MY_VALIDATION fixture.json --verbose  # shows print() output
"""
from app.scriptlink import (
    OptionObjectWrapper,
    OptionObject2015,
    ValidationError,
    AlertError,
    OkCancelError,
    ConfirmError,
    OpenUrlError,
    OpenFormError,
    get_connection,
)


def run(option_object: OptionObjectWrapper) -> OptionObject2015:
    """Script entry point.

    Args:
        option_object: Wrapper around OptionObject2015 with field access and diff tracking

    Returns:
        OptionObject2015 response with only modified fields

    Raises:
        ValidationError: To block form submission with error message
        AlertError: To show informational popup without blocking
    """
    # =========================================================================
    # FIELD ACCESS
    # =========================================================================

    # Get field value (returns empty string if not found)
    value = option_object.fields.get("123.45", "")

    # Get field value (raises KeyError if not found)
    # value = option_object.fields["123.45"]

    # Set field value (tracked automatically)
    option_object.fields["123.45"] = "New Value"

    # Set field properties
    option_object.fields["123.45"].required = True
    option_object.fields["123.45"].enabled = False
    option_object.fields["123.45"].locked = True

    # =========================================================================
    # METADATA ACCESS
    # =========================================================================

    entity_id = option_object.entity_id      # Patient/Entity ID
    facility = option_object.facility        # Facility code
    episode = option_object.episode_number   # Episode number
    user_id = option_object.option_user_id   # Current user
    staff_id = option_object.option_staff_id # Current staff

    # =========================================================================
    # DATABASE ACCESS
    # =========================================================================

    # Get a configured connection by name (from config/connections.yaml)
    conn = get_connection("MyDatabase")

    # Execute SELECT query
    results = conn.query(
        "SELECT * FROM patients WHERE id = :id",
        id=entity_id
    )
    for row in results:
        print(f"Found patient: {row['name']}")

    # Get single value
    count = conn.scalar("SELECT COUNT(*) FROM patients")

    # =========================================================================
    # ERROR RESPONSES
    # =========================================================================
    #
    # Error Types (raise as exceptions):
    #   ValidationError  - Blocks form submission, shows error message
    #   AlertError       - Shows popup, allows submission to continue
    #   OkCancelError    - Shows OK/Cancel dialog
    #   ConfirmError     - Shows Yes/No confirmation dialog
    #   OpenUrlError     - Opens URL in browser
    #   OpenFormError    - Opens another form by ID
    #
    # Note: Unhandled exceptions show as ALERT by default (configurable via
    #       script_error_blocking setting). Use ValidationError to explicitly
    #       block form submission.

    # Block form submission with error (option 1: raise exception)
    if not value:
        raise ValidationError("Field 123.45 is required")

    # Block form submission with error (option 2: set directly)
    # option_object.set_error("Something went wrong")

    # Show informational popup (doesn't block)
    # raise AlertError("Record was processed successfully")
    # or: option_object.set_alert("Info message")

    # Open URL in browser
    # raise OpenUrlError("https://example.com")
    # or: option_object.open_url("https://example.com")

    # Open another form
    # raise OpenFormError("FORM_ID")
    # or: option_object.open_form("FORM_ID")

    # =========================================================================
    # FORM INTROSPECTION
    # =========================================================================

    # Check what forms are available
    # form_ids = option_object.get_form_ids()          # ["100", "200"]
    # has_mi = option_object.has_form("200")            # True
    # is_mi = option_object.is_multiple_iteration("200") # True
    # count = option_object.row_count("200")            # 3

    # =========================================================================
    # ROW OPERATIONS (Multiple Iteration Forms)
    # =========================================================================
    #
    # MI forms are table-like sections where patients can have multiple rows
    # (e.g., medication lists, diagnoses). The first form on a myAvatar form
    # is always the parent; MI forms come after.
    #
    # Important myAvatar behaviors:
    #   - ADD RowAction is only allowed on FORM LOAD events (not pre-file
    #     or field-change events)
    #   - myAvatar does NOT send the MI form when the table is empty
    #   - Parent form required fields may need to be set before MI table data, depending on event logic

    # Read existing MI rows
    # rows = option_object.get_rows("200")
    # for row in rows:
    #     diagnosis = row.get("200.01", "")
    #     print(f"Row {row.row_id}: {diagnosis}")
    #     row["200.02"] = "Updated"          # set field value
    #     row["200.02"].required = True       # set field properties

    # Add a new row - clones field structure from existing rows
    # option_object.add_row("200", values={
    #     "200.01": "New diagnosis",
    #     "200.02": "2026-01-15",
    # })

    # Add a row with explicit field list (handles empty MI tables automatically)
    # option_object.add_row("200", fields=["200.01", "200.02"], values={
    #     "200.01": "New diagnosis",
    #     "200.02": "2026-01-15",
    # })

    # Add multiple rows
    # for code in ["F32.1", "F41.1", "F43.10"]:
    #     option_object.add_row("200", values={"200.01": code})

    # Delete an existing row by RowId
    # option_object.delete_row("200", "ROW_ID_HERE")

    # =========================================================================
    # LOGGING / DEBUG OUTPUT
    # =========================================================================

    # Use print() for debug output - captured by server
    print(f"Processing entity {entity_id}")

    # =========================================================================
    # RETURN RESPONSE
    # =========================================================================

    # Build and return response with only modified fields
    return option_object.build_response()
