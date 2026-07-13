import os
import unittest
from unittest.mock import Mock, patch

import audiolibro_gui as gui_module
from audiolibro_gui import AudiobookCreatorGUI


class FakeVariable:
    def __init__(self, value=""):
        self.value = value

    def get(self):
        return self.value

    def set(self, value):
        self.value = value


class FakeRoot:
    def __init__(self):
        self.callback = None

    def after(self, delay, callback):
        self.callback = callback


class NewBookSelectionTests(unittest.TestCase):
    def test_selecting_another_book_replaces_the_output_name(self):
        gui = object.__new__(AudiobookCreatorGUI)
        gui.config = {"last_input_directory": "/"}
        gui.text_file_path = FakeVariable()
        gui.output_file_name = FakeVariable("Primer libro")
        gui.load_preview = Mock()

        with patch(
            "audiolibro_gui.filedialog.askopenfilename",
            return_value=r"C:\Books\Segundo libro.epub",
        ):
            gui.browse_text_file()

        self.assertEqual(gui.output_file_name.get(), "Segundo libro")
        gui.load_preview.assert_called_once_with()

    def test_generation_settings_are_a_snapshot(self):
        self.assertTrue(
            hasattr(gui_module, "capture_generation_settings"),
            "generation settings must be captured before the worker starts",
        )
        gui = object.__new__(AudiobookCreatorGUI)
        gui.output_file_name = FakeVariable("Primer libro")
        gui.selected_voice = FakeVariable("voice-a")
        gui.retries_value = FakeVariable(3)
        gui.rate_value = FakeVariable("-5%")
        gui.chunking_strategy = FakeVariable("smart")
        gui.config = {"last_output_directory": r"D:\AUDIOLIBROS"}

        settings = gui_module.capture_generation_settings(gui)
        gui.output_file_name.set("Segundo libro")
        gui.selected_voice.set("voice-b")

        self.assertEqual(settings["output_name"], "Primer libro")
        self.assertEqual(settings["voice"], "voice-a")

    def test_each_generation_gets_a_unique_processed_input_file(self):
        self.assertTrue(
            hasattr(gui_module, "create_processed_input_file"),
            "each generation needs an independent processed input file",
        )
        paths = []
        try:
            paths.append(gui_module.create_processed_input_file("primer texto"))
            paths.append(gui_module.create_processed_input_file("segundo texto"))

            self.assertNotEqual(paths[0], paths[1])
            with open(paths[0], "r", encoding="utf-8") as first_file:
                self.assertEqual(first_file.read(), "primer texto")
            with open(paths[1], "r", encoding="utf-8") as second_file:
                self.assertEqual(second_file.read(), "segundo texto")
        finally:
            for path in paths:
                if os.path.exists(path):
                    os.remove(path)

    def test_stale_preview_result_cannot_replace_the_current_book(self):
        self.assertTrue(
            hasattr(AudiobookCreatorGUI, "_apply_preview_if_current"),
            "preview results must be tied to their source file",
        )
        gui = object.__new__(AudiobookCreatorGUI)
        gui.text_file_path = FakeVariable(r"C:\Books\Segundo.epub")
        gui.loaded_preview_path = None
        gui._update_preview = Mock()

        gui._apply_preview_if_current(r"C:\Books\Primero.epub", "texto anterior")
        gui._update_preview.assert_not_called()
        self.assertIsNone(gui.loaded_preview_path)

        gui._apply_preview_if_current(r"C:\Books\Segundo.epub", "texto actual")
        gui._update_preview.assert_called_once_with("texto actual")
        self.assertEqual(gui.loaded_preview_path, r"C:\Books\Segundo.epub")

    def test_scheduled_error_keeps_its_message(self):
        self.assertTrue(
            hasattr(gui_module, "schedule_error_dialog"),
            "delayed error dialogs must capture their message",
        )
        root = FakeRoot()
        with patch("audiolibro_gui.messagebox.showerror") as showerror:
            gui_module.schedule_error_dialog(root, "fallo concreto")
            root.callback()

        showerror.assert_called_once_with("Error", "fallo concreto")


if __name__ == "__main__":
    unittest.main()
