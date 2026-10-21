"""discord_codex.py: the pure parts (addressing, commands, context, watch prompt and messages), without Discord."""
import os
import unittest

import discord_claude as shared
import discord_codex as bot


class AddressingTests(unittest.TestCase):
    def test_a_mention_or_the_codex_prefix_addresses_this_bot_and_other_messages_do_not(self):
        self.assertEqual(bot.question_of('<@42> 분리에 대해 어떻게 생각해', 42), '분리에 대해 어떻게 생각해')
        self.assertEqual(bot.question_of('앞 문장 <@!42> 뒤 문장', 42), '앞 문장  뒤 문장')
        self.assertIsNone(bot.question_of('<@42>', 42))                    # a bare mention: nothing to answer
        self.assertIsNone(bot.question_of('<@7> 너 말이야', 42))            # someone else mentioned
        self.assertEqual(bot.question_of('!codex 왜?', 42), '왜?')
        self.assertIsNone(bot.question_of('!gpt 왜?', 42))                 # one prefix only (2026-10-22 "양식 통일")
        self.assertIsNone(bot.question_of('진행해', 42))
        self.assertIsNone(bot.question_of('!new', 42))                      # Claude's command, not ours

    def test_the_same_commands_as_the_claude_bot_when_addressed(self):
        self.assertEqual(bot.command_of(bot.question_of('<@42> !status', 42)), '!status')
        self.assertEqual(bot.command_of(bot.question_of('!codex !stop', 42)), '!stop')
        self.assertEqual(bot.command_of('!new'), '!new')
        self.assertIsNone(bot.command_of('왜?'))
        self.assertIsNone(bot.command_of('!q 질문'))

    def test_codex_command_is_read_only_and_writes_its_last_message(self):
        os.environ.pop('CODEX_MODEL', None)
        argv = bot.codex_command('codex', '/work', '/tmp/out.md')
        self.assertEqual(argv[:2], ['codex', 'exec'])
        self.assertEqual(argv[argv.index('--model') + 1], 'gpt-6-astra')
        self.assertEqual(argv[argv.index('--sandbox') + 1], 'read-only')
        self.assertEqual(argv[argv.index('--output-last-message') + 1], '/tmp/out.md')
        self.assertEqual(argv[-1], '-')

    def test_question_prompt_is_read_only_and_carries_the_recent_conversation(self):
        context = bot.context_block([('사용자', '분리하자'), ('Claude', '조건부 찬성  입니다'), ('Codex', '')])
        self.assertEqual(context, '## 최근 대화 (오래된 것부터)\n- 사용자: 분리하자\n- Claude: 조건부 찬성 입니다\n\n')
        self.assertEqual(bot.context_block([]), '')
        self.assertEqual(bot.context_block([('a', 'x'*700)], each=600).count('x'), 600)
        prompt = bot.question_prompt('네 생각은?', context)
        self.assertTrue(prompt.startswith(bot.QUESTION_NOTE))
        self.assertIn('읽기 전용', prompt)
        self.assertIn('## 최근 대화', prompt)
        self.assertIn('## 질문\n네 생각은?', prompt)


class WatchTests(unittest.TestCase):
    def test_watch_prompt_carries_the_message_the_reply_and_the_commit_range(self):
        """User 2026-10-22 "대화 중간중간에 codex가 개입" — kept when Codex became its own bot."""
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

    def test_findings_are_posted_as_marked_messages_the_claude_bot_can_collect(self):
        parts = bot.findings_messages('1. 첫 지적\n2. 둘째', 'gpt-6-astra')
        self.assertEqual(len(parts), 1)
        self.assertTrue(parts[0].startswith('🔍 코덱스(gpt-6-astra) 검수 지적'))
        self.assertEqual(shared.objections_from([(False, True, parts[0]), (True, False, 'reply')]), '1. 첫 지적\n2. 둘째')
        long = bot.findings_messages('\n'.join(f'{i}. 지적 ' + 'x'*80 for i in range(40)), 'm')
        self.assertGreater(len(long), 1)
        self.assertTrue(all(p.startswith('🔍') for p in long))
        self.assertTrue(long[1].startswith(bot.CONTINUED))
        rows = [(False, True, p) for p in reversed(long)] + [(True, False, 'reply')]
        self.assertEqual(shared.objections_from(rows).count('. 지적'), 40)

    def test_one_off_claude_answers_are_not_reviewed_and_settings_follow_the_environment(self):
        self.assertTrue(bot.is_one_off('답\n🧠 Sonnet 5.5 · 일회성 답(본 대화에 안 남음)'))
        self.assertFalse(bot.is_one_off('보통 답\n🧠 Fable 5.1'))
        for name in ('CODEX_WATCH', 'CODEX_WATCH_MINUTES', 'CODEX_WATCH_DELAY', 'CODEX_TURN_MINUTES', 'CODEX_CONTEXT'):
            os.environ.pop(name, None)
        self.assertTrue(bot.watch_enabled())
        self.assertEqual(bot.watch_minutes(), 5.0)
        self.assertEqual(bot.watch_delay(), 20.0)
        self.assertEqual(bot.turn_minutes(), 10.0)
        self.assertEqual(bot.context_size(), 12)
        os.environ['CODEX_WATCH'] = '0'
        os.environ['CODEX_WATCH_DELAY'] = '5'
        try:
            self.assertFalse(bot.watch_enabled())
            self.assertEqual(bot.watch_delay(), 5.0)
        finally:
            os.environ.pop('CODEX_WATCH')
            os.environ.pop('CODEX_WATCH_DELAY')


if __name__ == '__main__':
    unittest.main()
