#!/usr/bin/env python3
"""
Quick MIDI port test - just lists available ports and tests connection
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

import mido
import yaml

def quick_test():
    print("🎹 Quick MIDI Input Test")
    print("=" * 30)
    
    # List available ports
    print("📋 Available MIDI Input Ports:")
    try:
        ports = mido.get_input_names()
        if not ports:
            print("   ❌ No MIDI input ports found!")
            return False
        
        for i, port in enumerate(ports, 1):
            print(f"   {i}. {port}")
        
    except Exception as e:
        print(f"   ❌ Error listing ports: {e}")
        return False
    
    # Load config
    print(f"\n📋 Configuration:")
    try:
        with open('config.yaml', 'r') as f:
            config = yaml.safe_load(f)
        
        input_port = config.get('midi', {}).get('input_port', 'auto')
        input_channel = config.get('midi', {}).get('input_channel', 1)
        
        print(f"   Input Port: {input_port}")
        print(f"   Input Channel: {input_channel}")
        
    except Exception as e:
        print(f"   ⚠️  Could not load config: {e}")
        input_port = 'auto'
    
    # Test connection
    print(f"\n🔌 Testing Connection to '{input_port}':")
    try:
        if input_port == 'auto':
            if ports:
                test_port = ports[0]
                print(f"   Auto-selecting: {test_port}")
            else:
                print("   ❌ No ports available for auto-selection")
                return False
        else:
            test_port = input_port
        
        # Try to open and immediately close
        with mido.open_input(test_port) as port:
            print(f"   ✅ Successfully connected to: {test_port}")
            print(f"   ✅ Connection test passed!")
            return True
            
    except Exception as e:
        print(f"   ❌ Connection failed: {e}")
        
        # Try first available port as fallback
        if input_port != 'auto' and ports:
            print(f"   🔄 Trying fallback: {ports[0]}")
            try:
                with mido.open_input(ports[0]) as port:
                    print(f"   ✅ Fallback connection successful!")
                    print(f"   💡 Consider updating config to use: {ports[0]}")
                    return True
            except Exception as e2:
                print(f"   ❌ Fallback also failed: {e2}")
        
        return False

if __name__ == "__main__":
    success = quick_test()
    if success:
        print(f"\n🎯 Ready to run full debug script:")
        print(f"   /Users/oberon/Projects/coding/other/SoundForgeEngine/rpi-engine/.venv/bin/python debug_midi_input.py")
    else:
        print(f"\n❌ MIDI input issues detected - check your MIDI setup")
    
    sys.exit(0 if success else 1)
