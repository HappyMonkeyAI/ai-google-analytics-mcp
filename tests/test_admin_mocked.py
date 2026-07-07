from unittest.mock import MagicMock, patch

from ga4_provision_mcp import admin as ga_admin


def test_normalize_property_id():
    assert ga_admin.normalize_property_id("properties/999") == "999"
    assert ga_admin.normalize_property_id("999") == "999"


@patch("ga4_provision_mcp.admin._client")
def test_provision_property_mock(mock_client):
    client = MagicMock()
    mock_client.return_value = client
    created = MagicMock()
    created.name = "properties/12345"
    created.display_name = "My App - Production"
    client.create_property.return_value = created

    result = ga_admin.provision_property("accounts/111", "My App")
    assert result["property_id"] == "12345"
    client.create_property.assert_called_once()