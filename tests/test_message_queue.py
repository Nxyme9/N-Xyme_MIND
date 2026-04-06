"""Tests for SQLite-based message queue."""

import json
import tempfile
import time
from pathlib import Path

import pytest

from src.orchestration.message_queue.message_queue import MessageQueue, MessagePriority


@pytest.fixture
def temp_db_path(tmp_path):
    return tmp_path / "test_queue.db"


@pytest.fixture
def mq(temp_db_path):
    queue = MessageQueue(
        db_path=temp_db_path, visibility_timeout=1, max_retries=3, default_ttl=60
    )
    yield queue
    queue.close()


class TestMessageEnqueue:
    def test_enqueue_string_message(self, mq):
        msg_id = mq.enqueue("test message")
        assert msg_id is not None
        assert len(msg_id) > 0

    def test_enqueue_dict_message(self, mq):
        body = {"task": "process_data", "user": "alice"}
        msg_id = mq.enqueue(body)
        msg = mq.get_message(msg_id)
        assert msg is not None
        assert json.loads(msg.body) == body

    def test_enqueue_with_high_priority(self, mq):
        msg_id = mq.enqueue("high priority", priority=MessagePriority.HIGH)
        msg = mq.get_message(msg_id)
        assert msg.priority == MessagePriority.HIGH

    def test_enqueue_with_low_priority(self, mq):
        msg_id = mq.enqueue("low priority", priority=MessagePriority.LOW)
        msg = mq.get_message(msg_id)
        assert msg.priority == MessagePriority.LOW

    def test_enqueue_with_string_priority(self, mq):
        msg_id = mq.enqueue("test", priority="high")
        msg = mq.get_message(msg_id)
        assert msg.priority == MessagePriority.HIGH

    def test_enqueue_with_custom_ttl(self, mq):
        msg_id = mq.enqueue("test", ttl_seconds=120)
        msg = mq.get_message(msg_id)
        assert msg.ttl_seconds == 120

    def test_enqueue_with_custom_max_retries(self, mq):
        msg_id = mq.enqueue("test", max_retries=5)
        msg = mq.get_message(msg_id)
        assert msg.max_retries == 5

    def test_enqueue_with_custom_id(self, mq):
        custom_id = "my-custom-id"
        msg_id = mq.enqueue("test", message_id=custom_id)
        assert msg_id == custom_id


class TestMessageDequeue:
    def test_dequeue_returns_message(self, mq):
        mq.enqueue("test message")
        msg = mq.dequeue("worker-1")
        assert msg is not None
        assert msg.body == "test message"
        assert msg.status == "processing"
        assert msg.consumer_id == "worker-1"

    def test_dequeue_empty_queue_returns_none(self, mq):
        msg = mq.dequeue("worker-1")
        assert msg is None

    def test_dequeue_marks_message_processing(self, mq):
        msg_id = mq.enqueue("test")
        msg = mq.dequeue("worker-1")
        stored = mq.get_message(msg_id)
        assert stored.status == "processing"

    def test_dequeue_respects_priority_order(self, mq):
        mq.enqueue("low", priority=MessagePriority.LOW)
        mq.enqueue("high", priority=MessagePriority.HIGH)
        mq.enqueue("normal", priority=MessagePriority.NORMAL)

        first = mq.dequeue("worker-1")
        second = mq.dequeue("worker-2")
        third = mq.dequeue("worker-3")

        assert first.body == "high"
        assert second.body == "normal"
        assert third.body == "low"

    def test_dequeue_same_priority_fifo(self, mq):
        mq.enqueue("first", priority=MessagePriority.NORMAL)
        time.sleep(0.01)
        mq.enqueue("second", priority=MessagePriority.NORMAL)
        time.sleep(0.01)
        mq.enqueue("third", priority=MessagePriority.NORMAL)

        first = mq.dequeue("w1")
        second = mq.dequeue("w2")
        third = mq.dequeue("w3")

        assert first.body == "first"
        assert second.body == "second"
        assert third.body == "third"

    def test_multiple_consumers(self, mq):
        mq.enqueue("msg1")
        mq.enqueue("msg2")

        msg1 = mq.dequeue("consumer-a")
        msg2 = mq.dequeue("consumer-b")

        assert msg1.consumer_id == "consumer-a"
        assert msg2.consumer_id == "consumer-b"
        assert msg1.id != msg2.id


class TestAcknowledgment:
    def test_ack_removes_message(self, mq):
        msg_id = mq.enqueue("test")
        mq.dequeue("worker-1")
        result = mq.ack(msg_id)
        assert result is True
        assert mq.get_message(msg_id) is None

    def test_ack_non_processing_message_fails(self, mq):
        msg_id = mq.enqueue("test")
        result = mq.ack(msg_id)
        assert result is False

    def test_ack_unknown_message_fails(self, mq):
        result = mq.ack("nonexistent")
        assert result is False


