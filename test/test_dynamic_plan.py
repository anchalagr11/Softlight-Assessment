import sys
import os
import pytest
import logging
from unittest.mock import MagicMock, patch

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Add src to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../src")))

from agents.orchestrator_agent import OrchestratorAgent
from llm.llm_client import LLMClient

@pytest.fixture
def mock_llm_client():
    with patch("agents.orchestrator_agent.LLMClient") as MockClient:
        client_instance = MockClient.return_value
        yield client_instance

def test_linear_plan(mock_llm_client):
    logger.info("----------------------------------------------------------------")
    logger.info("TEST: Linear Plan Generation")
    logger.info("Task: Rename project Alpha to Beta in Linear")
    
    agent = OrchestratorAgent()
    
    # Mock LLM response for Linear task
    mock_llm_client.plan.return_value = [
        {"action": "navigate", "value": "https://linear.app/"},
        {"action": "click", "selector": "text=Projects"}
    ]
    
    plan = agent.create_plan("Rename project Alpha to Beta in Linear")
    
    assert plan.planning_success
    assert len(plan.steps) == 2
    assert plan.steps[0].action == "navigate"
    assert plan.steps[0].value == "https://linear.app/"
    assert plan.steps[1].action == "click"
    
    logger.info("✅ Linear plan verification passed.")

def test_notion_plan(mock_llm_client):
    logger.info("----------------------------------------------------------------")
    logger.info("TEST: Notion Plan Generation")
    logger.info("Task: Create a new page in Notion")
    
    agent = OrchestratorAgent()
    
    # Mock LLM response for Notion task
    mock_llm_client.plan.return_value = [
        {"action": "navigate", "value": "https://www.notion.so/"},
        {"action": "click", "selector": "text=New Page"}
    ]
    
    plan = agent.create_plan("Create a new page in Notion")
    
    assert plan.planning_success
    assert len(plan.steps) == 2
    assert plan.steps[0].action == "navigate"
    assert plan.steps[0].value == "https://www.notion.so/"
    
    logger.info("✅ Notion plan verification passed.")

def test_asana_plan(mock_llm_client):
    logger.info("----------------------------------------------------------------")
    logger.info("TEST: Asana Plan Generation")
    logger.info("Task: Check my tasks in Asana")
    
    agent = OrchestratorAgent()
    
    # Mock LLM response for Asana task
    mock_llm_client.plan.return_value = [
        {"action": "navigate", "value": "https://app.asana.com/"},
        {"action": "click", "selector": "text=My Tasks"}
    ]
    
    plan = agent.create_plan("Check my tasks in Asana")
    
    assert plan.planning_success
    assert len(plan.steps) == 2
    assert plan.steps[0].action == "navigate"
    assert plan.steps[0].value == "https://app.asana.com/"
    
    logger.info("✅ Asana plan verification passed.")

def test_youtube_plan(mock_llm_client):
    logger.info("----------------------------------------------------------------")
    logger.info("TEST: YouTube Plan Generation")
    logger.info("Task: Search for 'funny cats' on YouTube")
    
    agent = OrchestratorAgent()
    
    # Mock LLM response for YouTube task
    mock_llm_client.plan.return_value = [
        {"action": "navigate", "value": "https://www.youtube.com/"},
        {"action": "type", "selector": "input[name='search_query']", "value": "funny cats"},
        {"action": "click", "selector": "button[id='search-icon-legacy']"}
    ]
    
    plan = agent.create_plan("Search for 'funny cats' on YouTube")
    
    assert plan.planning_success
    assert len(plan.steps) == 3
    assert plan.steps[0].action == "navigate"
    assert plan.steps[0].value == "https://www.youtube.com/"
    
    logger.info("✅ YouTube plan verification passed.")

def test_google_docs_plan(mock_llm_client):
    logger.info("----------------------------------------------------------------")
    logger.info("TEST: Google Docs Plan Generation")
    logger.info("Task: Open a new blank document")
    
    agent = OrchestratorAgent()
    
    # Mock LLM response for Google Docs task
    mock_llm_client.plan.return_value = [
        {"action": "navigate", "value": "https://docs.google.com/"},
        {"action": "click", "selector": "text=Blank"}
    ]
    
    plan = agent.create_plan("Open a new blank document")
    
    assert plan.planning_success
    assert len(plan.steps) == 2
    assert plan.steps[0].action == "navigate"
    assert plan.steps[0].value == "https://docs.google.com/"
    
    logger.info("✅ Google Docs plan verification passed.")
