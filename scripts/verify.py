"""Offline verification entry point. Requires no running Streamlit server.

Fails explicitly until application modules and meaningful tests exist.
Use --planning to check the initial file pack only, not application behavior.
"""
from pathlib import Path
import argparse
import compileall
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--planning', action='store_true')
    args = parser.parse_args()
    limits = {'AGENT_RULES.md': 60, 'PROJECT.md': 80, 'HANDOFF.md': 30,
              'prompts/FULLSTACK_AGENT.md': 50}
    required = [*limits, 'API_CONTRACT.md', 'TASKS.md', '.gitignore', '.env.example']
    problems = []
    for name in required:
        path = ROOT / name
        if not path.is_file():
            problems.append(f'Missing {name}')
        elif name in limits and len(path.read_text(encoding='utf-8').splitlines()) > limits[name]:
            problems.append(f'{name} exceeds {limits[name]} lines')
    if problems:
        print('\n'.join(problems))
        return 1
    print('Planning files present; document line limits pass.')
    if args.planning:
        print('Application behavior NOT checked (--planning).')
        return 0
    modules = ['app.py', 'study_app.py', 'study.py', 'ai_provider.py', 'lab_app.py',
               'engine.py', 'workflow.py', 'ledger.py']
    for name in [*modules, 'data/packs.json', 'data/demo-notes.md', 'requirements.txt',
                 'tests/test_core.py', 'tests/test_study.py', 'tests/test_study_app.py']:
        if not (ROOT / name).is_file():
            problems.append(f'Missing implementation: {name}')
    if problems:
        print('\n'.join(problems))
        return 1
    for name in [*modules, 'tests']:
        path = ROOT / name
        compiled = (compileall.compile_dir(path, quiet=1) if path.is_dir()
                    else compileall.compile_file(path, quiet=1))
        if not compiled:
            return 1
    sys.path.insert(0, str(ROOT))
    suite = unittest.defaultTestLoader.discover(str(ROOT / 'tests'))
    if suite.countTestCases() == 0:
        print('FAIL: no core tests discovered.')
        return 1
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    print('Browser demo walkthrough and server health still require separate checks.')
    return 0 if result.wasSuccessful() else 1


if __name__ == '__main__':
    raise SystemExit(main())
