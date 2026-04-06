import unittest
from ..src.agent_config import AgentConfig
import os

class TestAgentConfig(unittest.TestCase):
    
    def setUp(self):
        self.test_config_path = "tests/test_agent.yaml"
        # Create a test config file
        with open(self.test_config_path, 'w') as f:
            f.write("""
name: test_agent
description: Test agent for unit tests
type: test
version: 1.0.0
author: Test
capabilities:
  - test_capability
config:
  test_setting: value
permissions:
  - test:permission
skills:
  - name: test_skill
    description: Test skill description
""")
    
    def tearDown(self):
        if os.path.exists(self.test_config_path):
            os.remove(self.test_config_path)
    
    def test_load_config(self):
        """Test loading an agent configuration."""
        config = AgentConfig.load(self.test_config_path)
        self.assertEqual(config.get_name(), "test_agent")
        self.assertEqual(config.get_type(), "test")
        self.assertIn("test_capability", config.get_capabilities())
    
    def test_invalid_config(self):
        """Test that invalid config raises error."""
        # Create invalid config
        invalid_path = "tests/invalid.yaml"
        with open(invalid_path, 'w') as f:
            f.write("name: invalid\n")  # Missing required fields
        
        try:
            with self.assertRaises(ValueError):
                AgentConfig.load(invalid_path)
        finally:
            if os.path.exists(invalid_path):
                os.remove(invalid_path)

if __name__ == '__main__':
    unittest.main()
