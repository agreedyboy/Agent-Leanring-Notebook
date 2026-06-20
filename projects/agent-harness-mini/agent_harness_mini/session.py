# 简单记忆管理
from typing import Any
from dataclasses import dataclass, field
from datetime import datetime, timezone
import uuid

# 创建一个新的会话id
def new_session_id()->str:
    return uuid.uuid4().hex

# 返回当前时间戳
def utc_now()->str:
    return datetime.now(timezone.utc).isoformat()

@dataclass
class AgentSession:
    """
    管理一次会话的 messages 和基础元信息
    不负责调用模型，不负责执行工具，也不负责 trace。它只管“当前对话状态”
    """
    session_id: str
    messages: list[dict[str, Any]] = field(default_factory=list)
    created_at: str = field(default_factory=utc_now)
    updated_at: str = field(default_factory=utc_now)
    metadata: dict[str, Any] = field(default_factory=dict)

    # 创建一个新会话
    @classmethod
    def create(cls, system_prompt: str | None = None)->"AgentSession":
        session = cls(session_id = new_session_id())

        if system_prompt is not None:
            session.add_system_message(system_prompt)
        
        return session
    
    @classmethod
    def from_messages(
        cls,
        messages: list[dict[str, Any]],
        metadata: dict[str, Any] | None = None,
    ) -> "AgentSession":
        return cls(
            session_id=new_session_id(),
            messages=list(messages),
            metadata=metadata or {},
        )
    
    # 添加message并跟新最新修改时间
    def add_message(self, message: dict[str, Any])->None:
        self.messages.append(message)
        self.updated_at = utc_now()
        return
    
    # 添加系统消息
    def add_system_message(self, content: dict[str, str] | str)->None:

        if isinstance(content, dict):
            self.add_message(content)
        else:
            self.add_message({"role": "system", "content": content})
        return
    
    # 添加用户消息
    def add_user_message(self, content: dict[str, str] | str)->None:
        if isinstance(content, dict):
            self.add_message(content)
        else:
            self.add_message({"role": "user", "content": content})

    
    def add_assistant_message(self, message: dict[str, Any]) -> None:
        self.add_message(message)

    def add_tool_message(self, message: dict[str, Any]) -> None:
        self.add_message(message)

    def to_model_messages(self)->list[dict[str, Any]]:
        return list(self.messages)

    def to_model_message(self)->list[dict[str, Any]]:
        return self.to_model_messages()
    
    # 返回一个当前会话记录的快照
    def snapshot(self)->dict[str, Any]:
        return {
            "session_id": self.session_id,
            "messages": list(self.messages),
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "metadata": self.metadata,
        }
    
@dataclass(frozen=True)
class AgentRunResult:
    """
    表达一次 run_agent() 的最终运行结果
    """
    run_id: str
    session_id: str
    status: str
    output: str | None
    steps: int
    latency_ms: int
    error_type: str | None = None
    message: str | None = None

    @property
    def ok(self) -> bool:
        return self.status == "completed"

def build_session(system_prompt: str, prompt: str) -> AgentSession:
    session = AgentSession.create(system_prompt)
    session.add_user_message(prompt)
    return session