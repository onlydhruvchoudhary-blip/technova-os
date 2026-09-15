"""In-process pub/sub broker: topic + target filtering, backpressure drop, loop-less safety.

Uses asyncio.run() to drive the loop so no pytest-asyncio dependency is required.
"""
import asyncio

from app.broker import Broker


def test_broadcast_reaches_matching_topic_only():
    async def scenario():
        b = Broker()
        b.bind_loop(asyncio.get_running_loop())
        qa = b.subscribe("activity")
        qn = b.subscribe("notify")
        b.publish("activity", {"x": 1})
        await asyncio.sleep(0.02)  # allow call_soon_threadsafe fanout to run
        return qa.qsize(), qn.qsize(), (await qa.get()).data
    a, n, data = asyncio.run(scenario())
    assert a == 1
    assert n == 0
    assert data == {"x": 1}


def test_targeted_message_only_hits_that_user():
    async def scenario():
        b = Broker()
        b.bind_loop(asyncio.get_running_loop())
        q1 = b.subscribe("notify", user_id=1)
        q2 = b.subscribe("notify", user_id=2)
        b.publish("notify", {"hi": True}, target=1)
        await asyncio.sleep(0.02)
        return q1.qsize(), q2.qsize()
    a, b_ = asyncio.run(scenario())
    assert a == 1
    assert b_ == 0


def test_unsubscribe_stops_delivery():
    async def scenario():
        b = Broker()
        b.bind_loop(asyncio.get_running_loop())
        q = b.subscribe("activity")
        b.unsubscribe(q)
        cnt = b.subscriber_count
        b.publish("activity", {"x": 1})
        await asyncio.sleep(0.02)
        return cnt, q.qsize()
    cnt, size = asyncio.run(scenario())
    assert cnt == 0
    assert size == 0


def test_slow_consumer_is_dropped_not_blocking():
    async def scenario():
        b = Broker()
        b.bind_loop(asyncio.get_running_loop())
        q = b.subscribe("activity")
        for i in range(500):  # exceed maxsize; excess dropped, publisher never blocks/raises
            b.publish("activity", {"i": i})
        await asyncio.sleep(0.05)
        return q.qsize()
    assert asyncio.run(scenario()) <= 200


def test_publish_without_loop_is_silent():
    b = Broker()  # no loop bound — must not raise
    b.publish("activity", {"x": 1})
