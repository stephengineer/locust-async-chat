from locust_async_chat.users.user_pool import UserPool, TestUser


class TestTestUser:
    def test_to_login_payload(self):
        user = TestUser(
            index=1,
            given_name="John",
            surname="Doe1",
            email="john.doe1@locust.com",
            locale="en-US",
        )
        payload = user.to_login_payload()
        assert payload.given_name == "John"
        assert payload.surname == "Doe1"
        assert payload.email == "john.doe1@locust.com"
        assert payload.locale == "en-US"

    def test_to_login_payload_to_dict(self):
        user = TestUser(
            index=1, given_name="A", surname="B", email="a@b.com", locale="fr-FR"
        )
        d = user.to_login_payload().to_dict()
        assert d["givenName"] == "A"
        assert d["surname"] == "B"
        assert d["email"] == "a@b.com"
        assert d["locale"] == "fr-FR"


class TestUserPool:
    def test_acquire_generates_sequential_users(self, default_config):
        pool = UserPool(default_config)
        u1 = pool.acquire()
        u2 = pool.acquire()

        assert u1.index == 1
        assert u2.index == 2
        assert u1.surname == "Doe1"
        assert u2.surname == "Doe2"

    def test_acquire_builds_correct_email(self, default_config):
        pool = UserPool(default_config)
        user = pool.acquire()
        assert user.email == "john.doe1@locust.com"

    def test_size_tracks_acquired_users(self, default_config):
        pool = UserPool(default_config)
        assert pool.size == 0
        pool.acquire()
        pool.acquire()
        assert pool.size == 2

    def test_get_user_by_list_index(self, default_config):
        pool = UserPool(default_config)
        u1 = pool.acquire()
        u2 = pool.acquire()
        assert pool.get_user(0) is u1
        assert pool.get_user(1) is u2

    def test_get_user_returns_none_for_out_of_bounds(self, default_config):
        pool = UserPool(default_config)
        assert pool.get_user(0) is None
        assert pool.get_user(-1) is None

    def test_reset_clears_pool_and_resets_counter(self, default_config):
        pool = UserPool(default_config)
        pool.acquire()
        pool.acquire()
        pool.reset()

        assert pool.size == 0
        u = pool.acquire()
        assert u.index == 1  # counter restarted

    def test_custom_config_affects_user_generation(self):
        from locust_async_chat.config.config import LoadTestConfig

        config = LoadTestConfig(
            sut_login_url="https://example.com/login",
            sut_submit_url="https://example.com/submit",
            user_given_name="Alice",
            user_surname_prefix="Test",
            user_email_domain="test.io",
            user_locale="fr-FR",
        )
        pool = UserPool(config)
        user = pool.acquire()

        assert user.given_name == "Alice"
        assert user.surname == "Test1"
        assert user.email == "alice.test1@test.io"
        assert user.locale == "fr-FR"
