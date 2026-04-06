"""Read Maestro configuration: dump settings as raw SKILL output.

Verbosity levels:
    0 — tests, enabled analyses, outputs, variables (quick overview)
    1 — + per-analysis params, parameters, corners (full setup)
    2 — + envOption, simOption, runMode, jobControl, simulation results (everything)
"""

import re

from virtuoso_bridge import VirtuosoClient


def read_config(client: VirtuosoClient, ses: str, verbose: int = 1) -> dict[str, tuple[str, str]]:
    """Read Maestro config for a session.

    Args:
        ses: session string from open_session or find_open_session
        verbose: 0 = quick, 1 = full setup, 2 = everything incl. results

    Returns a dict where:
        key   = label
        value = (skill_expr, raw_output)
    """
    def q(label: str, expr: str) -> tuple[str, str]:
        """Execute SKILL, print to CIW, return (expr, raw output)."""
        wrapped = (
            f'let((rbResult) '
            f'rbResult = {expr} '
            f'printf("[%s read_config] {label}\\n" nth(2 parseString(getCurrentTime()))) '
            f'printf("  %L\\n" rbResult) '
            f'rbResult)'
        )
        r = client.execute_skill(wrapped)
        return (expr, r.output or "")

    # ---- Level 0: quick overview ----

    expr_setup = f'maeGetSetup(?session "{ses}")'
    _, tests_raw = q("maeGetSetup", expr_setup)
    test = ""
    if tests_raw and tests_raw != "nil":
        m = re.findall(r'"([^"]+)"', tests_raw)
        if m:
            test = m[0]

    result: dict[str, tuple[str, str]] = {"maeGetSetup": (expr_setup, tests_raw)}
    if not test:
        return result

    expr = f'maeGetEnabledAnalysis("{test}" ?session "{ses}")'
    _, enabled_raw = q("maeGetEnabledAnalysis", expr)
    result["maeGetEnabledAnalysis"] = (expr, enabled_raw)
    enabled = re.findall(r'"([^"]+)"', enabled_raw)

    expr_out = (
        f'let((outs result) '
        f'outs = maeGetTestOutputs("{test}" ?session "{ses}") '
        f'result = list() '
        f'foreach(o outs '
        f'  result = append1(result list(o~>name o~>type o~>signal o~>expression))) '
        f'result)'
    )
    result["maeGetTestOutputs"] = q("maeGetTestOutputs", expr_out)

    expr = f'maeGetSetup(?session "{ses}" ?typeName "variables")'
    result["variables"] = q("variables", expr)

    if verbose < 1:
        return result

    # ---- Level 1: full setup ----

    for ana in enabled:
        expr = f'maeGetAnalysis("{test}" "{ana}" ?session "{ses}")'
        result[f"maeGetAnalysis:{ana}"] = q(f"maeGetAnalysis:{ana}", expr)

    expr = f'maeGetSetup(?session "{ses}" ?typeName "parameters")'
    result["parameters"] = q("parameters", expr)

    expr = f'maeGetSetup(?session "{ses}" ?typeName "corners")'
    result["corners"] = q("corners", expr)

    if verbose < 2:
        return result

    # ---- Level 2: everything ----

    expr = f'maeGetEnvOption("{test}" ?session "{ses}")'
    result["maeGetEnvOption"] = q("maeGetEnvOption", expr)

    expr = f'maeGetSimOption("{test}" ?session "{ses}")'
    result["maeGetSimOption"] = q("maeGetSimOption", expr)

    expr = f'maeGetCurrentRunMode(?session "{ses}")'
    result["maeGetCurrentRunMode"] = q("maeGetCurrentRunMode", expr)

    expr = f'maeGetJobControlMode(?session "{ses}")'
    result["maeGetJobControlMode"] = q("maeGetJobControlMode", expr)

    # Results (only if simulation has been run)
    has_results_expr = 'maeOpenResults()'
    _, has_results = q("maeOpenResults", has_results_expr)
    if has_results and has_results.strip('"') not in ("nil", ""):
        expr = 'maeGetResultTests()'
        result["maeGetResultTests"] = q("maeGetResultTests", expr)
        result_tests = re.findall(r'"([^"]+)"',
                                  result["maeGetResultTests"][1])
        for rt in result_tests:
            expr = f'maeGetResultOutputs(?testName "{rt}")'
            result[f"maeGetResultOutputs:{rt}"] = q(
                f"maeGetResultOutputs:{rt}", expr)
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

        history_name = has_results.strip('"')
        expr = f'maeGetOverallYield("{history_name}")'
        result["maeGetOverallYield"] = q("maeGetOverallYield", expr)

        client.execute_skill('maeCloseResults()')

    # Simulation messages
    expr = f'maeGetSimulationMessages(?session "{ses}")'
    _, sim_msgs = q("maeGetSimulationMessages", expr)
    if sim_msgs and sim_msgs != "nil":
        result["maeGetSimulationMessages"] = (expr, sim_msgs)

    return result
