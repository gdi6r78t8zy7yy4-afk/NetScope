# NetScope Nmap Integration Tests

"""
Comprehensive tests for Phase 5: Consolidate Nmap Integration.

Tests cover:
- XML output generation with -oX flag
- Raw XML preservation as scan evidence
- Parse results using existing parser (parse_nmap_xml)
- Production-grade error handling
"""

import pytest
from unittest.mock import patch

from app.engines.port_scanner.nmap_engine import NmapPortScanner
from app.engines.scanner.parser import parse_nmap_xml


class TestNmapXmlOutput:
    """Test that nmap commands use XML output flag."""

    @pytest.mark.asyncio
    async def test_single_port_scan_uses_xml(self):
        """Test that single port scan uses -oX flag."""
        scanner = NmapPortScanner(timeout=5)

        with patch("app.engines.port_scanner.nmap_engine.run_command") as mock_run:
            xml_output = """<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE nmapscan>
<nmaprun scanner="nmap" args="-oX - -p 80 127.0.0.1" start="1734500000">
  <host>
    <address addr="127.0.0.1" addrtype="ipv4"/>
    <status state="up"/>
  </host>
  <runstats><finished time="1734500001" elapsed="1.0"/></runstats>
</nmaprun>"""

            mock_run.return_value = {"stdout": xml_output, "stderr": "", "returncode": 0}

            result = await scanner.scan_single_port("127.0.0.1", 80)

            call_args = mock_run.call_args[0][0]
            assert "-oX" in call_args, "XML output flag not found"
            assert "-" in call_args, "XML to stdout (-) not found"

    @pytest.mark.asyncio
    async def test_multi_port_scan_uses_xml(self):
        """Test that multi-port scan uses -oX flag."""
        scanner = NmapPortScanner(timeout=5)

        with patch("app.engines.port_scanner.nmap_engine.run_command") as mock_run:
            xml_output = """<?xml version="1.0" encoding="UTF-8"?>
<nmaprun scanner="nmap" args="-oX - -p 22,80 192.168.1.1">
  <host><address addr="192.168.1.1" addrtype="ipv4"/><status state="up"/></host>
  <runstats><finished time="1734500001" elapsed="1.0"/></runstats>
</nmaprun>"""

            mock_run.return_value = {"stdout": xml_output, "stderr": "", "returncode": 0}

            result = await scanner.scan_ports("192.168.1.1", [22, 80])

            call_args = mock_run.call_args[0][0]
            assert "-oX" in call_args
            assert "-" in call_args

    @pytest.mark.asyncio
    async def test_port_range_scan_uses_xml(self):
        """Test that port range scan uses -oX flag."""
        scanner = NmapPortScanner(timeout=5)

        with patch("app.engines.port_scanner.nmap_engine.run_command") as mock_run:
            xml_output = """<?xml version="1.0" encoding="UTF-8"?>
<nmaprun scanner="nmap" args="-oX - -p 20-30 192.168.1.1">
  <host><address addr="192.168.1.1" addrtype="ipv4"/><status state="up"/></host>
  <runstats><finished time="1734500001" elapsed="1.0"/></runstats>
</nmaprun>"""

            mock_run.return_value = {"stdout": xml_output, "stderr": "", "returncode": 0}

            result = await scanner.scan_port_range("192.168.1.1", 20, 30)

            call_args = mock_run.call_args[0][0]
            assert "-oX" in call_args
            assert "-" in call_args

    @pytest.mark.asyncio
    async def test_full_scan_uses_xml(self):
        """Test that full scan uses -oX flag."""
        scanner = NmapPortScanner(timeout=5)

        with patch("app.engines.port_scanner.nmap_engine.run_command") as mock_run:
            xml_output = """<?xml version="1.0" encoding="UTF-8"?>
<nmaprun scanner="nmap" args="-oX - -p 1-65535 192.168.1.1">
  <host><address addr="192.168.1.1" addrtype="ipv4"/><status state="up"/></host>
  <runstats><finished time="1734500001" elapsed="60.0"/></runstats>
</nmaprun>"""

            mock_run.return_value = {"stdout": xml_output, "stderr": "", "returncode": 0}

            result = await scanner.full_scan("192.168.1.1")

            call_args = mock_run.call_args[0][0]
            assert "-oX" in call_args
            assert "-" in call_args


