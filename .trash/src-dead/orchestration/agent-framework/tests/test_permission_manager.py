import unittest
import json
import os
from src.permission_manager import PermissionManager

class TestPermissionManager(unittest.TestCase):
    
    def setUp(self):
        self.test_permissions_path = "tests/test_permissions.json"
        # Create test permissions file
        permissions_data = {
            "roles": {
                "user": {
                    "permissions": ["file:read", "memory:read"],
                    "deny": ["file:write"]
                },
                "admin": {
                    "permissions": ["file:read", "file:write", "memory:read", "memory:write"],
                    "deny": []
                }
            },
            "rules": [
                {
                    "name": "test_rule",
                    "pattern": "^test.*",
                    "action": "allow",
                    "role": "user"
                }
            ],
            "defaults": {
                "role": "user",
                "action": "prompt",
                "timeout": 300
            }
        }
        with open(self.test_permissions_path, 'w') as f:
            json.dump(permissions_data, f)
    
    def tearDown(self):
        if os.path.exists(self.test_permissions_path):
            os.remove(self.test_permissions_path)
    
    def test_check_permission(self):
        """Test permission checking."""
        pm = PermissionManager(self.test_permissions_path)
        
        # User should be able to read but not write
        self.assertTrue(pm.check_permission("user", "file:read"))
        self.assertFalse(pm.check_permission("user", "file:write"))
        
        # Admin should be able to do both
        self.assertTrue(pm.check_permission("admin", "file:read"))
        self.assertTrue(pm.check_permission("admin", "file:write"))
    
    def test_evaluate_rule(self):
        """Test rule evaluation."""
        pm = PermissionManager(self.test_permissions_path)
        
        # Test command matching rule
        result = pm.evaluate_rule("test command", "user")
        self.assertEqual(result, "allow")
        
        # Test command not matching any rule
        result = pm.evaluate_rule("other command", "user")
        self.assertEqual(result, "prompt")  # Default action
    
    def test_default_role(self):
        """Test getting default role."""
        pm = PermissionManager(self.test_permissions_path)
        self.assertEqual(pm.get_default_role(), "user")

if __name__ == '__main__':
    unittest.main()
