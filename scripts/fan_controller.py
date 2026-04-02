#!/usr/bin/env python3
"""
Simple Fan Control with Hysteresis for IT8689E (Gigabyte B650 AORUS ELITE AX)
Monitors CPU temperature and provides hysteresis for fan control.
Since the it87 driver doesn't work, this script helps configure BIOS profiles.
"""

import time
import subprocess
import json
import sys
import os

class FanController:
    def __init__(self):
        self.cpu_temp = 0
        self.gpu_temp = 0
        self.hysteresis = 5  # Temperature hysteresis in degrees
        self.last_fan_speed = 0
        self.temp_history = []
        self.max_history = 10
        
    def get_cpu_temp(self):
        """Get CPU temperature from k10temp"""
        try:
            with open('/sys/class/hwmon/hwmon2/temp1_input', 'r') as f:
                temp = int(f.read().strip()) / 1000
                return temp
        except:
            return 0
            
    def get_gpu_temp(self):
        """Get GPU temperature from amdgpu"""
        try:
            with open('/sys/class/hwmon/hwmon6/temp1_input', 'r') as f:
                temp = int(f.read().strip()) / 1000
                return temp
        except:
            return 0
            
    def get_fan_speed_rpm(self):
        """Try to get fan speed from available sensors"""
        fan_speeds = []
        
        # Try to read from various hwmon devices
        for i in range(7):  # hwmon0 to hwmon6
            try:
                with open(f'/sys/class/hwmon/hwmon{i}/fan1_input', 'r') as f:
                    speed = int(f.read().strip())
                    if speed > 0:
                        fan_speeds.append(speed)
            except:
                continue
                
        return fan_speeds if fan_speeds else [0]
        
    def should_change_fan_speed(self, target_temp):
        """Determine if fan speed should change with hysteresis"""
        if len(self.temp_history) < 3:
            return False
            
        avg_temp = sum(self.temp_history[-3:]) / 3
        
        # Check if we're outside the hysteresis range
        if abs(avg_temp - target_temp) > self.hysteresis:
            return True
            
        return False
        
    def update_temp_history(self):
        """Update temperature history"""
        self.temp_history.append(self.cpu_temp)
        if len(self.temp_history) > self.max_history:
            self.temp_history.pop(0)
            
    def monitor_loop(self):
        """Main monitoring loop"""
        print("Fan Controller with Hysteresis")
        print("=" * 50)
        print(f"Hysteresis: {self.hysteresis}°C")
        print("Press Ctrl+C to exit")
        print()
        
        try:
            while True:
                # Update temperatures
                self.cpu_temp = self.get_cpu_temp()
                self.gpu_temp = self.get_gpu_temp()
                fan_speeds = self.get_fan_speed_rpm()
                
                # Update temperature history
                self.update_temp_history()
                
                # Display current status
                print(f"\rCPU: {self.cpu_temp:.1f}°C | GPU: {self.gpu_temp:.1f}°C | Fans: {fan_speeds} RPM", end="")
                
                # Check if we should adjust fan speed
                if self.should_change_fan_speed(70):  # Target temp 70°C
                    print("\n[ACTION] Temperature outside hysteresis range")
                    
                time.sleep(1)
                
        except KeyboardInterrupt:
            print("\n\nExiting...")
            
    def generate_bios_recommendation(self):
        """Generate BIOS fan curve recommendation based on monitoring"""
        if not self.temp_history:
            return
            
        avg_temp = sum(self.temp_history) / len(self.temp_history)
        max_temp = max(self.temp_history)
        min_temp = min(self.temp_history)
        
        print("\n" + "="*50)
        print("BIOS FAN CURVE RECOMMENDATION")
        print("="*50)
        print(f"Average CPU temp: {avg_temp:.1f}°C")
        print(f"Max CPU temp: {max_temp:.1f}°C")
        print(f"Min CPU temp: {min_temp:.1f}°C")
        print(f"Temperature range: {max_temp - min_temp:.1f}°C")
        print()
        print("Recommended BIOS fan curve (for Gigabyte B650 AORUS ELITE AX):")
        print("1. Enter BIOS (Del or F2 during boot)")
        print("2. Go to Smart Fan 6 (or similar)")
        print("3. Configure the following curve:")
        print(f"   - Below {avg_temp:.0f}°C: 30-40% (quiet)")
        print(f"   - {avg_temp:.0f}-{avg_temp+5:.0f}°C: 40-60% (moderate)")
        print(f"   - Above {avg_temp+5:.0f}°C: 60-100% (performance)")
        print("4. Enable 'Fan Hysteresis' if available")
        print("5. Set 'Fan Step Up Time' to 0.5-1.0 seconds")
        print("6. Set 'Fan Step Down Time' to 1.0-2.0 seconds")
        print()
        print("This will prevent rapid fan ramp-ups while keeping your CPU cool.")

if __name__ == "__main__":
    controller = FanController()
    
    if len(sys.argv) > 1 and sys.argv[1] == "--recommend":
        # Generate recommendation without monitoring
        controller.temp_history = [65, 66, 67, 68, 69, 70, 71, 72, 73, 74]  # Sample data
        controller.generate_bios_recommendation()
    else:
        # Start monitoring
        controller.monitor_loop()