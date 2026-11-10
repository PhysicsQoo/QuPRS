"""Network-free tests for the bounded post-upload crates.io confirmation."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from urllib.error import HTTPError, URLError

from scripts.reconcile_crates_io_publish import (
    PublicationNotConfirmed, confirm_published, is_index_propagation_timeout,
)


class FakeResponse:
    status = 200

    def __init__(self, payload):
        self.payload = json.dumps(payload).encode("utf-8")

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def read(self):
        return self.payload


class PublicationConfirmationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.version = "0.15.0-rc.2"
        self.crate = Path(self.temp.name) / f"quprs-{self.version}.crate"
        self.crate.write_bytes(b"same source-and-lockfile archive")
        self.digest = hashlib.sha256(self.crate.read_bytes()).hexdigest()

    def metadata(self, **override):
        record = {"num": self.version, "checksum": self.digest, "yanked": False}
        record.update(override)
        return {"version": record}

    @staticmethod
    def http_error(status):
        return HTTPError("https://crates.io", status, "fake", {}, None)

    def run_events(self, events, attempts=4):
        sequence = list(events)
        polls, sleeps = [], []
        def opener(request, timeout):
            self.assertEqual(request.full_url, f"https://crates.io/api/v1/crates/quprs/{self.version}")
            self.assertEqual(timeout, 12)
            polls.append(request)
            response = sequence.pop(0)
            if isinstance(response, Exception):
                raise response
            return FakeResponse(response)
        confirm_published(self.version, self.crate, attempts=attempts,
                          delay_seconds=0.01, opener=opener, sleeper=sleeps.append)
        return len(polls), sleeps

    def test_immediately_published_exact_archive(self):
        self.assertEqual(self.run_events([self.metadata()])[0], 1)

    def test_eventually_visible_after_404_429_503(self):
        n, delays = self.run_events([
            self.http_error(404), self.http_error(429), self.http_error(503), self.metadata()
        ])
        self.assertEqual(n, 4)
        self.assertEqual(len(delays), 3)

    def test_network_timeout_and_missing_version_fail_after_bounded_attempts(self):
        for event in (URLError("offline"), self.http_error(404)):
            with self.subTest(event=event):
                with self.assertRaises(PublicationNotConfirmed):
                    self.run_events([event] * 3, attempts=3)

    def test_rejected_http_statuses_fail_closed(self):
        for status in (400, 401, 403, 422):
            with self.subTest(status=status):
                with self.assertRaises(PublicationNotConfirmed):
                    self.run_events([self.http_error(status)])

    def test_mismatch_is_never_a_retryable_condition(self):
        for record in (self.metadata(checksum="0" * 64),
                       self.metadata(yanked=True),
                       self.metadata(num="0.15.0-rc.3"),
                       {"other": "not-a-version"}):
            with self.subTest(record=record):
                with self.assertRaises(PublicationNotConfirmed):
                    self.run_events([record])

    def test_requires_proven_index_timeout_when_cargo_exits_nonzero(self):
        self.assertTrue(is_index_propagation_timeout("timed out waiting for package in registry index"))
        self.assertTrue(is_index_propagation_timeout("registry index update timed out"))
        for log in ("error: HTTP 403 Forbidden",
                    "error: upload network timeout",
                    "error: failed compiling crate",
                    "index timed out; 401 Unauthorized"):
            with self.subTest(log=log):
                self.assertFalse(is_index_propagation_timeout(log))

    def test_invalid_version_is_not_sent_to_network(self):
        with self.assertRaises(PublicationNotConfirmed):
            confirm_published("../0.15.0", self.crate, opener=lambda *_args: None)


if __name__ == "__main__":
    unittest.main()
