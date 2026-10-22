"""discord_claude.py: the pure parts (quick-turn routing, Codex-bot routing, conversation turn limit), without Discord."""
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


class SecondModelTests(unittest.TestCase):
    """User 2026-10-21 "다른 agent의 검수" → 2026-10-22 "claude는 내부에서 codex 호출하는건 없애되, codex봇이 claude의 말에
    반박하는 체계는 유지": this bot calls no Codex; it routes Codex-addressed messages away, answers lab's 🔍 review
    notices and hands the Codex bot's channel objections to Claude."""

    def test_messages_for_the_codex_bot_are_routed_away(self):
        self.assertEqual(bot.codex_request('!codex 이 판정 맞아?'), '이 판정 맞아?')
        self.assertEqual(bot.codex_request('!codex !status'), '!status')
        self.assertIsNone(bot.codex_request('!codex'))
        self.assertIsNone(bot.codex_request('!q 질문'))
        self.assertIsNone(bot.quick_request('!codex 질문'))
        self.assertTrue(bot.addressed_to_other_bot('!codex 왜?', False))
        self.assertTrue(bot.addressed_to_other_bot('<@42> 네 생각은?', True))
        self.assertFalse(bot.addressed_to_other_bot('진행해', False))
        self.assertFalse(bot.addressed_to_other_bot('!status', False))
        self.assertFalse(hasattr(bot, 'codex_command'))   # no in-process Codex left

    def test_review_notice_with_findings_starts_a_response_and_a_clean_one_does_not(self):
        self.assertEqual(bot.finished_review('🔍 # review-code-abc1234 — 검수\n결론: 지적 2건\n...'),
                         ('review-code-abc1234', True))
        self.assertEqual(bot.finished_review('🔍 # review-code-abc1234 — 검수\n검수자\n\n결론: 이상 없음'),
                         ('review-code-abc1234', False))
        self.assertIsNone(bot.finished_review('✅ # 101-ships — 완료'))
        self.assertIsNone(bot.finished_experiment('🔍 # review-code-abc1234 — 검수'))
        self.assertIn('불일치', bot.respond_prompt('review-code-abc1234'))

    def test_objections_since_the_last_reply_are_collected_and_prefixed_to_the_next_prompt(self):
        rows = [  # newest first, as the channel history comes
            (False, True, '답입니다\n🧠 gpt-6-astra · 읽기 전용'),           # Codex's answer to the owner: not an objection
            (False, False, '<@42> 네 생각은?'),                               # the owner
            (False, True, '🔍 (계속)\n2. 둘째 지적'),
            (False, True, '🔍 코덱스(gpt-6-astra) 검수 지적 — 다음 메시지에서 Claude가 받는다\n1. 첫 지적'),
            (True, False, '제 답'),                                            # this bot's last reply: stop here
            (False, True, '🔍 코덱스(gpt-6-astra) 검수 지적\n0. 옛 지적'),
        ]
        self.assertEqual(bot.objections_from(rows), '1. 첫 지적\n2. 둘째 지적')
        self.assertEqual(bot.objections_from([(False, True, '🔍 코덱스(gpt-6-astra): 이상 없음'), (True, False, 'x')]), '')
        prefix = bot.watch_prefix('1. 지적')
        self.assertTrue(prefix.startswith('(직전 답에 대한 코덱스 검수 지적'))
        self.assertIn('불일치', prefix)
        state = {'1': 'sess', '1:turns': 2, '1:model': 'm'}
        bot.forget(state, '1')
        self.assertEqual(state, {})


