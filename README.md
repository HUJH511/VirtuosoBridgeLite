<p align="center">
  <img src="assets/banner.svg" alt="virtuoso-bridge-lite" width="100%"/>
</p>

<p align="center">
  <a href="https://www.python.org/downloads/"><img src="https://img.shields.io/badge/python-3.9%2B-blue.svg" alt="Python 3.9+"/></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-green.svg" alt="License: MIT"/></a>
  <a href="https://github.com/Arcadia-1/virtuoso-bridge-lite"><img src="https://img.shields.io/github/stars/Arcadia-1/virtuoso-bridge-lite?style=social" alt="GitHub stars"/></a>
  <a href="https://claude.ai/code"><img src="https://img.shields.io/badge/AI%20Native-agent--driven%20development-blueviolet" alt="AI Native"/></a>
</p> 

Control a remote Cadence Virtuoso from any machine over SSH. No VNC, no X11, no manual terminal sessions.

Use a coding agent (Claude Code, Cursor, etc.) to read this repo and tailor it to your project — PDK, libraries, tech node, directory structure. You describe intent; the agent writes SKILL, builds layouts, runs simulations.

> **If you are an AI agent**, read [`AGENTS.md`](AGENTS.md) first and follow its setup checklist.

## Quick Start

```bash
pip install -e .
virtuoso-bridge init        # generates .env
```

Edit `.env`, fill in one variable:

```dotenv
VB_REMOTE_HOST=my-server    # SSH host alias from ~/.ssh/config
```

Then:

```bash
virtuoso-bridge start
```

```python
from virtuoso_bridge import BridgeClient

client = BridgeClient()
result = client.execute_skill("1+2")
print(result)  # {'ok': True, 'result': {'output': '3', ...}}
```

Done.

### Prerequisites

1. **SSH**: `ssh my-server` must work in your terminal without a password prompt. Fix SSH first if it doesn't.
2. **Virtuoso**: a Virtuoso process must be running on the remote machine.

## Architecture

> Want to understand the raw mechanism? See [`core/`](core/) — the entire bridge distilled into 3 files (180 lines), with no dependencies, no CLI, no auto-reconnect. Read it first, then use the full package.

```
Local Machine (any OS)            Remote Virtuoso Server
──────────────────────            ──────────────────────
Python script                     Virtuoso (running)
    │                                 │
    ▼                                 ▼
BridgeClient ──TCP──► BridgeService  RAMIC daemon (Python 2.7)
                          │              │
                          └──SSH tunnel──┘
                                 │
                              SKILL execution
```

Three capabilities:

1. **SKILL execution** — send SKILL commands to a running Virtuoso, get results back
2. **Layout & Schematic editing** — Python API for creating/modifying cellviews
3. **Spectre simulation** — run simulations remotely, parse results automatically

## CLI

```bash
virtuoso-bridge init      # create .env template
virtuoso-bridge start     # start the bridge service
virtuoso-bridge restart   # force-restart
virtuoso-bridge status    # check connection health + Spectre license
```

## Build & Test

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
pytest
```

## Citation

If you use virtuoso-bridge in academic work, please cite:

```bibtex
@article{zhang2025virtuosobridge,
  title   = {Virtuoso-Bridge: An Agent-Native Bridge for Harness Engineering
             in Analog and Mixed-Signal Workflows},
  author  = {Zhang, Zhishuai and Li, Xintian and Sun, Nan and Jie, Lu},
  year    = {2025}
}
```

## Authors

- **Zhishuai Zhang** — Tsinghua University
- **Xintian Li** — Tsinghua University
- **Nan Sun** — Tsinghua University
- **Lu Jie** — Tsinghua University
