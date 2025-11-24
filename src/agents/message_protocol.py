from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class ActionStep(BaseModel):
    action: str = Field(
        ...,
        description=(
            "One of: navigate | click | right_click | type | press | wait_for | wait_for_user | screenshot"
        )
    )
    url: Optional[str] = None
    selector: Optional[str] = None
    value: Optional[str] = None
    name: Optional[str] = None
    api_endpoint: Optional[str] = None     
    api_method: Optional[str] = None       
    payload: Optional[Dict[str, Any]] = None   

    class Config:
        extra = "allow"


class Plan(BaseModel):
    steps: List[ActionStep]
    raw_llm_output: Optional[str] = None  
    model_used: Optional[str] = None
    planning_success: bool = True

class StepExecutionResult(BaseModel):
    step_index: int
    action: str
    success: bool
    state_changed: bool = False
    screenshot_path: Optional[str] = None
    page_url: Optional[str] = None
    error: Optional[str] = None
    details: Dict[str, Any] = Field(default_factory=dict)


class ExecutionResult(BaseModel):
    task: str
    steps: List[StepExecutionResult] = Field(default_factory=list)
    success: bool = True
    error: Optional[str] = None          
    dataset_path: Optional[str] = None

    def mark_failure(self, error_msg: str):
        self.success = False
        self.error = error_msg


class AgentState(BaseModel):
    task: str
    plan: Optional[Plan] = None
    execution: Optional[ExecutionResult] = None
    retry_count: int = 0       
    final: bool = False        
    keep_open: bool = False 
    

    observation: Optional[str] = None  
    is_complete: bool = False          

    class Config:
        arbitrary_types_allowed = True