class DebateTests(unittest.TestCase):
    """User 2026-10-22 "둘이 따로 생각하고, 나온 의견을 가지고 토론하는 모습": independent answers, then DEBATE_ROUNDS
    rounds that this bot answers at once; `!solo` keeps Codex out."""

    def test_solo_prefix_gives_the_text_and_rounds_follow_the_environment(self):
        self.assertEqual(bot.solo_request('!solo 이건 너만 답해'), '이건 너만 답해')
        self.assertIsNone(bot.solo_request('!solo'))
        self.assertIsNone(bot.solo_request('진행해'))
        self.assertIsNone(bot.quick_request('!solo 질문'))
        self.assertFalse(bot.addressed_to_other_bot('!solo 질문', False))
        os.environ.pop('DEBATE_ROUNDS', None)
        self.assertEqual(bot.debate_rounds(), 1)
        for value, rounds in (('0', 0), ('2', 2), ('-1', 0), ('x', 1)):
            os.environ['DEBATE_ROUNDS'] = value
            try:
                self.assertEqual(bot.debate_rounds(), rounds)
            finally:
                os.environ.pop('DEBATE_ROUNDS')

    def test_only_the_first_part_of_a_round_with_objections_opens_a_debate_turn(self):
        self.assertEqual(bot.debate_round_of('🔍 코덱스(gpt-6-astra) 토론 1/1 — Claude가 바로 답한다\n1. 지적'), (1, 1))
        self.assertEqual(bot.debate_round_of('🔍 코덱스(m) 토론 2/3 — Claude가 바로 답한다\n1. 재반박'), (2, 3))
        self.assertIsNone(bot.debate_round_of('🔍 코덱스(gpt-6-astra) 토론 1/1: 이상 없음'))
        self.assertIsNone(bot.debate_round_of('🔍 (계속)\n2. 둘째'))
        self.assertIsNone(bot.debate_round_of('🔍 코덱스(gpt-6-astra) 검수 지적 — 다음 메시지에서 Claude가 받는다\n1. 지적'))
        self.assertIsNone(bot.debate_round_of('💭 코덱스(gpt-6-astra) 독립 답\n제 생각은…\n🧠 gpt-6-astra · 읽기 전용'))
        self.assertIsNone(bot.debate_round_of('🔍 # review-code-abc — 검수 (토론 아님)'))
        self.assertIsNone(bot.debate_round_of(''))

    def test_debate_reply_prompt_asks_for_fixes_or_rebuttals_under_the_round_header(self):
        prompt = bot.debate_reply_prompt('1. 첫 지적', 1, 1)
        self.assertTrue(prompt.startswith('(토론 1/1:'))
        self.assertIn('🗣️ 토론 1/1', prompt)
        self.assertIn('불일치', prompt)
        self.assertTrue(prompt.endswith('1. 첫 지적\n'))
        # the independent answer (💭) is not an objection; a round's parts are collected like the watch's
        rows = [(False, True, '🔍 (계속)\n2. 둘째'), (False, True, '🔍 코덱스(m) 토론 1/1 — Claude가 바로 답한다\n1. 첫째'),
                (False, True, '💭 코덱스(m) 독립 답\n내 답\n🧠 m · 읽기 전용'), (True, False, '제 답')]
        self.assertEqual(bot.objections_from(rows), '1. 첫째\n2. 둘째')
        self.assertIn('토론', bot.SYSTEM)

    def test_only_the_codex_bot_opens_debate_turns_when_its_id_is_set(self):
        """Debate 1/1 objection 2026-10-22: without CODEX_BOT_ID any bot in the channel could open a Claude turn."""
        self.assertTrue(bot.from_codex(7, True, None, 1, 0))      # any other bot when no id is configured
        self.assertTrue(bot.from_codex(7, True, None, 1, 7))
        self.assertFalse(bot.from_codex(8, True, None, 1, 7))     # another bot
        self.assertFalse(bot.from_codex(1, True, None, 1, 0))     # this bot itself
        self.assertFalse(bot.from_codex(7, True, 99, 1, 7))       # a webhook (lab)
        self.assertFalse(bot.from_codex(7, False, None, 1, 7))    # a person


class SecretEnvTests(unittest.TestCase):
    def test_model_subprocesses_do_not_inherit_tokens(self):
        """User 2026-10-22 "토큰을 분리하지 않아도 괜찮나?": one env file for both bots is fine only if `claude -p`
        and `codex exec` never see the tokens."""
        env = {'DISCORD_BOT_TOKEN': 'a', 'CODEX_BOT_TOKEN': 'b', 'DISCORD_LAB_WEBHOOK_ID': 'c', 'OPENAI_API_KEY': 'd',
               'PATH': '/bin', 'GAIA_WORKDIR': '/w', 'CODEX_MODEL': 'm', 'DISCORD_OWNER_ID': '1'}
        self.assertEqual(bot.clean_env(env), {'PATH': '/bin', 'GAIA_WORKDIR': '/w', 'CODEX_MODEL': 'm', 'DISCORD_OWNER_ID': '1'})
        self.assertNotIn('DISCORD_BOT_TOKEN', bot.clean_env({**os.environ, 'DISCORD_BOT_TOKEN': 'x'}))


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
