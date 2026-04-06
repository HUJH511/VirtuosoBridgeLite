#!/usr/bin/env python3
"""Hello World — execute SKILL expressions and display return values locally.

Prerequisites:
- virtuoso-bridge tunnel running (virtuoso-bridge start)
- RAMIC daemon loaded in Virtuoso CIW
"""
from virtuoso_bridge import VirtuosoClient

client = VirtuosoClient.from_env()

# Print a banner in CIW
skill_cmd = r'printf("\n\n==============================================\nHello, Virtuoso!\n")'
r = client.execute_skill(skill_cmd)
print(f"Banner: {r.output!r}")

# Date & Time
skill_cmd = r'getCurrentTime()'
r = client.execute_skill(skill_cmd)
print(f"Date & Time:     {r.output}")

# Cadence Version
skill_cmd = r'getVersion()'
r = client.execute_skill(skill_cmd)
print(f"Cadence Version: {r.output}")

# SKILL Version
skill_cmd = r'getSkillVersion()'
r = client.execute_skill(skill_cmd)
print(f"SKILL Version:   {r.output}")

# Working Directory
skill_cmd = r'getWorkingDir()'
r = client.execute_skill(skill_cmd)
print(f"Working Dir:     {r.output}")

# Host Name
skill_cmd = r'getHostName()'
r = client.execute_skill(skill_cmd)
print(f"Host Name:       {r.output}")

# Simple arithmetic
skill_cmd = "1 + 2"
r = client.execute_skill(skill_cmd)
print(f"1 + 2 =          {r.output}")

# String concatenation
skill_cmd = 'strcat("Hello" " from SKILL")'
r = client.execute_skill(skill_cmd)
print(f"strcat:          {r.output}")
