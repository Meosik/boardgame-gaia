"""discord_claude.py: the pure parts (quick-turn routing, conversation turn limit), without Discord."""
import os
import unittest

import discord_claude as bot


class QuickTurnTests(unittest.TestCase):
    def test_quick_prefix_gives_the_question_and_nothing_else_matches(self):
        self.assertEqual(bot.quick_request('!q 101은 언제 끝나?'), '101은 언제 끝나?')
        self.assertEqual(bot.quick_request('!quick  상태  '), '상태')
        self.assertIsNone(bot.quick_request('!q'))
        self.assertIsNone(bot.quick_request('!q   '))
        self.assertIsNone(bot.quick_request('진행해'))
        self.assertIsNone(bot.quick_request('!new'))

    def test_quick_model_defaults_to_sonnet_and_follows_the_environment(self):
        os.environ.pop('CLAUDE_QUICK_MODEL', None)
        self.assertEqual(bot.quick_model(), 'claude-sonnet-5-5')
        os.environ['CLAUDE_QUICK_MODEL'] = 'claude-haiku-5-5'
        try:
            self.assertEqual(bot.quick_model(), 'claude-haiku-5-5')
        finally:
            os.environ.pop('CLAUDE_QUICK_MODEL')

    def test_quick_command_has_no_session_and_no_fallback(self):
        argv = bot.command('claude', None, bot.quick_model(), fallback=False)
        self.assertNotIn('--resume', argv)
        self.assertNotIn('--fallback-model', argv)
        self.assertEqual(argv[argv.index('--model') + 1], 'claude-sonnet-5-5')


class McpTests(unittest.TestCase):
    def test_mcp_servers_are_off_unless_asked_for(self):
        os.environ.pop('CLAUDE_BOT_MCP', None)
        argv = bot.command('claude', 'sid', 'claude-fable-5-1')
        self.assertIn('--strict-mcp-config', argv)
        self.assertEqual(argv[argv.index('--mcp-config') + 1], str(bot.MCP_CONFIG))
        self.assertTrue(bot.MCP_CONFIG.exists())
        import json
        self.assertEqual(json.loads(bot.MCP_CONFIG.read_text()), {'mcpServers': {}})
        os.environ['CLAUDE_BOT_MCP'] = '1'
        try:
            self.assertNotIn('--strict-mcp-config', bot.command('claude', None, 'claude-fable-5-1'))
        finally:
            os.environ.pop('CLAUDE_BOT_MCP')

    def test_review_prompt_reads_the_markdown_and_the_template_only(self):
        prompt = bot.review_prompt('101-ships-vs-menu-full')
        self.assertTrue(prompt.startswith('/lab-review 101-ships-vs-menu-full\n'))
        self.assertIn('lab/results/101-ships-vs-menu-full.md', prompt)
        self.assertIn('TEMPLATE.md', prompt)
        self.assertNotIn('.json을 읽고', prompt)