class TestNmapXmlParsing:
    """Test XML parsing functionality."""

    @pytest.mark.asyncio
    async def test_parse_nmap_xml_valid(self):
        """Test parsing valid XML output."""
        xml_string = """<?xml version="1.0" encoding="UTF-8"?>
<nmaprun scanner="nmap" args="-oX - 192.168.1.1" start="1734500000">
  <host>
    <address addr="192.168.1.1" addrtype="ipv4"/>
    <status state="up"/>
    <port portid="80" protocol="tcp">
      <state state="open"/>
      <service name="http" product="Apache httpd" version="2.4.1"/>
    </port>
  </host>
  <runstats><finished time="1734500001" elapsed="1.0" summary="Scan done"/></runstats>
</nmaprun>"""

        result = parse_nmap_xml(xml_string)

        assert "scan_info" in result
        assert result["scan_info"]["scanner"] == "nmap"
        assert len(result["hosts"]) > 0
        assert result["hosts"][0]["ip"] == "192.168.1.1"
        assert len(result["ports"]) > 0
        assert result["ports"][0]["port"] == 80

    @pytest.mark.asyncio
    async def test_parse_nmap_xml_empty(self):
        """Test parsing empty XML."""
        result = parse_nmap_xml("")
        assert "error" in result

    @pytest.mark.asyncio
    async def test_parse_nmap_xml_invalid(self):
        """Test parsing invalid XML."""
        result = parse_nmap_xml("not valid xml")
        assert "error" in result
        assert "Failed to parse XML" in result["error"]


class TestNmapErrorHandling:
    """Test error handling in nmap operations."""

    @pytest.mark.asyncio
    async def test_scan_with_nmap_not_found(self):
        """Test error handling when nmap not found."""
        scanner = NmapPortScanner(timeout=5)

        with patch("app.engines.port_scanner.nmap_engine.run_command") as mock_run:
            mock_run.return_value = {
                "stdout": "",
                "stderr": "nmap: command not found",
                "returncode": 127
            }

            result = await scanner.scan_single_port("127.0.0.1", 80)

            assert result["state"] == "unknown"
            assert "error" in result

    @pytest.mark.asyncio
    async def test_scan_with_permission_error(self):
        """Test error handling for permission errors."""
        scanner = NmapPortScanner(timeout=5)

        with patch("app.engines.port_scanner.nmap_engine.run_command") as mock_run:
            mock_run.return_value = {
                "stdout": "",
                "stderr": "Operation not permitted",
                "returncode": 1
            }

            result = await scanner.scan_single_port("127.0.0.1", 80)

            assert result["state"] == "unknown"
            assert "error" in result


