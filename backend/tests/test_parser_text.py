from app.services.parser import parse_document

def test_parse_txt(tmp_path):
    file = tmp_path / "policy.txt"
    file.write_text("# Refunds\\nRefunds within 30 days.", encoding="utf-8")
    result = parse_document(file)
    assert result["file_type"] == "txt"
    assert result["blocks"][0]["type"] == "heading"
