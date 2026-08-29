import unittest

from adapters.deepseek_web import (
    DeepSeekWebError,
    parse_json_response,
    parse_marked_json_response,
    select_new_json_candidate,
)


class DeepSeekWebTests(unittest.TestCase):
    def test_real_response_shape_is_parsed(self):
        value = parse_json_response('{"type":"tool_call","id":"call_001","tool":"list_files","arguments":{"path":".","recursive":false}}')
        self.assertEqual(value["tool"], "list_files")

    def test_markdown_fence_is_tolerated(self):
        value = parse_json_response('```json\n{"type":"final","content":"done"}\n```')
        self.assertEqual(value["type"], "final")

    def test_fenced_python_dunder_content_is_preserved(self):
        value = parse_json_response(
            '```json\n{"type":"tool_call","id":"1","tool":"create_text_file","arguments":{"path":"x.py","lines":["if __name__ == \'__main__\':"]}}\n```'
        )
        self.assertEqual(value["arguments"]["lines"][0], "if __name__ == '__main__':")

    def test_non_json_is_rejected(self):
        with self.assertRaises(DeepSeekWebError):
            parse_json_response("I cannot comply")

    def test_unescaped_quotes_are_rejected_instead_of_guessed(self):
        with self.assertRaises(DeepSeekWebError):
            parse_json_response('{"type":"final","content":"changed "before" to "after""}')

    def test_finds_new_json_when_virtualized_count_is_unchanged(self):
        old = '{"type":"tool_call","id":"4"}'
        new = '{"type":"tool_call","id":"5"}'
        texts = ["ordinary user prompt", old, new]
        self.assertEqual(select_new_json_candidate(texts, {old}), new)

    def test_resurfaced_old_json_is_not_selected(self):
        old = '{"type":"tool_call","id":"1"}'
        self.assertEqual(select_new_json_candidate([old], {old}), "")

    def test_only_current_turn_candidate_is_selected(self):
        old = '{"type":"final","content":"same","_turn":"old-turn"}'
        new = '{"type":"final","content":"same","_turn":"new-turn"}'
        self.assertEqual(select_new_json_candidate([old, new], set(), "new-turn"), new)

    def test_turn_marker_is_validated_and_removed(self):
        value = parse_marked_json_response(
            '{"type":"final","content":"done","_turn":"abc"}', "abc"
        )
        self.assertEqual(value, {"type": "final", "content": "done"})
        with self.assertRaises(DeepSeekWebError):
            parse_marked_json_response(
                '{"type":"final","content":"done","_turn":"old"}', "new"
            )


if __name__ == "__main__":
    unittest.main()
