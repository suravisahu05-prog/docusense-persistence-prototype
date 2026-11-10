from app.services.technical_rules import extract_technical_eav
from app.services.contradiction_engine import analyze_eav, dashboard_payload


def _eavs(text, doc, filename):
    return extract_technical_eav(text, doc, filename)


def test_polling_interval_and_gateway_timeout_are_risk_not_direct_conflict():
    a = _eavs("Sensor polling interval is 60 seconds.", "doc-a", "sensor_manual.txt")
    b = _eavs("Cloud gateway timeout limit is 30 seconds.", "doc-b", "gateway_spec.txt")
    findings = analyze_eav(a + b)
    assert len(findings) == 1
    assert findings[0]["type"] == "potential_operational_conflict"
    assert findings[0]["status"] == "needs_review"
    assert findings[0]["evidence"] == ["Sensor polling interval is 60 seconds.", "Cloud gateway timeout limit is 30 seconds."]


def test_same_attribute_different_values_is_direct_conflict():
    a = _eavs("Device request timeout is 60 seconds.", "doc-a", "manual.txt")
    b = _eavs("Device request timeout is 30 seconds.", "doc-b", "cloud.txt")
    findings = analyze_eav(a + b)
    assert any(x["type"] == "direct_conflict" for x in findings)


def test_duration_units_are_normalized():
    eav = _eavs("Gateway timeout is 500 ms.", "doc-a", "gateway.txt")
    assert eav[0]["value"] == 0.5
    assert eav[0]["unit"] == "seconds"


def test_firmware_and_hardware_attributes_are_extracted():
    eavs = _eavs("Firmware version is 2.4.1.\nMaximum operating temperature is 70 C.\nMaximum payload size is 1 MB.\nSupply voltage is 5 V.", "doc-a", "hardware.txt")
    attrs = {x["attribute"] for x in eavs}
    assert {"firmware_version", "max_operating_temperature", "max_payload_size", "voltage"} <= attrs
    assert all(x["evidence"] and x["source_file"] == "hardware.txt" for x in eavs)


def test_dashboard_payload_registers_findings_and_summary():
    a = _eavs("Sensor polling interval is 60 seconds.", "doc-a", "sensor.txt")
    b = _eavs("Gateway timeout is 30 seconds.", "doc-b", "gateway.txt")
    findings = analyze_eav(a + b)
    payload = dashboard_payload("scan-123", [{}, {}], a + b, findings)
    assert payload["dashboard"]["status"] == "ready"
    assert payload["summary"]["operational_risks"] == 1
    assert payload["dashboard"]["findings"][0]["status"] == "needs_review"


def test_device_request_timeout_above_gateway_cap_is_operational_risk():
    a = _eavs("Sensor request timeout is 60 seconds.", "doc-a", "sensor_manual.txt")
    b = _eavs("Cloud gateway request timeout limit is 30 seconds.", "doc-b", "gateway_spec.txt")
    findings = analyze_eav(a + b)
    assert any(x["type"] == "potential_operational_conflict" and
               x["attribute"] == "request_timeout_vs_gateway_timeout" for x in findings)
