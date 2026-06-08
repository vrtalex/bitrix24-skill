# Catalog: boards

Scope: scrum and board methods.

| Method | Risk | Scope | Required | Deprecated | Docs |
|---|---|---|---|---|---|
| `tasks.api.scrum.sprint.list` | read | task |  |  | https://github.com/bitrix24/b24restdocs/blob/main/api-reference/sonet-group/scrum/sprint/tasks-api-scrum-sprint-list.md |
| `tasks.api.scrum.sprint.add` | write | task | fields |  | https://github.com/bitrix24/b24restdocs/blob/main/api-reference/sonet-group/scrum/sprint/tasks-api-scrum-sprint-add.md |
| `tasks.api.scrum.sprint.start` | write | task | id |  | https://github.com/bitrix24/b24restdocs/blob/main/api-reference/sonet-group/scrum/sprint/tasks-api-scrum-sprint-start.md |
| `tasks.api.scrum.sprint.complete` | write | task | id |  | https://github.com/bitrix24/b24restdocs/blob/main/api-reference/sonet-group/scrum/sprint/tasks-api-scrum-sprint-complete.md |
| `tasks.api.scrum.kanban.getStages` | read | task | sprintId |  | https://github.com/bitrix24/b24restdocs/blob/main/api-reference/sonet-group/scrum/kanban/tasks-api-scrum-kanban-get-stages.md |
| `tasks.api.scrum.kanban.addTask` | write | task | sprintId,taskId,stageId |  | https://github.com/bitrix24/b24restdocs/blob/main/api-reference/sonet-group/scrum/kanban/tasks-api-scrum-kanban-add-task.md |
| `tasks.api.scrum.kanban.deleteTask` | destructive | task | sprintId,taskId |  | https://github.com/bitrix24/b24restdocs/blob/main/api-reference/sonet-group/scrum/kanban/tasks-api-scrum-kanban-delete-task.md |
| `tasks.api.scrum.epic.list` | read | task |  |  | https://github.com/bitrix24/b24restdocs/blob/main/api-reference/sonet-group/scrum/epic/tasks-api-scrum-epic-list.md |
| `tasks.api.scrum.epic.add` | write | task | fields |  | https://github.com/bitrix24/b24restdocs/blob/main/api-reference/sonet-group/scrum/epic/tasks-api-scrum-epic-add.md |
| `tasks.api.scrum.backlog.get` | read | task | id |  | https://github.com/bitrix24/b24restdocs/blob/main/api-reference/sonet-group/scrum/backlog/tasks-api-scrum-backlog-get.md |
| `tasks.api.scrum.backlog.add` | write | task | fields |  | https://github.com/bitrix24/b24restdocs/blob/main/api-reference/sonet-group/scrum/backlog/tasks-api-scrum-backlog-add.md |
| `tasks.api.scrum.task.update` | write | task | id,fields |  | https://github.com/bitrix24/b24restdocs/blob/main/api-reference/sonet-group/scrum/task/tasks-api-scrum-task-update.md |