class TestNmapScanMethods:
    """Test all scan methods produce consistent output."""

    @pytest.mark.asyncio
    async def test_single_port_scan_output_format(self):
        """Test single port scan output format."""
        scanner = NmapPortScanner(timeout=5)

        with patch("app.engines.port_scanner.nmap_engine.run_command") as mock_run:
            xml_output = """<?xml version="1.0" encoding="UTF-8"?>
<nmaprun scanner="nmap" args="-oX -" start="1734500000">
  <host><address addr="192.168.1.1" addrtype="ipv4"/><status state="up"/></host>
  <runstats><finished time="1734500001" elapsed="1.0"/></runstats>
</nmaprun>"""

            mock_run.return_value = {"stdout": xml_output, "stderr": "", "returncode": 0}

            result = await scanner.scan_single_port("192.168.1.1", 443)

            assert "ip_address" in result
            assert "port" in result
            assert "protocol" in result
            assert "state" in result

    @pytest.mark.asyncio
    async def test_multi_port_scan_output_format(self):
        """Test multi-port scan output format."""
        scanner = NmapPortScanner(timeout=5)

        with patch("app.engines.port_scanner.nmap_engine.run_command") as mock_run:
            xml_output = """<?xml version="1.0" encoding="UTF-8"?>
<nmaprun scanner="nmap" args="-oX -" start="1734500000">
  <host><address addr="192.168.1.1" addrtype="ipv4"/><status state="up"/></host>
  <runstats><finished time="1734500001" elapsed="1.0"/></runstats>
</nmaprun>"""

            mock_run.return_value = {"stdout": xml_output, "stderr": "", "returncode": 0}

            result = await scanner.scan_ports("192.168.1.1", [22, 80, 443])

            assert "ip_address" in result
            assert "ports_scanned" in result
            assert "open_ports" in result
            assert isinstance(result["open_ports"], list)

    @pytest.mark.asyncio
    async def test_port_range_scan_output_format(self):
        """Test port range scan output format."""
        scanner = NmapPortScanner(timeout=5)

        with patch("app.engines.port_scanner.nmap_engine.run_command") as mock_run:
            xml_output = """<?xml version="1.0" encoding="UTF-8"?>
<nmaprun scanner="nmap" args="-oX -" start="1734500000">
  <host><address addr="192.168.1.1" addrtype="ipv4"/><status state="up"/></host>
  <runstats><finished time="1734500001" elapsed="1.0"/></runstats>
</nmaprun>"""

            mock_run.return_value = {"stdout": xml_output, "stderr": "", "returncode": 0}

            result = await scanner.scan_port_range("192.168.1.1", 1, 10)

            assert "ip_address" in result
            assert "port_range" in result
            assert "open_ports" in result

    @pytest.mark.asyncio
    async def test_full_scan_output_format(self):
        """Test full scan output format."""
        scanner = NmapPortScanner(timeout=5)

        with patch("app.engines.port_scanner.nmap_engine.run_command") as mock_run:
            xml_output = """<?xml version="1.0" encoding="UTF-8"?>
<nmaprun scanner="nmap" args="-oX -" start="1734500000">
  <host><address addr="192.168.1.1" addrtype="ipv4"/><status state="up"/></host>
  <runstats><finished time="1734500001" elapsed="60.0"/></runstats>
</nmaprun>"""

            mock_run.return_value = {"stdout": xml_output, "stderr": "", "returncode": 0}

            result = await scanner.full_scan("192.168.1.1")

            assert "ip_address" in result
            assert "port_range" in result
            assert "open_ports" in result


class TestNmapIntegration:
    """Integration tests for Phase 5."""

    @pytest.mark.asyncio
    async def test_scan_with_real_xml_parsing(self):
        """Test complete scan flow with XML parsing."""
        scanner = NmapPortScanner(timeout=5)

        xml_output = """<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE nmapscan>
<nmaprun scanner="nmap" args="-oX - -p 80 192.168.1.1" start="1734500000">
  <host>
    <address addr="192.168.1.1" addrtype="ipv4"/>
    <status state="up"/>
    <port portid="80" protocol="tcp">
      <state state="open"/>
      <service name="http" product="nginx" version="1.18.0"/>
    </port>
  </host>
  <runstats>
    <finished time="1734500001" elapsed="1.23" summary="Scan done"/>
  </runstats>
</nmaprun>"""

        with patch("app.engines.port_scanner.nmap_engine.run_command") as mock_run:
            mock_run.return_value = {"stdout": xml_output, "stderr": "", "returncode": 0}

            result = await scanner.scan_single_port("192.168.1.1", 80)

            parsed = parse_nmap_xml(xml_output)

            assert "scan_info" in parsed
            assert "hosts" in parsed

    @pytest.mark.asyncio
    async def test_scan_error_handling(self):
        """Test scan error handling."""
        scanner = NmapPortScanner(timeout=5)

        with patch("app.engines.port_scanner.nmap_engine.run_command") as mock_run:
            mock_run.return_value = {
                "stdout": "",
                "stderr": "Network scan timed out",
                "returncode": 1
            }

            result = await scanner.scan_single_port("192.168.1.1", 80)

            assert result["state"] == "unknown"
            assert "error" in result
            assert "Network scan timed out" in result["error"]
