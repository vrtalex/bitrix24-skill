# Catalog: templates

Scope: recurring task templates.

| Method | Risk | Scope | Required | Deprecated | Docs |
|---|---|---|---|---|---|
| `tasks.template.fields` | read | task |  |  | https://github.com/bitrix24/b24restdocs/blob/main/api-reference/tasks/template/tasks-template-fields.md |
| `tasks.template.get` | read | task | templateId |  | https://github.com/bitrix24/b24restdocs/blob/main/api-reference/tasks/template/tasks-template-get.md |
| `tasks.template.add` | write | task | fields |  | https://github.com/bitrix24/b24restdocs/blob/main/api-reference/tasks/template/tasks-template-add.md |
| `tasks.template.update` | write | task | templateId,fields |  | https://github.com/bitrix24/b24restdocs/blob/main/api-reference/tasks/template/tasks-template-update.md |
| `tasks.template.delete` | destructive | task | templateId |  | https://github.com/bitrix24/b24restdocs/blob/main/api-reference/tasks/template/tasks-template-delete.md |
| `tasks.template.checklist.list` | read | task | templateId |  | https://github.com/bitrix24/b24restdocs/blob/main/api-reference/tasks/template/checklist/tasks-template-checklist-list.md |
| `tasks.template.checklist.add` | write | task | templateId,fields |  | https://github.com/bitrix24/b24restdocs/blob/main/api-reference/tasks/template/checklist/tasks-template-checklist-add.md |
| `tasks.template.checklist.complete` | write | task | templateId,checkListItemId |  | https://github.com/bitrix24/b24restdocs/blob/main/api-reference/tasks/template/checklist/tasks-template-checklist-complete.md |
