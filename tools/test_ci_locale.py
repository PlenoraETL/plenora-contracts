"""Controprove C2: workflow indipendenti e piccoli processi realmente eseguiti."""
import contextlib
import io
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import yaml

import ci_locale as ci


class CiLocaleTests(unittest.TestCase):
    def setUp(self):
        (ci.ROOT / 'target').mkdir(exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(dir=ci.ROOT / 'target')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / '.github/workflows').mkdir(parents=True)

    def workflow(self, jobs, name='pr.yml', event='pull_request'):
        (self.root / '.github/workflows' / name).write_text(
            yaml.safe_dump({'on': {event: None}, 'jobs': jobs}), encoding='utf-8')

    def job(self, steps, **options):
        return {'runs-on': 'windows-latest', 'steps': steps, **options}

    def run_plan(self):
        plan = ci.derive(self.root)
        with patch.object(ci, 'git', side_effect=lambda root, *args: 'a' * 40 if args[0] == 'rev-parse' else ''), \
                patch.object(ci, 'host_os', return_value='Windows'), contextlib.redirect_stdout(io.StringIO()):
            path, receipt = ci.execute(plan, self.root)
        self.assertEqual(ci.strict_loads(path.read_text(encoding='utf-8')), receipt)
        for step in receipt['steps']:
            if step['status'] == 'PASS':
                self.assertEqual(step['exit_code'], 0)
                self.assertTrue(Path(step['log']).is_file())
                self.assertIsInstance(step['command'], list)
        return receipt

    def test_process_failure_and_default_condition(self):
        self.workflow({'probe': self.job([
            {'run': 'raise SystemExit(7)', 'shell': 'python'},
            {'run': "raise RuntimeError('must not run')", 'shell': 'python'},
            {'run': "print('cleanup')", 'shell': 'python', 'if': 'always()'},
        ])})
        receipt = self.run_plan()
        self.assertEqual([s['status'] for s in receipt['steps']], ['FAIL', 'NON ESEGUITO', 'PASS'])
        self.assertEqual(receipt['exit_code'], 1)

    def test_missing_step_blocks_following_and_never_green(self):
        self.workflow({'probe': self.job([{'name': 'missing'}, {'run': 'print(1)', 'shell': 'python'}])})
        receipt = self.run_plan()
        self.assertEqual([s['status'] for s in receipt['steps']], ['NON ESEGUITO'] * 2)
        self.assertEqual(receipt['exit_code'], 2)

    def test_status_conditions_are_evaluated_at_runtime(self):
        self.workflow({'probe': self.job([
            {'run': 'raise SystemExit(1)', 'shell': 'python'},
            {'run': 'print(1)', 'shell': 'python', 'if': '${{ success() }}'},
            {'run': 'print(1)', 'shell': 'python', 'if': 'true'},
            {'run': 'print(1)', 'shell': 'python', 'if': '${{ failure() }}'},
        ])})
        self.assertEqual([s['status'] for s in self.run_plan()['steps']],
                         ['FAIL', 'NON ESEGUITO', 'NON ESEGUITO', 'PASS'])

    def test_exported_environment_and_step_precedence(self):
        self.workflow({'probe': self.job([
            {'run': "import os; open(os.environ['GITHUB_ENV'], 'w').write('X=exported\\n')", 'shell': 'python'},
            {'run': "import os; assert os.environ['X'] == 'local'; assert '${{ env.X }}' == 'local'",
             'shell': 'python', 'env': {'X': 'local'}},
            {'run': "import os; assert os.environ['X'] == 'exported'; assert '${{ env.X }}' == 'exported'",
             'shell': 'python'},
        ], env={'X': 'initial'})})
        self.assertEqual([s['status'] for s in self.run_plan()['steps']], ['PASS'] * 3)

    def test_expression_types_are_not_silently_coerced(self):
        from ci_locale_expr import evaluate, truth, Unsupported
        self.assertTrue(truth(evaluate("'false'", {})))
        self.assertTrue(truth(evaluate("'0'", {})))
        self.assertFalse(truth(evaluate('false', {})))
        for expression in ("true == 'true'", 'false == 0'):
            with self.assertRaises(Unsupported):
                evaluate(expression, {})

    def test_runtime_temp_directory(self):
        self.workflow({'probe': self.job([
            {'run': "import os; from pathlib import Path; assert Path(os.environ['TMP_PROBE']).is_dir()",
             'shell': 'python', 'env': {'TMP_PROBE': '${{ runner.temp }}'}}])})
        self.assertEqual(self.run_plan()['steps'][0]['status'], 'PASS')

    def test_condition_uses_current_step_environment(self):
        self.workflow({'probe': self.job([
            {'run': 'print(1)', 'shell': 'python', 'env': {'X': 'one'}},
            {'run': 'print(2)', 'shell': 'python', 'env': {'X': 'two'}, 'if': "env.X == 'one'"},
        ])})
        self.assertEqual([s['status'] for s in self.run_plan()['steps']], ['PASS', 'NON ESEGUITO'])

    def test_status_function_in_literal_is_not_a_function(self):
        self.assertFalse(ci.condition("'always()' == 'always()'", {'success()': False}))

    def test_defaults_and_working_directory(self):
        (self.root / 'work').mkdir()
        data = {'on': {'pull_request': {'paths': ['src/**']}},
                'defaults': {'run': {'shell': 'python', 'working-directory': 'work'}},
                'env': {'GLOBAL': 'yes'},
                'jobs': {'probe': self.job([{'run': "import os; from pathlib import Path; assert Path.cwd().name == 'work'; assert os.environ['GLOBAL'] == 'yes'"}])}}
        (self.root / '.github/workflows/pr.yml').write_text(yaml.safe_dump(data), encoding='utf-8')
        plan = ci.derive(self.root)
        self.assertEqual(plan['jobs'][0]['filters']['pull_request']['paths'], ['src/**'])
        self.assertEqual(self.run_plan()['steps'][0]['status'], 'PASS')

    def test_empty_job_is_not_pass(self):
        self.workflow({'probe': self.job([])})
        self.assertEqual(self.run_plan()['jobs'][0]['status'], 'NON ESEGUITO')

    def test_matrix_needs_env_defaults_and_filters(self):
        self.workflow({'first': self.job([{'run': 'print(1)', 'shell': 'python'}]),
                       'matrix': self.job([{'run': 'print(2)', 'shell': 'python'}],
                           needs=['first'], strategy={'matrix': {'os': ['ubuntu-latest', 'windows-latest'],
                               'exclude': [{'os': 'ubuntu-latest'}], 'include': [{'os': 'windows-2025'}]}})})
        plan = ci.derive(self.root)
        self.assertEqual(len(plan['jobs']), 3)
        self.assertEqual([j['matrix']['os'] for j in plan['jobs'] if j['key'] == 'matrix'],
                         ['windows-latest', 'windows-2025'])
        receipt = self.run_plan()
        self.assertEqual([j['status'] for j in receipt['jobs']], ['PASS', 'NON ESEGUITO', 'NON ESEGUITO'])

    def test_conditions_services_platform_and_unknown_action(self):
        cases = [({'if': 'false'}, [{'run': 'print(1)', 'shell': 'python'}]),
                 ({'services': {'db': {'image': 'postgres:17'}}}, [{'run': 'print(1)', 'shell': 'python'}]),
                 ({'runs-on': 'ubuntu-latest'}, [{'run': 'print(1)', 'shell': 'python'}]),
                 ({}, [{'uses': 'unknown/action@v1'}]),
                 ({}, [{'run': 'print(1)', 'shell': 'python', 'if': 'unknown.context'}])]
        for options, steps in cases:
            with self.subTest(options=options, steps=steps):
                self.workflow({'probe': self.job(steps, **options)})
                self.assertEqual(self.run_plan()['steps'][0]['status'], 'NON ESEGUITO')

    def test_false_step_does_not_prevent_next_step(self):
        self.workflow({'probe': self.job([{'run': 'print(1)', 'shell': 'python', 'if': 'false'},
                                         {'run': 'print(2)', 'shell': 'python'}])})
        self.assertEqual([s['status'] for s in self.run_plan()['steps']], ['NON ESEGUITO', 'PASS'])

    def test_all_profiles_present_release_never_executes(self):
        self.workflow({'release': self.job([{'run': 'print(1)', 'shell': 'python'}])}, 'rilascio.yml', 'release')
        self.workflow({'manual': self.job([{'run': 'print(1)', 'shell': 'python'}])}, 'manual.yml', 'workflow_dispatch')
        plan = ci.derive(self.root)
        self.assertEqual({j['profile'] for j in plan['jobs']}, {'release', 'qualifica'})
        self.assertEqual(self.run_plan()['counts'], {'NON ESEGUITO': 2})

    def test_checkout_is_read_only_and_verifies_sha(self):
        args = {'repository': 'owner/repo', 'ref': 'a' * 40, 'path': 'dependency'}
        with self.assertRaises(ci.Unsupported):
            ci.checkout_source(args, self.root)
        exists = patch.object(Path, 'exists', return_value=True)
        exists.start()
        self.addCleanup(exists.stop)
        def answer(root, *command):
            return {'remote': 'https://github.com/owner/repo.git',
                    'status': '', 'rev-parse': 'a' * 40}[command[0]]
        with patch.object(ci, 'git', side_effect=answer), patch.object(ci.subprocess, 'run') as run:
            self.assertEqual(ci.checkout_source(args, self.root), str(self.root / 'dependency'))
            ci.additional_checkout(self.root, args, str(self.root / 'dependency'))
            run.assert_not_called()
        with patch.object(ci, 'git', side_effect=lambda root, *args: 'b' * 40 if args[0] == 'rev-parse' else answer(root, *args)):
            with self.assertRaises(ci.Unsupported):
                ci.checkout_source(args, self.root)
        with self.assertRaises(ci.Unsupported):
            ci.inside(self.root, '.git/config')

    def test_null_and_empty_steps_are_not_pass(self):
        for step in (None, {'run': '', 'shell': 'python'}):
            with self.subTest(step=step):
                self.workflow({'probe': self.job([step])})
                self.assertEqual(self.run_plan()['steps'][0]['status'], 'NON ESEGUITO')

    def test_generated_documents_are_not_contract_documents(self):
        import validate_specs as validator
        (self.root / 'target').mkdir()
        (self.root / 'target/binary.md').write_bytes(b'\xff')
        (self.root / 'README.md').write_text('[missing](missing.md)', encoding='utf-8')
        with patch.object(validator, 'ROOT', self.root):
            errors = validator.validate_markdown_links()
        self.assertEqual(len(errors), 1)
        self.assertIn('missing.md', errors[0])

    def test_missing_script_is_not_executed(self):
        self.workflow({'probe': self.job([{'run': 'python tools/missing.py', 'shell': 'python'}])})
        self.assertEqual(self.run_plan()['steps'][0]['status'], 'NON ESEGUITO')

    def test_strict_json(self):
        for text in ('{"x": 1, "x": 2}', 'NaN', 'Infinity'):
            with self.assertRaises(ValueError):
                ci.strict_loads(text)

    def test_git_fetch_is_never_executed(self):
        self.workflow({'probe': self.job([{'run': 'git fetch origin main', 'shell': 'python'}])})
        with patch.object(ci.subprocess, 'run') as run:
            self.assertEqual(self.run_plan()['steps'][0]['status'], 'NON ESEGUITO')
            run.assert_not_called()

    def test_skipped_output_never_passes(self):
        self.workflow({'probe': self.job([{'run': "print('skipped')", 'shell': 'python'}])})
        self.assertEqual(self.run_plan()['steps'][0]['status'], 'NON ESEGUITO')

    def test_unknown_action_revision_is_not_known(self):
        self.workflow({'probe': self.job([{'uses': 'actions/checkout@unknown'}])})
        self.assertEqual(self.run_plan()['steps'][0]['status'], 'NON ESEGUITO')

    def test_python_version_and_live_commands(self):
        for step in (
            {'uses': 'actions/setup-python@6d4fd22b20465ccc0f7354476588e8df7c9ca0e0',
             'with': {'python-version': '2.7'}},
            {'run': 'docker ps', 'shell': 'python'},
            {'run': 'psql --version', 'shell': 'python'},
            {'run': 'vagrant up', 'shell': 'python'},
        ):
            with self.subTest(step=step):
                self.workflow({'probe': self.job([step])})
                self.assertEqual(self.run_plan()['steps'][0]['status'], 'NON ESEGUITO')

    def test_repository_covers_every_job_and_step(self):
        expected, steps = set(), {}
        for path in (ci.ROOT / '.github/workflows').glob('*.yml'):
            raw = yaml.load(path.read_text(encoding='utf-8'), Loader=yaml.BaseLoader)
            for key, job in raw['jobs'].items():
                source = path.relative_to(ci.ROOT).as_posix() + '/jobs/' + key
                expected.add(source)
                for index, step in enumerate(job.get('steps', [])):
                    steps[f'{source}/steps/{index}'] = step
        plan = ci.derive()
        self.assertEqual({j['source'] for j in plan['jobs']}, expected)
        self.assertEqual({s['source']: s['raw'] for j in plan['jobs'] for s in ci.flatten(j['steps'])}, steps)
        # Controprova: perdere un job o un passo rompe il confronto indipendente.
        self.assertNotEqual({j['source'] for j in plan['jobs'] if j['key'] != 'validate'}, expected)
        actual = dict(steps)
        actual.pop(next(iter(actual)))
        self.assertNotEqual(actual, steps)
        self.assertEqual(len(plan['jobs']), 10)
        self.assertEqual({j['key'] for j in plan['jobs']}, {'validate', 'coverage', 'pip-audit', 'gates'})



if __name__ == '__main__':
    unittest.main()
