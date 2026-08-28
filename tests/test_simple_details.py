import unittest

import panel as pn

from whateels.components import SimpleDetails


class SimpleDetailsOverflowTests(unittest.TestCase):

    def test_content_ancestors_do_not_clip_dropdown_menus(self):
        select = pn.widgets.Select(name="Choice", options=["A", "B"])
        details = SimpleDetails("Section", select, expanded=True)

        layout = details.objects[0]
        content_row = layout.objects[1]
        content_body = content_row.objects[1]

        for container in (details, layout, content_row, content_body):
            self.assertEqual(container.styles.get("overflow"), "visible")
            self.assertNotIn("overflow-x", container.styles)
            self.assertNotIn("overflow-y", container.styles)

    def test_horizontal_inset_still_uses_fixed_layout_spacers(self):
        details = SimpleDetails(
            "Section",
            pn.widgets.Select(options=["A", "B"]),
            expanded=True,
        )

        content_row = details.objects[0].objects[1]

        self.assertIsInstance(content_row.objects[0], pn.Spacer)
        self.assertEqual(content_row.objects[0].width, 10)
        self.assertIsInstance(content_row.objects[2], pn.Spacer)
        self.assertEqual(content_row.objects[2].width, 10)
        self.assertEqual(content_row.margin, (10, 0))
        self.assertEqual(content_row.styles.get("max-width"), "100%")


if __name__ == "__main__":
    unittest.main()
