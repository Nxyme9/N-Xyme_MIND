import unittest
from ..src.router import Router
import os

class TestRouter(unittest.TestCase):
    
    def setUp(self):
        # Use the actual agent configs directory for testing
        self.router = Router("../../configs/opencode/agents")
    
    def test_load_agents(self):
        """Test loading agents from directory."""
        agents = self.router.agents
        # Should have at least the 8 agents we created
        self.assertGreaterEqual(len(agents), 8)
        
        # Check specific agents
        self.assertIn("prometheus", agents)
        self.assertIn("security", agents)
        self.assertIn("planner", agents)
    
    def test_route_task(self):
        """Test task routing."""
        # Test memory-related task should go to oracle
        agent = self.router.route_task("search memory for previous conversations")
        self.assertEqual(agent.get_name(), "oracle")
        
        # Test security task should go to security
        agent = self.router.route_task("analyze this command for security risks")
        self.assertEqual(agent.get_name(), "security")
        
        # Test capture task should go to sisyphus
        agent = self.router.route_task("record voice note")
        self.assertEqual(agent.get_name(), "sisyphus")
    
    def test_get_agent_by_name(self):
        """Test getting specific agent."""
        agent = self.router.get_agent_by_name("planner")
        self.assertIsNotNone(agent)
        self.assertEqual(agent.get_name(), "planner")

if __name__ == '__main__':
    unittest.main()
