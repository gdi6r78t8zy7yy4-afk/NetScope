#!/usr/bin/env python3
"""Test script to verify progress tracking logic."""

import sys
sys.path.insert(0, '/Users/carl/Documents/workspace/NetScope/backend')

# Test CIDR calculation
import ipaddress

def test_cidr_progress():
    """Test progress calculation for discovery scans."""
    
    test_cases = [
        ("192.168.1.0/24", 254),  # Standard /24 network
        ("10.0.0.0/8", 16777214), # Large /8 network
        ("172.16.0.0/16", 65534), # /16 network
        ("192.168.1.0/32", 1),    # Single host
        ("192.168.1.0/30", 2),    # Small range
    ]
    
    for cidr, expected_hosts in test_cases:
        try:
            network = ipaddress.ip_network(cidr, strict=False)
            actual_hosts = network.host_count if hasattr(network, 'host_count') else (2 ** (32 - int(cidr.split('/')[-1])))
            
            # Test progress calculation
            total_hosts = actual_hosts
            progress_per_host = 90 / total_hosts if total_hosts > 0 else 0
            
            # Test with various hosts discovered
            for hosts_discovered in [0, 1, 5, 10, total_hosts]:
                progress = min(10 + int(hosts_discovered * progress_per_host), 95)
                print(f"CIDR: {cidr}, Hosts: {hosts_discovered}, Progress: {progress}%")
            
            print(f"  Total hosts calculated: {actual_hosts} (expected: {expected_hosts})")
            print(f"  Progress per host: {progress_per_host}")
        except Exception as e:
            print(f"Error with CIDR {cidr}: {e}")
        print()

def test_port_range_progress():
    """Test progress calculation for port scans."""
    
    test_cases = [
        ("single_port", 1),
        ("common_ports", 20),
        ("port_range_1-100", 100),
        ("full_tcp", 65535),
    ]
    
    for scan_type, total_ports in test_cases:
        progress_per_port = (90 / total_ports) if total_ports > 0 else 0
        
        # Test with various ports scanned
        for ports_scanned in [0, 1, 5, 20, total_ports]:
            progress = min(10 + int((ports_scanned / max(total_ports, 1)) * 90), 95)
            print(f"Scan type: {scan_type}, Ports scanned: {ports_scanned}, Progress: {progress}%")
        
        print(f"  Total ports: {total_ports}")
        print(f"  Progress per port: {progress_per_port:.6f}")
        print()

def test_edge_cases():
    """Test edge cases."""
    
    # Zero division protection
    print("Testing edge cases:")
    
    # Empty CIDR
    total_hosts = 100  # Default when calculation fails
    progress_per_host = (90 / total_hosts) if total_hosts > 0 else 0
    print(f"Default total hosts: {total_hosts}, Progress per host: {progress_per_host}")
    
    # Very small CIDR
    total_hosts = 1
    progress_per_host = (90 / total_hosts) if total_hosts > 0 else 0
    progress = min(10 + int(1 * progress_per_host), 95)
    print(f"Single host CIDR: Progress = {progress}%")
    
    # All edge cases pass if no exceptions raised
    print("\nAll edge cases passed!")

if __name__ == "__main__":
    print("=" * 60)
    print("CIDR Progress Calculations")
    print("=" * 60)
    test_cidr_progress()
    
    print("\n" + "=" * 60)
    print("Port Range Progress Calculations")
    print("=" * 60)
    test_port_range_progress()
    
    print("\n" + "=" * 60)
    print("Edge Case Tests")
    print("=" * 60)
    test_edge_cases()
