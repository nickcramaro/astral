"""Streaming audio buffer — sentence-level TTS from raw text deltas.

Receives raw DM text deltas (with markers), detects sentence boundaries,
fires TTS concurrently per sentence, and delivers audio messages in text order.
"""

import asyncio
import logging
import re
from typing import Callable, Coroutine

from app.audio.pipeline import AudioPipeline
from app.orchestrator.parser import MARKER_PATTERN, Segment

log = logging.getLogger(__name__)

# Sentence-ending punctuation: period (not ellipsis), !, or ?
# followed by optional closing quote and whitespace
SENTENCE_END = re.compile(r'(?<!\.)([.!?])["\']?\s')


class StreamingAudioBuffer:
    """Accumulates raw DM deltas and fires TTS as sentences complete.

    Audio tasks start concurrently but results are delivered in FIFO order
    so the frontend voice queue receives clips matching text order.
    """

    def __init__(
        self,
        pipeline: AudioPipeline,
        send_fn: Callable[[dict], Coroutine],
    ):
        self._pipeline = pipeline
        self._send = send_fn
        self._raw_buf = ""
        self._scan_pos = 0
        self._seg_type = "narrate"  # Current voice context
        self._seg_meta = ""         # NPC name when seg_type == "npc"
        self._voice_buf = ""        # Accumulating sentence text
        self._queue: asyncio.Queue[asyncio.Task | None] = asyncio.Queue()
        self._drain_task = asyncio.create_task(self._drain())
        self.sent_messages: list[dict] = []  # For opening cache

    def feed(self, raw_delta: str) -> None:
        """Accept a raw text delta. Non-blocking — fires TTS tasks as sentences complete."""
        self._raw_buf += raw_delta
        self._scan()

    async def flush(self) -> None:
        """Flush remaining voice text and wait for all audio to complete."""
        # Generate audio for any remaining text in voice buffer
        text = self._voice_buf.strip()
        if text:
            self._enqueue_voice(text)
            self._voice_buf = ""

        # Sentinel tells drain loop to stop
        await self._queue.put(None)
        await self._drain_task

    def cancel(self) -> None:
        """Cancel all pending audio tasks and the drain loop."""
        self._drain_task.cancel()
        # Drain the queue and cancel any pending tasks
        while not self._queue.empty():
            try:
                task = self._queue.get_nowait()
                if task is not None and not task.done():
                    task.cancel()
            except asyncio.QueueEmpty:
                break

    # ── Internal ──────────────────────────────────────────────────

    def _scan(self) -> None:
        """Walk the raw buffer from scan_pos, processing markers and sentences."""
        buf = self._raw_buf
        pos = self._scan_pos

        while pos < len(buf):
            # Check for start of a marker
            bracket = buf.find('[', pos)

            if bracket == -1:
                # No brackets — rest is plain text
                self._voice_buf += buf[pos:]
                pos = len(buf)
                self._check_sentences()
                break

            # Add text before the bracket to voice buffer
            if bracket > pos:
                self._voice_buf += buf[pos:bracket]
                self._check_sentences()

            # Look for closing bracket
            close = buf.find(']', bracket)
            if close == -1:
                # Incomplete marker — stop scanning, wait for more data
                pos = bracket
                break

            # We have a complete bracket pair — check if it's a known marker
            marker_text = buf[bracket:close + 1]
            m = MARKER_PATTERN.match(marker_text)

            if m:
                marker_body = m.group(1)
                if ":" in marker_body:
                    mtype, meta = marker_body.split(":", 1)
                    mtype = mtype.lower()
                    meta = meta.strip()
                else:
                    mtype = marker_body.lower()
                    meta = ""

                if mtype in ("ambient", "sfx"):
                    # Fire audio immediately for ambient/sfx
                    seg = Segment(type=mtype, content="", meta=meta)
                    self._enqueue_segment(seg)
                elif mtype in ("narrate", "npc"):
                    # Flush current voice buffer before switching voice
                    text = self._voice_buf.strip()
                    if text:
                        self._enqueue_voice(text)
                        self._voice_buf = ""
                    self._seg_type = mtype
                    self._seg_meta = meta if mtype == "npc" else ""
                elif mtype == "roll":
                    # Just flush voice buffer — roll handling is in session.py
                    text = self._voice_buf.strip()
                    if text:
                        self._enqueue_voice(text)
                        self._voice_buf = ""

                pos = close + 1
            else:
                # Not a recognized marker — include the bracket as plain text
                self._voice_buf += buf[bracket:close + 1]
                pos = close + 1
                self._check_sentences()

        self._scan_pos = pos

    def _check_sentences(self) -> None:
        """Check voice buffer for complete sentences and fire TTS for each."""
        while True:
            m = SENTENCE_END.search(self._voice_buf)
            if not m:
                break
            # Sentence ends at the match position (include the punctuation)
            end = m.end()
            sentence = self._voice_buf[:end].strip()
            self._voice_buf = self._voice_buf[end:]
            if sentence:
                self._enqueue_voice(sentence)

    def _enqueue_voice(self, text: str) -> None:
        """Create a TTS task for text using the current voice context."""
        seg = Segment(
            type=self._seg_type,
            content=text,
            meta=self._seg_meta,
        )
        self._enqueue_segment(seg)

    def _enqueue_segment(self, segment: Segment) -> None:
        """Create an async task for audio generation and put it on the queue."""
        task = asyncio.create_task(self._generate(segment))
        self._queue.put_nowait(task)

    async def _generate(self, segment: Segment) -> list[dict]:
        """Generate audio messages for a single segment."""
        messages = []
        try:
            async for msg in self._pipeline.process_segment(segment):
                messages.append(msg)
        except Exception:
            log.exception("Streaming audio generation failed for segment: %s", segment)
        return messages

    async def _drain(self) -> None:
        """Await tasks in FIFO order and send results over WebSocket."""
        try:
            while True:
                task = await self._queue.get()
                if task is None:
                    break  # Sentinel from flush()
                messages = await task
                for msg in messages:
                    await self._send(msg)
                    self.sent_messages.append(msg)
        except asyncio.CancelledError:
            pass
        except Exception:
            log.exception("Streaming audio drain failed")
