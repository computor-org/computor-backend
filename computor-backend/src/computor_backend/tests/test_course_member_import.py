"""Tests for course member import functionality.

The batch ``import_course_members`` helper these tests used to cover was
replaced by the singular, async ``import_course_member`` (takes a
``CourseMemberImportRequest`` and needs a live Postgres + course-role ceiling
setup). Its DB-backed tests were removed here rather than ported blind; the
hermetic XML-parser coverage below is kept. New integration coverage for
``import_course_member`` is tracked as a follow-up.
"""
from computor_backend.utils.excel_xml_parser import parse_course_member_xml


# Sample XML content for testing
SAMPLE_XML = """<?xml version="1.0" encoding="UTF-8"?>
<?mso-application progid="Excel.Sheet"?>
<ss:Workbook xmlns:ss="urn:schemas-microsoft-com:office:spreadsheet" xmlns:wb="urn:schemas-microsoft-com:office:excel">
  <ss:Worksheet ss:Name="Members">
    <ss:Table>
      <ss:Row>
        <ss:Cell><ss:Data ss:Type="String">E-Mail</ss:Data></ss:Cell>
        <ss:Cell><ss:Data ss:Type="String">Vorname</ss:Data></ss:Cell>
        <ss:Cell><ss:Data ss:Type="String">Familienname</ss:Data></ss:Cell>
        <ss:Cell><ss:Data ss:Type="String">Matrikelnummer</ss:Data></ss:Cell>
        <ss:Cell><ss:Data ss:Type="String">Gruppe</ss:Data></ss:Cell>
      </ss:Row>
      <ss:Row>
        <ss:Cell><ss:Data ss:Type="String">john.doe@example.com</ss:Data></ss:Cell>
        <ss:Cell><ss:Data ss:Type="String">John</ss:Data></ss:Cell>
        <ss:Cell><ss:Data ss:Type="String">Doe</ss:Data></ss:Cell>
        <ss:Cell><ss:Data ss:Type="String">12345</ss:Data></ss:Cell>
        <ss:Cell><ss:Data ss:Type="String">Group A</ss:Data></ss:Cell>
      </ss:Row>
      <ss:Row>
        <ss:Cell><ss:Data ss:Type="String">jane.smith@example.com</ss:Data></ss:Cell>
        <ss:Cell><ss:Data ss:Type="String">Jane</ss:Data></ss:Cell>
        <ss:Cell><ss:Data ss:Type="String">Smith</ss:Data></ss:Cell>
        <ss:Cell><ss:Data ss:Type="String">67890</ss:Data></ss:Cell>
        <ss:Cell><ss:Data ss:Type="String">Group B</ss:Data></ss:Cell>
      </ss:Row>
    </ss:Table>
  </ss:Worksheet>
</ss:Workbook>"""


def test_xml_parser():
    """Test XML parser with sample data."""
    parsed = parse_course_member_xml(SAMPLE_XML)

    assert len(parsed) == 2
    assert parsed[0]['email'] == 'john.doe@example.com'
    assert parsed[0]['given_name'] == 'John'
    assert parsed[0]['family_name'] == 'Doe'
    assert parsed[0]['student_id'] == '12345'
    assert parsed[0]['course_group_title'] == 'Group A'

    assert parsed[1]['email'] == 'jane.smith@example.com'
    assert parsed[1]['given_name'] == 'Jane'
