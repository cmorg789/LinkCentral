"""HTTP Request node for external API calls."""
import json
from typing import Optional

import requests
from requests.auth import HTTPBasicAuth

from app.workflow.nodes.base import BaseNode
from app.workflow.context import ExecutionContext


class HTTPRequestNode(BaseNode):
    """Makes HTTP requests to external APIs.

    Properties:
        url: Request URL (supports templates)
        method: HTTP method (GET, POST, PUT, DELETE, PATCH)
        headers: Dict of header name -> value (supports templates)
        body: Request body for POST/PUT/PATCH (supports templates)
        timeout: Timeout in seconds (default 30)
        auth_type: Authentication type ('none', 'basic', 'bearer')
        auth_config: Auth configuration dict:
            - For 'basic': {"username": "...", "password": "..."}
            - For 'bearer': {"token": "..."}
        output_variable: Variable name to store response
        parse_json: Auto-parse JSON response (default true)

    Response stored in output_variable contains:
        - If parse_json and response is JSON: parsed object
        - Otherwise: {"status_code": int, "text": str, "headers": dict}
    """

    SUPPORTED_METHODS = {"GET", "POST", "PUT", "DELETE", "PATCH"}

    def execute(self, context: ExecutionContext) -> Optional[str]:
        """Execute the HTTP request and store response."""
        url = self.get_property("url", "")
        method = self.get_property("method", "GET").upper()
        headers = self.get_property("headers", {})
        body = self.get_property("body", "")
        auth_type = self.get_property("auth_type", "none")
        auth_config = self.get_property("auth_config", {})
        output_variable = self.get_property("output_variable", "http_response")
        parse_json = self.get_property("parse_json", True)

        # Validate timeout
        try:
            timeout = float(self.get_property("timeout", 30))
            if timeout <= 0:
                timeout = 30
        except (ValueError, TypeError):
            timeout = 30

        if not url:
            context.variables[output_variable] = {"error": "No URL provided"}
            return self.get_output("default")

        if method not in self.SUPPORTED_METHODS:
            context.variables[output_variable] = {"error": f"Unsupported method: {method}"}
            return self.get_output("default")

        # Resolve URL template
        resolved_url = context.resolve_template(url)

        # Resolve header templates
        resolved_headers = {}
        for header_name, header_value in headers.items():
            resolved_headers[header_name] = context.resolve_template(str(header_value))

        # Resolve body template
        resolved_body = context.resolve_template(body) if body else None

        # Build auth
        auth = None
        if auth_type == "basic":
            username = context.resolve_template(auth_config.get("username", ""))
            password = context.resolve_template(auth_config.get("password", ""))
            auth = HTTPBasicAuth(username, password)
        elif auth_type == "bearer":
            token = context.resolve_template(auth_config.get("token", ""))
            resolved_headers["Authorization"] = f"Bearer {token}"

        try:
            # Make the request
            response = requests.request(
                method=method,
                url=resolved_url,
                headers=resolved_headers,
                data=resolved_body,
                timeout=timeout,
                auth=auth,
            )

            # Parse response
            if parse_json:
                try:
                    result = response.json()
                except (json.JSONDecodeError, ValueError):
                    # Not JSON, return raw response info
                    result = {
                        "status_code": response.status_code,
                        "text": response.text,
                        "headers": dict(response.headers),
                    }
            else:
                result = {
                    "status_code": response.status_code,
                    "text": response.text,
                    "headers": dict(response.headers),
                }

            context.variables[output_variable] = result

        except requests.Timeout:
            context.variables[output_variable] = {"error": "Request timed out"}
        except requests.RequestException as e:
            context.variables[output_variable] = {"error": f"Request failed: {str(e)}"}

        return self.get_output("default")
