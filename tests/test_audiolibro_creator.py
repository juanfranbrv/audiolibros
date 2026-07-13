import asyncio
import os
import inspect
import sys
import tempfile
import types
import unittest
from unittest.mock import patch
from unittest.mock import AsyncMock

import audiolibro_creator as creator


class JobIdentityTests(unittest.TestCase):
    def build_job_id(self, chunks, voice="voice-a", rate="-5%", strategy="smart"):
        self.assertTrue(
            hasattr(creator, "build_job_id"),
            "build_job_id must isolate temporary chunks by job",
        )
        return creator.build_job_id(chunks, voice, rate, strategy)

    def test_identical_jobs_have_the_same_id(self):
        first = self.build_job_id(["one", "two"])
        second = self.build_job_id(["one", "two"])
        self.assertEqual(first, second)

    def test_content_changes_job_id(self):
        self.assertNotEqual(self.build_job_id(["one"]), self.build_job_id(["other"]))

    def test_voice_changes_job_id(self):
        self.assertNotEqual(
            self.build_job_id(["one"], voice="voice-a"),
            self.build_job_id(["one"], voice="voice-b"),
        )

    def test_rate_changes_job_id(self):
        self.assertNotEqual(
            self.build_job_id(["one"], rate="-5%"),
            self.build_job_id(["one"], rate="+5%"),
        )

    def test_strategy_changes_job_id(self):
        self.assertNotEqual(
            self.build_job_id(["one"], strategy="smart"),
            self.build_job_id(["one"], strategy="legacy"),
        )


