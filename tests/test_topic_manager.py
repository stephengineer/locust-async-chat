from locust_async_chat.providers.ai.topic_manager import TopicManager, Topic


class TestTopicManagerRoundRobin:
    def test_cycles_through_topics(self):
        topics = [
            Topic(name="a", description="A"),
            Topic(name="b", description="B"),
            Topic(name="c", description="C"),
        ]
        mgr = TopicManager(predefined_topics=topics, selection_strategy="round_robin")

        assert mgr.select_topic().name == "a"
        assert mgr.select_topic().name == "b"
        assert mgr.select_topic().name == "c"
        assert mgr.select_topic().name == "a"  # wraps around

    def test_single_topic_always_returns_same(self):
        topics = [Topic(name="only", description="Only one")]
        mgr = TopicManager(predefined_topics=topics, selection_strategy="round_robin")
        for _ in range(5):
            assert mgr.select_topic().name == "only"


class TestTopicManagerRandom:
    def test_returns_from_topic_list(self):
        topics = [Topic(name="x", description="X"), Topic(name="y", description="Y")]
        mgr = TopicManager(
            predefined_topics=topics, selection_strategy="random", seed=42
        )
        selected = mgr.select_topic()
        assert selected.name in ("x", "y")

    def test_deterministic_with_seed(self):
        topics = [Topic(name="a", description="A"), Topic(name="b", description="B")]
        results1 = []
        results2 = []
        for seed_val in (99,):
            mgr = TopicManager(
                predefined_topics=topics, selection_strategy="random", seed=seed_val
            )
            results1 = [mgr.select_topic().name for _ in range(10)]
            mgr2 = TopicManager(
                predefined_topics=topics, selection_strategy="random", seed=seed_val
            )
            results2 = [mgr2.select_topic().name for _ in range(10)]
        assert results1 == results2


class TestTopicManagerEmpty:
    def test_empty_list_falls_back_to_defaults(self):
        # [] is falsy, so `predefined_topics or DEFAULT_TOPICS` uses defaults
        mgr = TopicManager(predefined_topics=[])
        assert len(mgr.topics) == len(TopicManager.DEFAULT_TOPICS)

    def test_none_uses_defaults(self):
        mgr = TopicManager(predefined_topics=None)
        assert mgr.topics is TopicManager.DEFAULT_TOPICS


class TestTopicManagerAddAndGet:
    def test_add_topic(self):
        topics = [Topic(name="base", description="Base")]
        mgr = TopicManager(predefined_topics=topics)
        mgr.add_topic(Topic(name="new", description="New topic"))
        assert len(mgr.topics) == 2
        assert mgr.get_topic_by_name("new") is not None

    def test_get_topic_by_name(self):
        topics = [
            Topic(name="pricing_question", description="Pricing", category="sales"),
        ]
        mgr = TopicManager(predefined_topics=topics)
        topic = mgr.get_topic_by_name("pricing_question")
        assert topic is not None
        assert topic.category == "sales"

    def test_get_topic_by_name_not_found(self):
        mgr = TopicManager(predefined_topics=[Topic(name="a", description="A")])
        assert mgr.get_topic_by_name("nonexistent") is None


class TestDefaultTopics:
    def test_default_topics_exist(self):
        assert len(TopicManager.DEFAULT_TOPICS) >= 8

    def test_all_defaults_have_names_and_descriptions(self):
        for topic in TopicManager.DEFAULT_TOPICS:
            assert topic.name
            assert topic.description
            assert topic.category
