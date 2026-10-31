"""Day 27 — Python + Streaming: Kafka / Event Hub producers & consumers.

Second bridge day into the streaming blocks: the pipeline stops being a
batch job that runs and exits, and becomes a stream that never ends.
No real broker, no network — every topic is an in-memory model of the
broker contract, so the tests run offline. Stdlib only.
"""