class ChunkValidationTests(unittest.TestCase):
    def ordered_files(self, temp_dir, expected_count):
        self.assertTrue(
            hasattr(creator, "get_ordered_chunk_files"),
            "get_ordered_chunk_files must validate the complete chunk set",
        )
        return creator.get_ordered_chunk_files(temp_dir, expected_count)

    @staticmethod
    def create_chunk(temp_dir, name):
        path = os.path.join(temp_dir, name)
        with open(path, "wb") as chunk_file:
            chunk_file.write(b"audio")
        return path

    def test_returns_exact_chunks_in_numeric_order(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            second = self.create_chunk(temp_dir, "chunk_0001.mp3")
            first = self.create_chunk(temp_dir, "chunk_0000.mp3")
            self.assertEqual(self.ordered_files(temp_dir, 2), [first, second])

    def test_rejects_a_missing_chunk(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            self.create_chunk(temp_dir, "chunk_0000.mp3")
            with self.assertRaises(RuntimeError):
                self.ordered_files(temp_dir, 2)

    def test_rejects_an_extra_chunk(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            self.create_chunk(temp_dir, "chunk_0000.mp3")
            self.create_chunk(temp_dir, "chunk_0001.mp3")
            with self.assertRaises(RuntimeError):
                self.ordered_files(temp_dir, 1)

    def test_rejects_an_invalid_chunk_name(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            self.create_chunk(temp_dir, "chunk_0.mp3")
            with self.assertRaises(RuntimeError):
                self.ordered_files(temp_dir, 1)

    def test_rejects_an_empty_chunk(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            open(os.path.join(temp_dir, "chunk_0000.mp3"), "wb").close()
            with self.assertRaises(RuntimeError):
                self.ordered_files(temp_dir, 1)


class CleanupTests(unittest.TestCase):
    def test_cleanup_removes_only_the_completed_job(self):
        self.assertEqual(
            len(inspect.signature(creator.cleanup).parameters),
            1,
            "cleanup must target one job directory",
        )
        with tempfile.TemporaryDirectory() as temp_root:
            completed_job = os.path.join(temp_root, "completed")
            pending_job = os.path.join(temp_root, "pending")
            os.makedirs(completed_job)
            os.makedirs(pending_job)

            creator.cleanup(completed_job)

            self.assertFalse(os.path.exists(completed_job))
            self.assertTrue(os.path.isdir(pending_job))


class ChunkSynthesisTests(unittest.TestCase):
    def test_failed_synthesis_does_not_leave_a_reusable_chunk(self):
        class FailingCommunicate:
            def __init__(self, text, voice, rate):
                pass

            async def save(self, output_path):
                with open(output_path, "wb") as output_file:
                    output_file.write(b"partial")
                raise ConnectionError("connection lost")

        fake_edge_tts = types.SimpleNamespace(Communicate=FailingCommunicate)
        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = os.path.join(temp_dir, "chunk_0000.mp3")
            partial_path = output_path + ".part"
            with open(partial_path, "wb") as stale_partial:
                stale_partial.write(b"stale")

            with patch.dict(sys.modules, {"edge_tts": fake_edge_tts}), patch.object(
                creator.console, "print"
            ):
                result = asyncio.run(
                    creator.synthesize_chunk("text", "voice", output_path, "-5%")
                )

            self.assertFalse(result)
            self.assertFalse(os.path.exists(output_path))
            self.assertFalse(os.path.exists(partial_path))

    def test_successful_synthesis_promotes_the_partial_file_atomically(self):
        class SuccessfulCommunicate:
            def __init__(self, text, voice, rate):
                pass

            async def save(self, output_path):
                with open(output_path, "wb") as output_file:
                    output_file.write(b"complete audio")

        fake_edge_tts = types.SimpleNamespace(Communicate=SuccessfulCommunicate)
        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = os.path.join(temp_dir, "chunk_0000.mp3")

            with patch.dict(sys.modules, {"edge_tts": fake_edge_tts}):
                result = asyncio.run(
                    creator.synthesize_chunk("text", "voice", output_path, "-5%")
                )

            self.assertTrue(result)
            self.assertTrue(os.path.isfile(output_path))
            self.assertFalse(os.path.exists(output_path + ".part"))


class JobLockTests(unittest.TestCase):
    def test_default_temporary_root_is_absolute(self):
        self.assertTrue(os.path.isabs(creator.TEMP_DIR))

    def test_same_job_cannot_run_twice_at_the_same_time(self):
        self.assertTrue(
            hasattr(creator, "acquire_job_lock"),
            "identical jobs need operating-system locking",
        )
        self.assertTrue(hasattr(creator, "release_job_lock"))

        with tempfile.TemporaryDirectory() as temp_root:
            first_lock = creator.acquire_job_lock("same-job", temp_root)
            try:
                with self.assertRaises(RuntimeError):
                    creator.acquire_job_lock("same-job", temp_root)
            finally:
                creator.release_job_lock(first_lock)

            second_lock = creator.acquire_job_lock("same-job", temp_root)
            creator.release_job_lock(second_lock)


class ProcessingErrorTests(unittest.TestCase):
    def test_missing_input_raises_a_normal_exception(self):
        missing_path = os.path.join(tempfile.gettempdir(), "missing-audiobook.epub")
        try:
            asyncio.run(
                creator.process_audiobook_creation(
                    missing_path,
                    os.path.join(tempfile.gettempdir(), "unused.mp3"),
                    "voice",
                    1,
                    "-5%",
                    "smart",
                    status_callback=lambda message: None,
                )
            )
        except BaseException as exc:
            self.assertIsInstance(exc, RuntimeError)
        else:
            self.fail("missing input must raise an exception")

    def test_ffmpeg_failure_raises_runtime_error_and_keeps_chunks(self):
        class FailedProcess:
            returncode = 1

            async def communicate(self):
                return b"", b"invalid audio"

        with tempfile.TemporaryDirectory() as temp_dir:
            chunk_path = os.path.join(temp_dir, "chunk_0000.mp3")
            with open(chunk_path, "wb") as chunk_file:
                chunk_file.write(b"audio")

            with patch.object(
                creator.asyncio,
                "create_subprocess_shell",
                new=AsyncMock(return_value=FailedProcess()),
            ), patch.object(creator.console, "print"):
                with self.assertRaisesRegex(RuntimeError, "invalid audio"):
                    asyncio.run(
                        creator.concatenate_chunks(
                            os.path.join(temp_dir, "output.mp3"), temp_dir, 1
                        )
                    )

            self.assertTrue(os.path.isfile(chunk_path))


if __name__ == "__main__":
    unittest.main()
