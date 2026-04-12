"""
CrewAI Agents — six specialized agents forming the intelligence pipeline.

Each agent gets a fresh LLM instance with the next available Groq API key,
enabling automatic key rotation across the 9-key pool on rate limits.
"""
import os
from crewai import Agent, LLM
from dotenv import load_dotenv

from .tools import (
    github_monitor_tool,
    deep_scrape_tool,
    slack_alert_tool,
    hackernews_signal_tool,
    pypi_stats_tool,
    memory_query_tool,
)
from .key_manager import get_next_key

load_dotenv()


def _model_profile() -> str:
    """Return the active model profile for the current run."""
    return os.getenv("OVERWATCH_MODEL_PROFILE", "balanced").strip().lower()


def _get_llm(role_tier: str = "core"):
    """Create an LLM instance with a profile-aware Groq model choice.

    Profiles:
    - balanced: fast model for tool-heavy support agents, strong model for core synthesis
    - fast: fast model for all agents to improve demo reliability under free-tier limits
    """
    high_model = os.getenv("OVERWATCH_HIGH_MODEL", "groq/llama-3.3-70b-versatile")
    fast_model = os.getenv("OVERWATCH_FAST_MODEL", "groq/llama-3.1-8b-instant")
    profile = _model_profile()

    model = high_model
    if profile == "fast":
        model = fast_model
    elif profile == "balanced" and role_tier == "support":
        model = fast_model

    return LLM(
        model=model,
        api_key=get_next_key("GROQ"),
    )


def _agent_limits(max_iter: int, max_execution_time: int) -> dict:
    """Shared execution limits to reduce token churn and tool looping."""
    return {
        "max_iter": max_iter,
        "max_execution_time": max_execution_time,
        "allow_delegation": False,
    }


def monitor_agent() -> Agent:
    """Agent that monitors GitHub repos for new commits and changes."""
    use_prefetched_monitor = os.getenv("OVERWATCH_PREFETCH_MONITOR", "0") == "1"
    return Agent(
        role="GitHub Repository Monitor",
        goal="Detect new architectural changes in target repositories.",
        backstory="You are an expert software engineer who maps dependency trees and detects breaking changes.",
        tools=[] if use_prefetched_monitor else [github_monitor_tool],
        verbose=True,
        llm=_get_llm(role_tier="support"),
        **_agent_limits(max_iter=1, max_execution_time=30),
    )


def signal_analyst_agent() -> Agent:
    """Agent that gathers ecosystem signals from HN and PyPI."""
    use_prefetched_signal = os.getenv("OVERWATCH_PREFETCH_SIGNAL", "0") == "1"
    return Agent(
        role="Signal Analyst",
        goal="Gather ecosystem intelligence from HackerNews and PyPI.",
        backstory="You monitor industry adoption velocities and community sentiment shifts.",
        tools=[] if use_prefetched_signal else [hackernews_signal_tool, pypi_stats_tool],
        verbose=True,
        llm=_get_llm(role_tier="support"),
        **_agent_limits(max_iter=2, max_execution_time=45),
    )


def researcher_agent() -> Agent:
    """Agent that deep-scrapes documentation and PR discussions."""
    use_prefetched_research = os.getenv("OVERWATCH_PREFETCH_RESEARCH", "0") == "1"
    return Agent(
        role="Deep Scrape Researcher",
        goal="Read the actual code changes, PR discussions, and release notes.",
        backstory="You dive deep into raw diffs and documentation to find architectural shifts.",
        tools=[] if use_prefetched_research else [deep_scrape_tool],
        verbose=True,
        llm=_get_llm(role_tier="support"),
        **_agent_limits(max_iter=2, max_execution_time=45),
    )


def analyst_agent() -> Agent:
    """Agent that synthesizes research into a structured briefing."""
    use_prefetched_memory = os.getenv("OVERWATCH_PREFETCH_MEMORY", "0") == "1"
    return Agent(
        role="Intelligence Analyst",
        goal="Synthesize raw research data into a structured intelligence briefing.",
        backstory="You use MemoryQueryTool to find historical pivots and synthesize cross-signal context.",
        tools=[] if use_prefetched_memory else [memory_query_tool],
        verbose=True,
        llm=_get_llm(role_tier="core"),
        **_agent_limits(max_iter=2, max_execution_time=50),
    )


def red_team_agent() -> Agent:
    """Adversarial reviewer that challenges unsupported claims.

    This agent strengthens report grounding by:
    - Attacking vague or generic architecture claims
    - Flagging statements not traceable to evidence
    - Requesting retry when grounding is insufficient
    """
    return Agent(
        role="Red Team Reviewer",
        goal="Challenge every claim in the analysis. Reject anything not supported by concrete evidence.",
        backstory=(
            "You are a skeptical adversarial reviewer. Your job is to find weak spots, "
            "unsupported claims, and generic statements. You do NOT accept vague architecture "
            "changes like 'improved performance' without specific evidence. You force the team "
            "to either cite concrete proof or remove the claim."
        ),
        verbose=True,
        llm=_get_llm(role_tier="support"),
        **_agent_limits(max_iter=2, max_execution_time=35),
    )


def verifier_agent() -> Agent:
    """Agent that validates the final report against quality schemas."""
    return Agent(
        role="Fact Verifier",
        goal="Ensure the final report meets strict quality schemas with cited sources.",
        backstory="You validate confidence scores, citation integrity, and architectural claim accuracy.",
        verbose=True,
        llm=_get_llm(role_tier="core"),
        **_agent_limits(max_iter=2, max_execution_time=35),
    )
