"""Read Maestro configuration, environment, and simulation results.

Three independent read functions:
    read_config(client, ses)  — test setup: analyses, outputs, variables, corners
    read_env(client, ses)     — system settings: env options, sim options, run mode
    read_results(client, ses) — simulation results: output values, specs, yield
"""

import re

from virtuoso_bridge import VirtuosoClient


def _q(client: VirtuosoClient, label: str, expr: str) -> tuple[str, str]:
    """Execute SKILL, print to CIW, return (expr, raw output)."""
    wrapped = (
        f'let((rbResult) '
        f'rbResult = {expr} '
        f'printf("[%s read] {label}\\n" nth(2 parseString(getCurrentTime()))) '
        f'printf("  %L\\n" rbResult) '
        f'rbResult)'
    )
    r = client.execute_skill(wrapped)
    return (expr, r.output or "")


def _get_test(client: VirtuosoClient, ses: str) -> str:
    """Get the first test name from a session."""
    r = client.execute_skill(f'maeGetSetup(?session "{ses}")')
    raw = r.output or ""
    if raw and raw != "nil":
        m = re.findall(r'"([^"]+)"', raw)
        if m:
            return m[0]
    return ""


def read_config(client: VirtuosoClient, ses: str) -> dict[str, tuple[str, str]]:
    """Read test configuration: tests, analyses, outputs, variables, parameters, corners.

    Returns dict of (skill_expr, raw_output) tuples.
    """
    def q(label, expr):
        return _q(client, label, expr)

    expr = f'maeGetSetup(?session "{ses}")'
    _, tests_raw = q("maeGetSetup", expr)
    test = ""
    if tests_raw and tests_raw != "nil":
        m = re.findall(r'"([^"]+)"', tests_raw)
        if m:
            test = m[0]

    result: dict[str, tuple[str, str]] = {"maeGetSetup": (expr, tests_raw)}
    if not test:
        return result

    # Enabled analyses
    expr = f'maeGetEnabledAnalysis("{test}" ?session "{ses}")'
    _, enabled_raw = q("maeGetEnabledAnalysis", expr)
    result["maeGetEnabledAnalysis"] = (expr, enabled_raw)
    enabled = re.findall(r'"([^"]+)"', enabled_raw)

    # Per-analysis params
    for ana in enabled:
        expr = f'maeGetAnalysis("{test}" "{ana}" ?session "{ses}")'
        result[f"maeGetAnalysis:{ana}"] = q(f"maeGetAnalysis:{ana}", expr)

    # Outputs
    expr_out = (
        f'let((outs result) '
        f'outs = maeGetTestOutputs("{test}" ?session "{ses}") '
        f'result = list() '
        f'foreach(o outs '
        f'  result = append1(result list(o~>name o~>type o~>signal o~>expression))) '
        f'result)'
    )
    result["maeGetTestOutputs"] = q("maeGetTestOutputs", expr_out)

    # Variables, parameters, corners
    for type_name in ("variables", "parameters", "corners"):
        expr = f'maeGetSetup(?session "{ses}" ?typeName "{type_name}")'
        result[type_name] = q(type_name, expr)

    return result


def read_env(client: VirtuosoClient, ses: str) -> dict[str, tuple[str, str]]:
    """Read system settings: env options, sim options, run mode, job control.

    Returns dict of (skill_expr, raw_output) tuples.
    """
    def q(label, expr):
        return _q(client, label, expr)

    test = _get_test(client, ses)
    if not test:
        return {}

    result: dict[str, tuple[str, str]] = {}

    expr = f'maeGetEnvOption("{test}" ?session "{ses}")'
    result["maeGetEnvOption"] = q("maeGetEnvOption", expr)

    expr = f'maeGetSimOption("{test}" ?session "{ses}")'
    result["maeGetSimOption"] = q("maeGetSimOption", expr)

    expr = f'maeGetCurrentRunMode(?session "{ses}")'
    result["maeGetCurrentRunMode"] = q("maeGetCurrentRunMode", expr)

    expr = f'maeGetJobControlMode(?session "{ses}")'
    result["maeGetJobControlMode"] = q("maeGetJobControlMode", expr)

    # Simulation messages
    expr = f'maeGetSimulationMessages(?session "{ses}")'
    _, sim_msgs = q("maeGetSimulationMessages", expr)
    if sim_msgs and sim_msgs not in ("nil", '""'):
        result["maeGetSimulationMessages"] = (expr, sim_msgs)

    return result


def read_results(client: VirtuosoClient, ses: str) -> dict[str, tuple[str, str]]:
    """Read simulation results: output values, spec status, yield.

    Finds the latest history automatically. Returns empty dict if no results.
    Returns dict of (skill_expr, raw_output) tuples.
    """
    def q(label, expr):
        return _q(client, label, expr)

    # Find history name from asiGetResultsDir
    history_expr = 'asiGetResultsDir(asiGetCurrentSession())'
    _, results_dir = q("asiGetResultsDir", history_expr)
    results_dir_str = results_dir.strip('"')
    latest_history = ""
    m = re.search(r'/maestro/results/maestro/([^/]+)/', results_dir_str)
    if m:
        latest_history = m.group(1)

    if not latest_history:
        return {}

    # Open results
    open_expr = f'maeOpenResults(?history "{latest_history}")'
    _, opened = q("maeOpenResults", open_expr)
    if not opened or opened.strip('"') in ("nil", ""):
        return {}

    result: dict[str, tuple[str, str]] = {}

    expr = 'maeGetResultTests()'
    result["maeGetResultTests"] = q("maeGetResultTests", expr)
    result_tests = re.findall(r'"([^"]+)"', result["maeGetResultTests"][1])

    for rt in result_tests:
        expr = f'maeGetResultOutputs(?testName "{rt}")'
        result[f"maeGetResultOutputs:{rt}"] = q(f"maeGetResultOutputs:{rt}", expr)
        result_outputs = re.findall(
            r'"([^"]+)"', result[f"maeGetResultOutputs:{rt}"][1])
        for ro in result_outputs:
            expr = f'maeGetOutputValue("{ro}" "{rt}")'
            _, val = q(f"maeGetOutputValue:{rt}:{ro}", expr)
            if val and val != "nil":
                result[f"maeGetOutputValue:{rt}:{ro}"] = (expr, val)

            expr = f'maeGetSpecStatus("{ro}" "{rt}")'
            _, spec = q(f"maeGetSpecStatus:{rt}:{ro}", expr)
            if spec and spec != "nil":
                result[f"maeGetSpecStatus:{rt}:{ro}"] = (expr, spec)

    expr = 'maeGetOverallSpecStatus()'
    result["maeGetOverallSpecStatus"] = q("maeGetOverallSpecStatus", expr)

    expr = f'maeGetOverallYield("{latest_history}")'
    result["maeGetOverallYield"] = q("maeGetOverallYield", expr)

    client.execute_skill('maeCloseResults()')

    return result
