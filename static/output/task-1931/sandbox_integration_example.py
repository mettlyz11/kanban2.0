#!/usr/bin/env python3
"""
OpenClaw ACP v2026 - Sandbox Integration Example
Date: 2026-04-25
Task: #1931

This example demonstrates:
1. Creating a sandboxed agent using OpenAI Agents SDK v2026
2. Manifest workspace configuration
3. Capability-based security controls
4. File manipulation within sandbox
5. Shell command execution
6. Checkpoint and restore
"""

import asyncio
import json
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any

from agents import (
    Agent, Runner, SandboxAgent, SandboxRunConfig,
    Manifest, File, LocalDir, S3Mount,
    Capability, Shell, Filesystem, Memory, Network,
    RunConfig, function_tool
)

# Try to import sandbox clients - these are optional dependencies
try:
    from agents import DockerSandboxClient
    DOCKER_AVAILABLE = True
except ImportError:
    DOCKER_AVAILABLE = False

try:
    from agents import UnixLocalSandboxClient
    UNIX_LOCAL_AVAILABLE = True
except ImportError:
    UNIX_LOCAL_AVAILABLE = False


# ============================================
# Section 1: Security Policy and Configuration
# ============================================

class SandboxSecurityPolicy:
    """OpenClaw sandbox security policy configuration"""
    
    # Default resource quotas
    DEFAULT_CPU: float = 2.0          # vCPUs
    DEFAULT_MEMORY: str = "4g"        # Memory
    DEFAULT_DISK: str = "10g"         # Disk space
    DEFAULT_TIMEOUT: int = 3600       # Seconds
    
    # Allowed commands (empty = all commands allowed)
    # In production, this should be strictly whitelisted
    ALLOWED_COMMANDS = [
        "ls", "cat", "echo", "pwd", "whoami",
        "python", "python3", "pip",
        "git", "grep", "find",
        # Add approved commands here
    ]
    
    # Network access control
    NETWORK_POLICY = {
        "allow_outbound": False,           # Default deny all outbound
        "allowed_domains": [               # Whitelisted domains
            "pypi.org",
            "files.pythonhosted.org",
            "github.com",
            "api.openai.com",
        ],
        "blocked_ips": [                   # Blacklisted IP ranges
            "10.0.0.0/8",
            "172.16.0.0/12",
            "192.168.0.0/16",
        ]
    }
    
    @classmethod
    def get_capabilities(
        cls,
        enable_shell: bool = True,
        enable_filesystem: bool = True,
        enable_memory: bool = False,
        enable_network: bool = False
    ) -> list[Capability]:
        """Get capability set based on security policy"""
        capabilities = []
        
        if enable_shell:
            capabilities.append(Shell(
                allowlist=cls.ALLOWED_COMMANDS if len(cls.ALLOWED_COMMANDS) > 0 else None,
                timeout=600  # Individual command timeout
            ))
        
        if enable_filesystem:
            capabilities.append(Filesystem(
                allow_patch=True,        # Allow apply-patch edits
                allow_image_view=True,   # Allow viewing images
                max_file_size="100m"     # Max file size per operation
            ))
        
        if enable_memory:
            capabilities.append(Memory(
                compaction_enabled=True,
                compaction_threshold=80000,  # Tokens
                memory_path="/.agent_memory"
            ))
        
        if enable_network:
            capabilities.append(Network(
                allowlist=cls.NETWORK_POLICY["allowed_domains"]
            ))
        
        return capabilities


# ============================================
# Section 2: Manifest Workspace Builders
# ============================================

def create_code_review_manifest(repo_path: Optional[Path] = None) -> Manifest:
    """Create a manifest for code review tasks"""
    
    entries = {
        "README.md": File(content=b"""
# Code Review Task

Please review the Python code in this repository.

## Instructions:
1. Read all Python files in src/ directory
2. Identify bugs, security issues, and code smells
3. Suggest improvements
4. Run tests if available
5. Write a summary report to REVIEW_RESULT.md
"""),
        "security_guidelines.md": File(content=b"""
# Security Guidelines for Reviewers

DO:
- Check for hardcoded secrets
- Look for SQL injection patterns
- Verify input sanitization
- Check for insecure dependencies

DON'T:
- Exfiltrate any code or data outside sandbox
- Run any unapproved network operations
- Modify files outside the workspace
""")
    }
    
    mounts = []
    if repo_path and repo_path.exists():
        mounts.append(LocalDir(
            src=str(repo_path),
            dst="/workspace/repo",
            read_only=True
        ))
    
    # Optional: S3 mount for large datasets
    # mounts.append(S3Mount(
    #     bucket="openclaw-code-review",
    #     prefix="datasets/",
    #     dst="/workspace/datasets",
    #     read_only=True
    # ))
    
    return Manifest(
        entries=entries,
        mounts=mounts,
        output_dir="/workspace/outputs",
        workspace_root="/workspace"
    )