class CodexTests(unittest.TestCase):
    """User 2026-10-21 "다른 agent의 검수": `!codex` asks the second model directly; a '🔍' review notice with
    findings starts a response turn, a clean one starts nothing."""

    def test_codex_prefix_gives_the_question(self):
        self.assertEqual(bot.codex_request('!codex 이 판정 맞아?'), '이 판정 맞아?')
        self.assertEqual(bot.codex_request('!gpt  왜? '), '왜?')
        self.assertIsNone(bot.codex_request('!codex'))
        self.assertIsNone(bot.codex_request('!q 질문'))
        self.assertIsNone(bot.quick_request('!codex 질문'))

    def test_codex_command_is_read_only_and_writes_its_last_message(self):
        os.environ.pop('CODEX_MODEL', None)
        argv = bot.codex_command('codex', '/work', '/tmp/out.md')
        self.assertEqual(argv[:2], ['codex', 'exec'])
        self.assertEqual(argv[argv.index('--model') + 1], 'gpt-6-astra')
        self.assertEqual(argv[argv.index('--sandbox') + 1], 'read-only')
        self.assertEqual(argv[argv.index('--output-last-message') + 1], '/tmp/out.md')
        self.assertEqual(argv[-1], '-')

    def test_review_notice_with_findings_starts_a_response_and_a_clean_one_does_not(self):
        self.assertEqual(bot.finished_review('🔍 # review-code-abc1234 — 검수\n결론: 지적 2건\n...'),
                         ('review-code-abc1234', True))
        self.assertEqual(bot.finished_review('🔍 # review-code-abc1234 — 검수\n검수자\n\n결론: 이상 없음'),
                         ('review-code-abc1234', False))
        self.assertIsNone(bot.finished_review('✅ # 101-ships — 완료'))
        self.assertIsNone(bot.finished_experiment('🔍 # review-code-abc1234 — 검수'))
        self.assertIn('불일치', bot.respond_prompt('review-code-abc1234'))

    def test_watch_reviews_every_turn_and_hands_objections_to_the_next_one(self):
        """User 2026-10-22 "대화 중간중간에 codex가 개입": the watch prompt carries the message, the reply and the
        commit range; objections are kept per channel and prefixed to the next prompt, a clean answer is not."""
        prompt = bot.watch_prompt('plan_menu는 어떻게 하기로 했어?', '편입 보류입니다.', 'abc1234def', 'bcd2345efa',
                                  'bcd2345 tools: x\n')
        self.assertTrue(prompt.startswith(bot.WATCH_NOTE))
        for part in ('## 사용자\nplan_menu는', '## Claude\n편입 보류', '## 커밋 abc1234..bcd2345', 'git diff abc1234..bcd2345',
                     'bcd2345 tools: x'):
            self.assertIn(part, prompt)
        self.assertIn('## 커밋 없음', bot.watch_prompt('q', 'a', 'same', 'same', ''))
        self.assertEqual(bot.watch_findings('결론: 이상 없음'), '')
        self.assertEqual(bot.watch_findings(''), '')
        self.assertEqual(bot.watch_findings('1. charge_rounds.py:49 경계가 비대칭\n'), '1. charge_rounds.py:49 경계가 비대칭')
        prefix = bot.watch_prefix('1. 지적')
        self.assertTrue(prefix.startswith('(직전 답에 대한 코덱스 검수 지적'))
        self.assertIn('불일치', prefix)
        state = {'1:codex': '1. 지적', '1': 'sess', '1:turns': 2}
        bot.forget(state, '1')
        self.assertEqual(state, {})
        os.environ['CODEX_WATCH'] = '0'
        self.assertFalse(bot.watch_enabled())
        os.environ['CODEX_WATCH'] = '1'
        self.assertTrue(bot.watch_enabled())
        os.environ.pop('CODEX_WATCH', None)
        self.assertTrue(bot.watch_enabled())
        os.environ.pop('CODEX_WATCH_MINUTES', None)
        self.assertEqual(bot.watch_minutes(), 5.0)


class TurnLimitTests(unittest.TestCase):
    def test_turns_count_per_conversation_and_reset_on_a_new_one(self):
        state = {}
        self.assertEqual(bot.count_turn(state, 'c', resumed=False), 1)
        self.assertEqual(bot.count_turn(state, 'c', resumed=True), 2)
        self.assertEqual(bot.count_turn(state, 'c', resumed=True), 3)
        self.assertEqual(bot.count_turn(state, 'c', resumed=False), 1)  # a fresh conversation starts over
        self.assertEqual(state['c:turns'], 1)

    def test_forget_drops_every_key_of_the_conversation(self):
        state = {'c': 'sid', 'c:model': 'claude-fable-5-1', 'c:turns': 10, 'd': 'other'}
        bot.forget(state, 'c')
        self.assertEqual(state, {'d': 'other'})

    def test_limit_defaults_to_ten_and_follows_the_environment(self):
        os.environ.pop('CLAUDE_SESSION_TURNS', None)
        self.assertEqual(bot.session_turn_limit(), 10)
        os.environ['CLAUDE_SESSION_TURNS'] = '3'
        try:
            self.assertEqual(bot.session_turn_limit(), 3)
        finally:
            os.environ.pop('CLAUDE_SESSION_TURNS')


if __name__ == '__main__':
    unittest.main()
