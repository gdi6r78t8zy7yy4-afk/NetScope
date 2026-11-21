# NetScope Export Utilities

"""
Export functionality for scan results and asset data.
"""

import csv
import json
from datetime import datetime
from io import StringIO

# Supported export formats
SUPPORTED_FORMATS = ["csv", "json", "pdf"]


def validate_export_format(format: str) -> bool:
    """
    Validate export format is supported.

    Args:
        format: File format to validate

    Returns:
        bool: True if format is supported, False otherwise
    """
    return format.lower() in SUPPORTED_FORMATS


def validate_export_data(data) -> bool:
    """
    Validate export data structure.

    Args:
        data: Data to validate

    Returns:
        bool: True if valid, False otherwise
    """
    if data is None:
        return False

    if not isinstance(data, (dict, list)):
        return False

    return True


def validate_export_parameters(format: str, data) -> tuple:
    """
    Validate export format and data.

    Args:
        format: Export format (csv, json, pdf)
        data: Data to export

    Returns:
        tuple: (is_valid, error_message)
    """
    # Validate format
    if not validate_export_format(format):
        return False, (
            f"Invalid export format: '{format}'. "
            f"Supported formats: {', '.join(SUPPORTED_FORMATS)}"
        )

    # Validate data
    if not validate_export_data(data):
        return False, "Invalid export data: expected dict or list"

    # Validate non-empty data for CSV and PDF
    if format in ["csv", "pdf"]:
        if isinstance(data, list) and len(data) == 0:
            return False, "Cannot export empty data"
        if isinstance(data, dict) and len(data) == 0:
            return False, "Cannot export empty data"

    return True, None


def export_to_csv(data, fields=None) -> str:
    """
    Export data to CSV format.

    Args:
        data: List of dicts or single dict
        fields: Optional list of field names to include

    Returns:
        CSV string
    """
    if not validate_export_data(data):
        raise ValueError("Invalid data for export")

    output = StringIO()

    # Handle single item
    if isinstance(data, dict):
        data = [data]

    # Determine fields from first record
    if fields is None:
        if len(data) > 0:
            fields = list(data[0].keys())
        else:
            fields = []

    # Write CSV
    writer = csv.DictWriter(output, fieldnames=fields)
    writer.writeheader()

    for row in data:
        # Convert values to strings
        cleaned_row = {}
        for field in fields:
            value = row.get(field, "")
            if isinstance(value, (list, dict)):
                cleaned_row[field] = json.dumps(value)
            else:
                cleaned_row[field] = str(value) if value is not None else ""
        writer.writerow(cleaned_row)

    return output.getvalue()


def export_to_json(data) -> str:
    """
    Export data to JSON format.

    Args:
        data: Data to export

    Returns:
        JSON string
    """
    if not validate_export_data(data):
        raise ValueError("Invalid data for export")

    # Convert datetime objects to strings
    def convert_datetime(obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        elif isinstance(obj, dict):
            return {k: convert_datetime(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [convert_datetime(item) for item in obj]
        return obj

    cleaned_data = convert_datetime(data)

    return json.dumps(cleaned_data, indent=2)


def generate_pdf_report(report_data) -> bytes:
    """
    Generate a PDF report.

    Args:
        report_data: Report content dictionary

    Returns:
        PDF bytes
    """
    if not validate_export_data(report_data):
        raise ValueError("Invalid report data")

    # Basic PDF structure (minimal valid PDF)
    pdf_content = """%PDF-1.4
1 0 obj
<<
/Type /Catalog
/Pages 2 0 R
>>
endobj

2 0 obj
<<
/Type /Pages
/Kids [3 0 R]
/Count 1
>>
endobj

3 0 obj
<<
/Type /Page
/Parent 2 0 R
/Resources <<
/Font << /F1 << /Type /Font /Subtype /Helvetica >> >>
/MediaBox [0 0 612 792]
>>
/Contents 4 0 R
>>
endobj

4 0 obj
<< /Length 100 >>
stream
BT
/F1 12 Tf
0 756 Td
(Scan Report) Tj
ET
endstream
endobj

xref
0 5
0000000000 65535 f
0000000010 00000 n
0000000059 00000 n
0000000113 00000 n
0000000246 00000 n
trailer
<<
/Size 5
/Root 1 0 R
>>
startxref
368
%%EOF"""

    # Add actual content if provided
    if isinstance(report_data, dict) and report_data.get("title"):
        title = report_data["title"]
        content_line = f"({title}) Tj"
        pdf_content = pdf_content.replace("(Scan Report) Tj", content_line)

    return pdf_content.encode("latin-1")


def format_timestamp(timestamp) -> str:
    """
    Format timestamp for export.

    Args:
        timestamp: datetime object or string

    Returns:
        Formatted string
    """
    if isinstance(timestamp, datetime):
        return timestamp.strftime("%Y-%m-%d %H:%M:%S")
    elif isinstance(timestamp, str):
        return timestamp
    else:
        return ""


def create_export_filename(base_name: str, format: str) -> str:
    """
    Create export filename with timestamp.

    Args:
        base_name: Base name for file
        format: File extension

    Returns:
        Complete filename
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"{base_name}_{timestamp}.{format}"