def create_data_analysis_manifest(input_data: bytes) -> Manifest:
    """Create a manifest for data analysis tasks"""
    return Manifest(
        entries={
            "input_data.csv": File(content=input_data),
            "analysis_instructions.md": File(content=b"""
# Data Analysis Task

Analyze the provided CSV data file.

Deliverables:
1. Summary statistics (mean, median, std, min, max)
2. Correlation matrix
3. Visualizations (saved as PNG)
4. Insights report in Markdown format
5. Cleaned data output as CSV

All outputs should be saved in the outputs/ directory.
""")
        },
        output_dir="/workspace/outputs"
    )


# ============================================
# Section 3: Sandboxed Agent Definitions
# ============================================

def create_sandbox_engineer_agent(
    model: str = "gpt-5.4",
    security_policy: SandboxSecurityPolicy = None
) -> SandboxAgent[None]:
    """Create a sandboxed engineer agent for code tasks"""
    
    policy = security_policy or SandboxSecurityPolicy()
    
    return SandboxAgent[None](
        name="OpenClaw Sandbox Engineer",
        model=model,
        instructions="""
You are a senior software engineer working in a secure sandbox environment.

## Your Environment
- You have shell access and can edit files
- All work stays within /workspace directory
- Network access is restricted to approved domains
- Your work may be audited

## Best Practices
1. Always read README or task instructions first
2. Understand existing code before making changes
3. Write tests for any modifications
4. Verify changes work before submitting
5. Document everything clearly

## Security Rules
- Never exfiltrate data outside the sandbox
- Don't attempt to escape the sandbox
- Report any security anomalies you discover
- Ask if you're unsure about permission boundaries
""",
        capabilities=policy.get_capabilities(
            enable_shell=True,
            enable_filesystem=True,
            enable_memory=True,
            enable_network=False  # Network disabled by default
        ),
        handoff_description="Sandboxed engineer for code tasks"
    )


def create_sandbox_data_analyst_agent(
    model: str = "gpt-5.4"
) -> SandboxAgent[None]:
    """Create a sandboxed data analyst agent"""
    
    policy = SandboxSecurityPolicy()
    
    return SandboxAgent[None](
        name="OpenClaw Data Analyst",
        model=model,
        instructions="""
You are a data analyst working in a secure sandbox environment.

## Capabilities
- Run Python data analysis scripts (pandas, numpy, matplotlib)
- Process CSV, JSON, and Parquet files
- Generate visualizations and reports
- All data stays within the sandbox

## Workflow
1. First explore the data structure
2. Clean and preprocess as needed
3. Perform statistical analysis
4. Generate visualizations
5. Write comprehensive report

## Data Privacy
- All data is confidential
- Don't attempt to export raw data
- Only share aggregated insights in reports
""",
        capabilities=policy.get_capabilities(
            enable_shell=True,
            enable_filesystem=True,
            enable_memory=True,
            enable_network=False
        )
    )


# ============================================
# Section 4: ACP Integration Layer
# ============================================

