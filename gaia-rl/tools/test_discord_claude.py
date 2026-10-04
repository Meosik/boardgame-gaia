"""lab/discord_claude.py: reply parsing, Discord chunking and the claude command line."""
import json
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'lab'))
import discord_claude as bot  # noqa: E402


class DiscordClaudeTests(unittest.TestCase):
    def test_reply_reports_refused_tools_and_keeps_the_session(self):
        out = json.dumps({'type': 'result', 'subtype': 'success', 'is_error': False, 'result': '확인했습니다.',
                          'session_id': 'abc', 'permission_denials': [
                              {'tool_name': 'Bash', 'tool_input': {'command': 'docker compose -p gaia restart'}},
                              {'tool_name': 'Bash', 'tool_input': {'command': 'docker compose -p gaia restart'}}]})
        text, session = bot.summarize(out, '', 0)
        self.assertEqual(session, 'abc')
        self.assertIn('확인했습니다.', text)
        self.assertEqual(text.count('docker compose -p gaia restart'), 1)

    def test_non_json_output_is_an_error_without_a_session(self):
        text, session = bot.summarize('', 'boom', 1)
        self.assertIsNone(session)
        self.assertIn('boom', text)

    def test_command_resumes_only_with_a_session_and_never_bypasses_permissions(self):
        fresh, resumed = bot.command('claude', None), bot.command('claude', 's1')
        self.assertNotIn('--resume', fresh)
        self.assertEqual(resumed[-2:], ['--resume', 's1'])
        self.assertEqual(fresh[fresh.index('--permission-mode')+1], 'dontAsk')
        settings = json.loads(bot.SETTINGS.read_text())['permissions']
        self.assertIn('Bash(docker compose -p gaia up:*)', settings['deny'])
        self.assertIn('Read(**/.env)', settings['deny'])

    def test_chunks_fit_discord_and_keep_fences_closed(self):
        parts = bot.chunks('a\n```\n' + '\n'.join(['x' * 80] * 60) + '\n```\nb', size=500)
        self.assertGreater(len(parts), 1)
        self.assertTrue(all(len(p) <= 520 and p.count('```') % 2 == 0 for p in parts))


if __name__ == '__main__':
    unittest.main()
