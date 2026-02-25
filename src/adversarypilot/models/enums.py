"""Shared enumerations for all AdversaryPilot domain objects."""

from enum import StrEnum


class TargetType(StrEnum):
    """Type of system being targeted."""

    CLASSIFIER = "classifier"
    CHATBOT = "chatbot"
    RAG = "rag"
    AGENT = "agent"
    MODERATION = "moderation"
    EMBEDDING = "embedding"
    MULTI_AGENT_SYSTEM = "multi_agent_system"
    MCP_CLIENT = "mcp_client"


class AccessLevel(StrEnum):
    """Level of access available to the attacker."""

    WHITE_BOX = "white_box"
    GRAY_BOX = "gray_box"
    BLACK_BOX = "black_box"


class Domain(StrEnum):
    """Attack domain."""

    AML = "aml"
    LLM = "llm"
    AGENT = "agent"


class Phase(StrEnum):
    """Attack lifecycle phase."""

    RECON = "recon"
    PROBE = "probe"
    EXPLOIT = "exploit"
    PERSISTENCE = "persistence"
    EVALUATION = "evaluation"


class Surface(StrEnum):
    """Attack surface / system layer."""

    MODEL = "model"
    DATA = "data"
    RETRIEVAL = "retrieval"
    TOOL = "tool"
    ACTION = "action"
    GUARDRAIL = "guardrail"


class Goal(StrEnum):
    """Attacker objective."""

    EVASION = "evasion"
    JAILBREAK = "jailbreak"
    EXFIL_SIM = "exfil_sim"
    EXTRACTION = "extraction"
    TOOL_MISUSE = "tool_misuse"
    POISONING = "poisoning"
    DOS = "dos"


class ExecutionMode(StrEnum):
    """How the technique is executed."""

    MANUAL = "manual"
    TOOL_ASSISTED = "tool_assisted"
    FULLY_AUTOMATED = "fully_automated"


class StealthLevel(StrEnum):
    """Stealth profile of a technique or constraint priority."""

    OVERT = "overt"
    MODERATE = "moderate"
    COVERT = "covert"


class JudgeType(StrEnum):
    """How success/failure of an attempt is judged."""

    KEYWORD = "keyword"
    CLASSIFIER = "classifier"
    LLM_JUDGE = "llm_judge"
    HUMAN = "human"
    RULE_BASED = "rule_based"


class CampaignPhase(StrEnum):
    """Campaign exploration/exploitation phase."""

    PROBE = "probe"
    EXPLOIT = "exploit"


class CampaignStatus(StrEnum):
    """Campaign lifecycle status."""

    PLANNING = "planning"
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    ABORTED = "aborted"