class ACPSandboxOrchestrator:
    """
    OpenClaw ACP Sandbox Orchestrator
    
    Manages sandbox lifecycle, security policy enforcement,
    and integration with ACP message protocol.
    """
    
    def __init__(self, sandbox_client=None):
        self.sandbox_client = sandbox_client or self._get_default_client()
        self.active_sandboxes: Dict[str, Any] = {}
        self.audit_log: list = []
    
    def _get_default_client(self):
        """Get the best available sandbox client"""
        if DOCKER_AVAILABLE:
            return DockerSandboxClient(
                default_image="openclaw/sandbox-python:v2026",
                network_mode="none"  # Default no network
            )
        elif UNIX_LOCAL_AVAILABLE:
            return UnixLocalSandboxClient()
        else:
            raise RuntimeError(
                "No sandbox client available. "
                "Install with: pip install 'openai-agents[docker]'"
            )
    
    def _audit_log(self, event_type: str, details: Dict[str, Any]):
        """Log sandbox events for audit"""
        entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "event_type": event_type,
            **details
        }
        self.audit_log.append(entry)
        # In production: write to secure log storage
    
    async def run_task_in_sandbox(
        self,
        task_id: str,
        agent: SandboxAgent,
        task_instructions: str,
        manifest: Manifest,
        workflow_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Run an agent task in a secure sandbox
        
        Args:
            task_id: ACP task identifier
            agent: SandboxAgent to execute
            task_instructions: Task description
            manifest: Workspace manifest
            workflow_name: Optional workflow name for tracing
        
        Returns:
            Task result with outputs and metadata
        """
        self._audit_log("sandbox_create", {
            "task_id": task_id,
            "agent_name": agent.name,
            "workflow": workflow_name
        })
        
        try:
            # Configure sandbox run
            run_config = RunConfig(
                sandbox=SandboxRunConfig(
                    client=self.sandbox_client,
                    manifest=manifest,
                    # Security policies are enforced by capabilities
                ),
                workflow_name=workflow_name or f"ACP-Task-{task_id}",
                tracing_enabled=True,
                max_steps=100  # Prevent infinite loops
            )
            
            # Run the agent in sandbox
            result = await Runner.run(
                agent,
                task_instructions,
                run_config=run_config
            )
            
            self._audit_log("sandbox_complete", {
                "task_id": task_id,
                "success": True,
                "turns": result.turns,
                "tokens_used": result.total_tokens
            })
            
            # Collect outputs from sandbox
            outputs = await self._collect_sandbox_outputs(
                result.sandbox_handle,
                manifest.output_dir
            )
            
            return {
                "task_id": task_id,
                "success": True,
                "final_output": result.final_output,
                "outputs": outputs,
                "turns": result.turns,
                "tokens_used": result.total_tokens,
                "trace_id": result.trace_id
            }
            
        except Exception as e:
            self._audit_log("sandbox_error", {
                "task_id": task_id,
                "error": str(e),
                "error_type": type(e).__name__
            })
            raise
    
    async def _collect_sandbox_outputs(
        self,
        sandbox_handle,
        output_dir: str
    ) -> Dict[str, str]:
        """Collect output files from sandbox"""
        # In real implementation:
        # 1. List files in output_dir within sandbox
        # 2. Read file contents
        # 3. Virus scan outputs before returning
        # 4. Apply data loss prevention filters
        
        return {
            "status": "output_collection_placeholder",
            "output_dir": output_dir,
            "note": "Actual implementation would extract files from sandbox"
        }
    
    async def create_checkpoint(
        self,
        task_id: str,
        sandbox_handle
    ) -> str:
        """Create a checkpoint for long-running task recovery"""
        checkpoint_name = f"acp-checkpoint-{task_id}-{int(datetime.utcnow().timestamp())}"
        
        # checkpoint = await sandbox_handle.checkpoint(checkpoint_name)
        
        self._audit_log("checkpoint_create", {
            "task_id": task_id,
            "checkpoint_name": checkpoint_name
        })
        
        return checkpoint_name


# ============================================
# Section 5: Example Usage
# ============================================

async def example_basic_sandbox_task():
    """Example: Run a simple code review task in sandbox"""
    # print("=" * 60)
    # print("Example 1: Basic Sandbox Task")
    # print("=" * 60)
    
    # 1. Create orchestrator
    orchestrator = ACPSandboxOrchestrator()
    
    # 2. Create agent
    agent = create_sandbox_engineer_agent()
    
    # 3. Create workspace manifest
    manifest = create_code_review_manifest()
    
    # 4. Define task
    task_id = "ACP-1931-DEMO"
    instructions = """
    Review the files in /workspace.
    1. Read README.md and security_guidelines.md
    2. List all files in the workspace
    3. Create a review summary at /workspace/outputs/review.md
    """
    
    # print(f"\nSubmitting task {task_id} to sandbox...")
    # print(f"Agent: {agent.name}")
    # print(f"Capabilities: {[type(c).__name__ for c in agent.capabilities]}")
    
    # 5. Execute (commented out for example - requires actual SDK)
    # result = await orchestrator.run_task_in_sandbox(
    #     task_id=task_id,
    #     agent=agent,
    #     task_instructions=instructions,
    #     manifest=manifest,
    #     workflow_name="Sandbox-Demo-CodeReview"
    # )
    
    # print("\n[DEMO MODE] Task would execute in isolated sandbox")
    # print("Expected behavior:")
    # print("  - Sandbox container created with isolated filesystem")
    # print("  - Files from manifest injected into workspace")
    # print("  - Agent reads files and executes shell commands within sandbox")
    # print("  - Outputs written to sandbox output directory")
    # print("  - Sandbox destroyed after task completion")
    
    # print("\nAudit log entries:")
    for entry in orchestrator.audit_log:
        # print(f"  [{entry['timestamp']}] {entry['event_type']}")


async def example_security_policy():
    """Example: Demonstrate security policy configuration"""
    # print("\n" + "=" * 60)
    # print("Example 2: Security Policy Configuration")
    # print("=" * 60)
    
    policy = SandboxSecurityPolicy()
    
    # print(f"\nDefault Resource Quotas:")
    # print(f"  CPU: {policy.DEFAULT_CPU} vCPUs")
    # print(f"  Memory: {policy.DEFAULT_MEMORY}")
    # print(f"  Disk: {policy.DEFAULT_DISK}")
    # print(f"  Timeout: {policy.DEFAULT_TIMEOUT}s")
    
    # print(f"\nAllowed Commands ({len(policy.ALLOWED_COMMANDS)}):")
    for cmd in policy.ALLOWED_COMMANDS[:10]:
        # print(f"  - {cmd}")
    
    # print(f"\nNetwork Policy:")
    # print(f"  Allow Outbound: {policy.NETWORK_POLICY['allow_outbound']}")
    # print(f"  Allowed Domains: {policy.NETWORK_POLICY['allowed_domains']}")
    
    # Different capability sets
    # print(f"\nCapability Configurations:")
    basic_caps = policy.get_capabilities(enable_shell=True, enable_filesystem=True)
    # print(f"  Basic (Shell+FS): {[type(c).__name__ for c in basic_caps]}")
    
    full_caps = policy.get_capabilities(
        enable_shell=True, enable_filesystem=True, 
        enable_memory=True, enable_network=True
    )
    # print(f"  Full (all): {[type(c).__name__ for c in full_caps]}")


async def example_manifest_configuration():
    """Example: Demonstrate manifest workspace configuration"""
    # print("\n" + "=" * 60)
    # print("Example 3: Manifest Workspace Configuration")
    # print("=" * 60)
    
    # Code review manifest
    manifest1 = create_code_review_manifest()
    # print(f"\nCode Review Manifest:")
    # print(f"  Files in workspace: {list(manifest1.entries.keys())}")
    # print(f"  Number of mounts: {len(manifest1.mounts)}")
    # print(f"  Output directory: {manifest1.output_dir}")
    
    # Data analysis manifest
    sample_data = b"date,value\n2026-01-01,100\n2026-01-02,150\n"
    manifest2 = create_data_analysis_manifest(sample_data)
    # print(f"\nData Analysis Manifest:")
    # print(f"  Files in workspace: {list(manifest2.entries.keys())}")
    # print(f"  Sample data size: {len(sample_data)} bytes")


# ============================================
# Section 6: Main Execution
# ============================================

async def main():
    """Run all examples"""
    # print("OpenClaw ACP v2026 - Sandbox Integration Examples")
    # print(f"Date: {datetime.now().isoformat()}")
    # print(f"Docker Client Available: {DOCKER_AVAILABLE}")
    # print(f"Unix Local Client Available: {UNIX_LOCAL_AVAILABLE}")
    
    await example_basic_sandbox_task()
    await example_security_policy()
    await example_manifest_configuration()
    
    # print("\n" + "=" * 60)
    # print("All examples completed!")
    # print("=" * 60)
    # print("\nNext steps:")
    # print("1. Install openai-agents with sandbox support:")
    # print("   pip install 'openai-agents[docker]'")
    # print("2. Configure OpenAI API key")
    # print("3. Run actual tasks using ACPSandboxOrchestrator")
    # print("4. See harness_config_example.json for advanced configuration")


if __name__ == "__main__":
    asyncio.run(main())
