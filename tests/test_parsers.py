from locust_async_chat.models.parsers import parse_correlation_id, parse_conversation_id


class TestParseCorrelationId:
    def test_extracts_from_nested_payload(self):
        resp = {"payload": {"message": {"metadata": {"correlationID": "corr-123"}}}}
        assert parse_correlation_id(resp) == "corr-123"

    def test_converts_non_string_to_string(self):
        resp = {"payload": {"message": {"metadata": {"correlationID": 12345}}}}
        assert parse_correlation_id(resp) == "12345"

    def test_returns_none_for_empty_dict(self):
        assert parse_correlation_id({}) is None

    def test_returns_none_when_metadata_missing(self):
        resp = {"payload": {"message": {}}}
        assert parse_correlation_id(resp) is None

    def test_returns_none_when_correlation_id_is_empty_string(self):
        resp = {"payload": {"message": {"metadata": {"correlationID": ""}}}}
        assert parse_correlation_id(resp) is None

    def test_returns_none_when_payload_missing(self):
        resp = {"other": "data"}
        assert parse_correlation_id(resp) is None


class TestParseConversationId:
    def test_extracts_first_conversation_id(self):
        resp = {
            "conversations": [
                {"id": "conv-001"},
                {"id": "conv-002"},
            ]
        }
        assert parse_conversation_id(resp) == "conv-001"

    def test_converts_non_string_id(self):
        resp = {"conversations": [{"id": 999}]}
        assert parse_conversation_id(resp) == "999"

    def test_returns_none_for_empty_conversations(self):
        resp = {"conversations": []}
        assert parse_conversation_id(resp) is None

    def test_returns_none_when_conversations_missing(self):
        assert parse_conversation_id({}) is None

    def test_returns_none_when_conversations_not_a_list(self):
        resp = {"conversations": "not-a-list"}
        assert parse_conversation_id(resp) is None

    def test_returns_none_when_first_item_has_no_id(self):
        resp = {"conversations": [{"name": "test"}]}
        assert parse_conversation_id(resp) is None

    def test_returns_none_when_first_item_not_dict(self):
        resp = {"conversations": ["string-item"]}
        assert parse_conversation_id(resp) is None
