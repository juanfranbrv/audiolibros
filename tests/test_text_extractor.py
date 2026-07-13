import os
import tempfile
import unittest

from ebooklib import epub

from text_extractor import extract_from_epub


class EpubReadingOrderTests(unittest.TestCase):
    def test_extracts_documents_in_spine_order(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            epub_path = os.path.join(temp_dir, "out-of-order.epub")
            book = epub.EpubBook()
            book.set_identifier("order-test")
            book.set_title("Order test")
            book.set_language("es")

            second = epub.EpubHtml(
                title="Segundo", file_name="chapter-2.xhtml", uid="chapter-2"
            )
            second.content = "<h1>SEGUNDO</h1>"
            first = epub.EpubHtml(
                title="Primero", file_name="chapter-1.xhtml", uid="chapter-1"
            )
            first.content = "<h1>PRIMERO</h1>"

            book.add_item(second)
            book.add_item(first)
            book.add_item(epub.EpubNcx())
            book.add_item(epub.EpubNav())
            book.spine = ["nav", first, second]
            epub.write_epub(epub_path, book)

            extracted = extract_from_epub(epub_path)

            self.assertLess(extracted.index("PRIMERO"), extracted.index("SEGUNDO"))

    def test_falls_back_to_manifest_when_spine_has_no_readable_text(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            epub_path = os.path.join(temp_dir, "empty-spine.epub")
            book = epub.EpubBook()
            book.set_identifier("fallback-test")
            book.set_title("Fallback test")
            book.set_language("es")

            empty = epub.EpubHtml(
                title="Vacío", file_name="empty.xhtml", uid="empty"
            )
            empty.content = "<div></div>"
            readable = epub.EpubHtml(
                title="Legible", file_name="readable.xhtml", uid="readable"
            )
            readable.content = "<p>CONTENIDO LEGIBLE</p>"

            book.add_item(empty)
            book.add_item(readable)
            book.add_item(epub.EpubNcx())
            book.add_item(epub.EpubNav())
            book.spine = [empty]
            epub.write_epub(epub_path, book)

            extracted = extract_from_epub(epub_path)

            self.assertIn("CONTENIDO LEGIBLE", extracted)


if __name__ == "__main__":
    unittest.main()
