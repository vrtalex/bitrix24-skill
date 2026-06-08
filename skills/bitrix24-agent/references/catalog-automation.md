# Catalog: automation

Scope: business process execution, robots, workflow templates.

| Method | Risk | Scope | Required | Deprecated | Docs |
|---|---|---|---|---|---|
| `bizproc.workflow.start` | write | bizproc | TEMPLATE_ID,DOCUMENT_ID |  | https://github.com/bitrix24/b24restdocs/blob/main/api-reference/bizproc/bizproc-workflow-start.md |
| `bizproc.workflow.terminate` | destructive | bizproc | ID |  | https://github.com/bitrix24/b24restdocs/blob/main/api-reference/bizproc/bizproc-workflow-terminate.md |
| `bizproc.workflow.kill` | destructive | bizproc | ID |  | https://github.com/bitrix24/b24restdocs/blob/main/api-reference/bizproc/bizproc-workflow-kill.md |
| `bizproc.task.list` | read | bizproc |  |  | https://github.com/bitrix24/b24restdocs/blob/main/api-reference/bizproc/bizproc-task/bizproc-task-list.md |
| `bizproc.task.complete` | write | bizproc | TASK_ID,STATUS |  | https://github.com/bitrix24/b24restdocs/blob/main/api-reference/bizproc/bizproc-task/bizproc-task-complete.md |
| `bizproc.robot.list` | read | bizproc |  |  | https://github.com/bitrix24/b24restdocs/blob/main/api-reference/bizproc/bizproc-robot/bizproc-robot-list.md |
| `bizproc.robot.add` | write | bizproc | CODE,HANDLER,NAME,PLACEMENT_HANDLER |  | https://github.com/bitrix24/b24restdocs/blob/main/api-reference/bizproc/bizproc-robot/bizproc-robot-add.md |
| `bizproc.robot.update` | write | bizproc | CODE,FIELDS |  | https://github.com/bitrix24/b24restdocs/blob/main/api-reference/bizproc/bizproc-robot/bizproc-robot-update.md |
| `bizproc.workflow.template.list` | read | bizproc |  |  | https://github.com/bitrix24/b24restdocs/blob/main/api-reference/bizproc/template/bizproc-workflow-template-list.md |
| `bizproc.workflow.template.update` | write | bizproc | ID,FIELDS |  | https://github.com/bitrix24/b24restdocs/blob/main/api-reference/bizproc/template/bizproc-workflow-template-update.md |
| `lists.get` | read | lists | IBLOCK_TYPE_ID |  | https://github.com/bitrix24/b24restdocs/blob/main/api-reference/lists/lists/lists-get.md |
| `lists.field.get` | read | lists | IBLOCK_TYPE_ID,IBLOCK_ID,IBLOCK_CODE |  | https://github.com/bitrix24/b24restdocs/blob/main/api-reference/lists/fields/lists-field-get.md |
| `lists.element.get` | read | lists | IBLOCK_TYPE_ID,IBLOCK_ID,IBLOCK_CODE |  | https://github.com/bitrix24/b24restdocs/blob/main/api-reference/lists/elements/lists-element-get.md |
| `lists.element.add` | write | lists | IBLOCK_TYPE_ID,IBLOCK_ID,IBLOCK_CODE,ELEMENT_CODE,FIELDS |  | https://github.com/bitrix24/b24restdocs/blob/main/api-reference/lists/elements/lists-element-add.md |
| `lists.element.update` | write | lists | IBLOCK_TYPE_ID,IBLOCK_ID,IBLOCK_CODE,ELEMENT_ID,ELEMENT_CODE,FIELDS |  | https://github.com/bitrix24/b24restdocs/blob/main/api-reference/lists/elements/lists-element-update.md |