class TestNegativeAcknowled:
    def test_nack_requeues_message(self, mq):
        msg_id = mq.enqueue("test")
        mq.dequeue("worker-1")
        result = mq.nack(msg_id, requeue=True)
        assert result is True
        msg = mq.get_message(msg_id)
        assert msg.status == "pending"
        assert msg.retries == 1

    def test_nack_moves_to_dead_letter_after_max_retries(self, mq):
        msg_id = mq.enqueue("test", max_retries=1)
        mq.dequeue("worker-1")
        mq.nack(msg_id, requeue=True)
        dead_letters = mq.get_dead_letters()
        assert len(dead_letters) == 1
        assert dead_letters[0].id == msg_id
        assert mq.get_message(msg_id) is None

    def test_nack_without_requeue(self, mq):
        msg_id = mq.enqueue("test")
        mq.dequeue("worker-1")
        mq.nack(msg_id, requeue=False)
        dead_letters = mq.get_dead_letters()
        assert len(dead_letters) == 1

    def test_nack_non_processing_message_fails(self, mq):
        msg_id = mq.enqueue("test")
        result = mq.nack(msg_id)
        assert result is False


class TestQueueDepth:
    def test_queue_depth_increments(self, mq):
        assert mq.get_queue_depth() == 0
        mq.enqueue("msg1")
        mq.enqueue("msg2")
        assert mq.get_queue_depth() == 2

    def test_queue_depth_decrements_on_dequeue(self, mq):
        mq.enqueue("msg1")
        mq.enqueue("msg2")
        mq.dequeue("worker-1")
        assert mq.get_queue_depth() == 1

    def test_queue_depth_by_priority(self, mq):
        mq.enqueue("high", priority=MessagePriority.HIGH)
        mq.enqueue("normal1", priority=MessagePriority.NORMAL)
        mq.enqueue("normal2", priority=MessagePriority.NORMAL)
        mq.enqueue("low", priority=MessagePriority.LOW)

        depth = mq.get_queue_depth_by_priority()
        assert depth["high"] == 1
        assert depth["normal"] == 2
        assert depth["low"] == 1


class TestDeadLetterQueue:
    def test_dead_letters_after_max_retries(self, mq):
        msg_id = mq.enqueue("test", max_retries=2)
        for _ in range(2):
            mq.dequeue("worker-1")
            mq.nack(msg_id, requeue=True)
        dead_letters = mq.get_dead_letters()
        assert len(dead_letters) == 1

    def test_requeue_dead_letter(self, mq):
        msg_id = mq.enqueue("test", max_retries=1)
        mq.dequeue("worker-1")
        mq.nack(msg_id, requeue=True)
        assert len(mq.get_dead_letters()) == 1
        result = mq.requeue_dead_letter(msg_id)
        assert result is True
        assert len(mq.get_dead_letters()) == 0
        msg = mq.get_message(msg_id)
        assert msg is not None
        assert msg.status == "pending"
        assert msg.retries == 0

    def test_delete_dead_letter(self, mq):
        msg_id = mq.enqueue("test", max_retries=1)
        mq.dequeue("worker-1")
        mq.nack(msg_id, requeue=False)
        result = mq.delete_dead_letter(msg_id)
        assert result is True
        assert len(mq.get_dead_letters()) == 0


class TestTTLExpiration:
    def test_purge_expired_messages(self, mq):
        short_ttl_mq = MessageQueue(db_path=mq._db_path, default_ttl=1)
        short_ttl_mq.enqueue("expires soon")
        time.sleep(1.1)
        deleted = short_ttl_mq.purge_expired()
        assert deleted == 1
        short_ttl_mq.close()

    def test_expired_messages_not_dequeued(self, mq):
        very_short_mq = MessageQueue(db_path=mq._db_path, default_ttl=1)
        very_short_mq.enqueue("will expire")
        time.sleep(1.1)
        msg = very_short_mq.dequeue("worker-1")
        assert msg is None
        very_short_mq.close()


class TestQueueStats:
    def test_stats_empty_queue(self, mq):
        stats = mq.get_stats()
        assert stats["pending"] == 0
        assert stats["processing"] == 0
        assert stats["dead_letters"] == 0

    def test_stats_with_messages(self, mq):
        mq.enqueue("msg1")
        mq.enqueue("msg2")
        msg = mq.dequeue("worker-1")
        stats = mq.get_stats()
        assert stats["pending"] == 1
        assert stats["processing"] == 1
        assert stats["total_messages"] == 2


class TestMessagePersistence:
    def test_messages_survive_restart(self, temp_db_path):
        mq1 = MessageQueue(db_path=temp_db_path)
        msg_id = mq1.enqueue("persistent message", priority=MessagePriority.HIGH)
        mq1.close()

        mq2 = MessageQueue(db_path=temp_db_path)
        msg = mq2.get_message(msg_id)
        assert msg is not None
        assert msg.body == "persistent message"
        assert msg.priority == MessagePriority.HIGH
        mq2.close()


class TestMessageClass:
    def test_message_to_dict(self):
        from src.orchestration.message_queue.message_queue import Message

        msg = Message(
            id="test-1",
            body="hello",
            priority=MessagePriority.HIGH,
        )
        d = msg.to_dict()
        assert d["id"] == "test-1"
        assert d["body"] == "hello"
        assert d["priority"] == "high"

    def test_message_is_expired(self):
        from src.orchestration.message_queue.message_queue import Message

        msg = Message(
            id="test-1",
            body="hello",
            priority=MessagePriority.NORMAL,
            created_at=time.time() - 100,
            ttl_seconds=10,
        )
        assert msg.is_expired() is True

    def test_message_is_not_expired(self):
        from src.orchestration.message_queue.message_queue import Message

        msg = Message(
            id="test-1",
            body="hello",
            priority=MessagePriority.NORMAL,
            created_at=time.time(),
            ttl_seconds=3600,
        )
        assert msg.is_expired() is False
