"""Example script template.

Copy this file and rename to match your ScriptLink parameter.
E.g., MY_VALIDATION.py for parameter "MY_VALIDATION"

The script will be discovered automatically at runtime - no restart needed.
"""
from app.scriptlink import OptionObjectWrapper, OptionObject2015, ValidationError, AlertError, get_connection


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

    # Block form submission with error (option 1: raise exception)
    if not value:
        raise ValidationError("Field 123.45 is required")

    # Block form submission with error (option 2: set directly)
    # option_object.set_error("Something went wrong")

    # Show informational popup (doesn't block)
    # raise AlertError("Record was processed successfully")
    # or: option_object.set_alert("Info message")

    # Open URL in browser
    # option_object.open_url("https://example.com")

    # Open another form
    # option_object.open_form("FORM_ID")

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
