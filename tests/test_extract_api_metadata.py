import pathlib
import sys
import unittest


TOOLS_DIR = pathlib.Path(__file__).resolve().parents[1] / "tools"
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

import extract_api_metadata as ex  # noqa: E402


DEPRECATED_DOC = """# Update a lead crm.lead.update

> Scope: [`crm`](../../scopes/permissions.md)
>
> Who can execute the method: any user

{% note warning "DEPRECATED" %}

The development of this method has been halted. Use [crm.item.update](../universal/crm-item-update.md).

{% endnote %}

## Method parameters

{% include [Parameter note](../../../_includes/required.md) %}

#|
|| **Name**
`type` | **Description** ||
|| **id***
[`integer`](../../data-types.md) | Lead identifier ||
|| **fields**
[`object`](../../data-types.md) | Lead fields ||
|#

### Parameter fields {#fields}
#|
|| **TITLE**
[`string`] | Title ||
|#
"""

LIST_DOC = """# Get a list booking.v1.resource.list

> Scope: [`booking`](../../scopes/permissions.md)

The method returns a list of resources.

## Method parameters

#|
|| **Name** | **Description** ||
|| **filter**
[`object`] | Optional filter ||
|#
"""

NON_METHOD_DOC = """# Working with leads overview

This section describes the general principles of working with leads.
See also [crm.lead.add](./crm-lead-add.md).
"""


FALSE_DEPRECATED_DOC = """# Get a task list tasks.task.list

> Scope: [`task`](../../scopes/permissions.md)

The method returns a list of tasks.

## Method parameters

#|
|| **Name** | **Description** ||
|| **filter**
[`object`] | Optional filter ||
|#

## Examples

```php
// getTotal() is deprecated (removed in SDK 2.0); use the full match count instead
$total = $result->getTotal();
```
"""


class ExtractMethodTests(unittest.TestCase):
    def test_deprecated_word_only_in_body_is_not_method_deprecation(self):
        # "deprecated" appears only in a code example below "## Method parameters", not in
        # the method header -> the METHOD itself must NOT be flagged deprecated.
        result = ex.extract_method(FALSE_DEPRECATED_DOC, "tasks/tasks-task-list.md")
        self.assertEqual(result["method"], "tasks.task.list")
        self.assertFalse(result["deprecated"])
        self.assertIsNone(result["replacement"])

    def test_deprecated_method_with_required_param(self):
        result = ex.extract_method(DEPRECATED_DOC, "crm/leads/crm-lead-update.md")
        self.assertEqual(result["method"], "crm.lead.update")
        self.assertEqual(result["scope"], ["crm"])
        self.assertEqual(result["required"], ["id"])
        self.assertTrue(result["deprecated"])
        self.assertEqual(result["replacement"], "crm.item.update")
        self.assertEqual(result["doc_path"], "crm/leads/crm-lead-update.md")

    def test_list_method_no_required_not_deprecated(self):
        result = ex.extract_method(LIST_DOC, "booking/booking/booking-v1-resource-list.md")
        self.assertEqual(result["method"], "booking.v1.resource.list")
        self.assertEqual(result["scope"], ["booking"])
        self.assertEqual(result["required"], [])
        self.assertFalse(result["deprecated"])
        self.assertIsNone(result["replacement"])

    def test_non_method_doc_returns_none(self):
        self.assertIsNone(ex.extract_method(NON_METHOD_DOC, "crm/leads/index.md"))


if __name__ == "__main__":
    unittest.main()
