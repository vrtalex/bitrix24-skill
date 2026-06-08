# Catalog: core

Scope: baseline CRM (universal `crm.item.*`)/tasks/events operations.

| Method | Risk | Scope | Required | Deprecated | Docs |
|---|---|---|---|---|---|
| `user.current` | read | user,user_brief,user_basic |  |  | https://github.com/bitrix24/b24restdocs/blob/main/api-reference/user/user-current.md |
| `user.get` | read | user,user_brief,user_basic |  |  | https://github.com/bitrix24/b24restdocs/blob/main/api-reference/user/user-get.md |
| `department.get` | read | department |  |  | https://github.com/bitrix24/b24restdocs/blob/main/api-reference/departments/department-get.md |
| `crm.item.add` | write | crm | entityTypeId,fields |  | https://github.com/bitrix24/b24restdocs/blob/main/api-reference/crm/universal/crm-item-add.md |
| `crm.item.list` | read | crm | entityTypeId |  | https://github.com/bitrix24/b24restdocs/blob/main/api-reference/crm/universal/crm-item-list.md |
| `crm.item.get` | read | crm | entityTypeId,id |  | https://github.com/bitrix24/b24restdocs/blob/main/api-reference/crm/universal/crm-item-get.md |
| `crm.item.update` | write | crm | entityTypeId,fields |  | https://github.com/bitrix24/b24restdocs/blob/main/api-reference/crm/universal/crm-item-update.md |
| `crm.item.delete` | destructive | crm | entityTypeId,id |  | https://github.com/bitrix24/b24restdocs/blob/main/api-reference/crm/universal/crm-item-delete.md |
| `crm.lead.add` | write | crm |  | → crm.item.add | https://github.com/bitrix24/b24restdocs/blob/main/api-reference/crm/leads/crm-lead-add.md |
| `crm.lead.list` | read | crm |  | → crm.item.list | https://github.com/bitrix24/b24restdocs/blob/main/api-reference/crm/leads/crm-lead-list.md |
| `crm.lead.update` | write | crm | id | → crm.item.update | https://github.com/bitrix24/b24restdocs/blob/main/api-reference/crm/leads/crm-lead-update.md |
| `crm.deal.add` | write | crm |  | → crm.item.add | https://github.com/bitrix24/b24restdocs/blob/main/api-reference/crm/deals/crm-deal-add.md |
| `crm.deal.list` | read | crm |  | → crm.item.list | https://github.com/bitrix24/b24restdocs/blob/main/api-reference/crm/deals/crm-deal-list.md |
| `crm.deal.update` | write | crm | id | → crm.item.update | https://github.com/bitrix24/b24restdocs/blob/main/api-reference/crm/deals/crm-deal-update.md |
| `tasks.task.add` | write | task | fields |  | https://github.com/bitrix24/b24restdocs/blob/main/api-reference/tasks/tasks-task-add.md |
| `tasks.task.list` | read | task |  |  | https://github.com/bitrix24/b24restdocs/blob/main/api-reference/tasks/tasks-task-list.md |
| `tasks.task.update` | write | task | taskId,fields |  | https://github.com/bitrix24/b24restdocs/blob/main/api-reference/tasks/tasks-task-update.md |
| `tasks.task.complete` | write | task | taskId |  | https://github.com/bitrix24/b24restdocs/blob/main/api-reference/tasks/tasks-task-complete.md |
| `event.bind` | write | - | event,handler |  | https://github.com/bitrix24/b24restdocs/blob/main/api-reference/events/event-bind.md |
| `event.get` | read | - |  |  | https://github.com/bitrix24/b24restdocs/blob/main/api-reference/events/event-get.md |
| `event.unbind` | destructive | - | event,handler |  | https://github.com/bitrix24/b24restdocs/blob/main/api-reference/events/event-unbind.md |
| `event.offline.list` | read | - |  |  | https://github.com/bitrix24/b24restdocs/blob/main/api-reference/events/event-offline-list.md |
| `event.offline.get` | read | - |  |  | https://github.com/bitrix24/b24restdocs/blob/main/api-reference/events/event-offline-get.md |
| `event.offline.clear` | destructive | - | process_id |  | https://github.com/bitrix24/b24restdocs/blob/main/api-reference/events/event-offline-clear.md |
| `event.offline.error` | write | - | process_id |  | https://github.com/bitrix24/b24restdocs/blob/main/api-reference/events/event-offline-error.md |
| `batch` | mixed | - |  |  | https://github.com/bitrix24/b24restdocs/blob/main/settings/how-to-call-rest-api/batch.md |
| `crm.item.fields` | read | crm | entityTypeId |  | https://github.com/bitrix24/b24restdocs/blob/main/api-reference/crm/universal/crm-item-fields.md |
| `crm.activity.todo.add` | write | crm | ownerTypeId,ownerId,deadline |  | https://github.com/bitrix24/b24restdocs/blob/main/api-reference/crm/timeline/activities/todo/crm-activity-todo-add.md |
| `crm.activity.list` | read | crm |  |  | https://github.com/bitrix24/b24restdocs/blob/main/api-reference/crm/timeline/activities/activity-base/crm-activity-list.md |
| `crm.activity.fields` | read | crm |  |  | https://github.com/bitrix24/b24restdocs/blob/main/api-reference/crm/timeline/activities/activity-base/crm-activity-fields.md |
| `crm.timeline.comment.add` | write | crm | fields |  | https://github.com/bitrix24/b24restdocs/blob/main/api-reference/crm/timeline/comments/crm-timeline-comment-add.md |
| `crm.timeline.comment.list` | read | crm | filter |  | https://github.com/bitrix24/b24restdocs/blob/main/api-reference/crm/timeline/comments/crm-timeline-comment-list.md |
| `crm.status.list` | read | crm |  |  | https://github.com/bitrix24/b24restdocs/blob/main/api-reference/crm/status/crm-status-list.md |
| `crm.category.list` | read | crm | entityTypeId |  | https://github.com/bitrix24/b24restdocs/blob/main/api-reference/crm/universal/category/crm-category-list.md |
| `crm.item.productrow.set` | write | crm | ownerId,ownerType,productRows |  | https://github.com/bitrix24/b24restdocs/blob/main/api-reference/crm/universal/product-rows/crm-item-productrow-set.md |
| `crm.item.productrow.list` | read | crm | filter |  | https://github.com/bitrix24/b24restdocs/blob/main/api-reference/crm/universal/product-rows/crm-item-productrow-list.md |
| `crm.requisite.list` | read | crm |  |  | https://github.com/bitrix24/b24restdocs/blob/main/api-reference/crm/requisites/universal/crm-requisite-list.md |
| `crm.requisite.add` | write | crm | fields,ENTITY_TYPE_ID,ENTITY_ID,PRESET_ID,NAME |  | https://github.com/bitrix24/b24restdocs/blob/main/api-reference/crm/requisites/universal/crm-requisite-add.md |
| `tasks.task.get` | read | task |  |  | https://github.com/bitrix24/b24restdocs/blob/main/api-reference/tasks/tasks-task-get.md |
| `tasks.task.getFields` | read | task |  |  | https://github.com/bitrix24/b24restdocs/blob/main/api-reference/tasks/tasks-task-get-fields.md |
| `tasks.task.delegate` | write | task | taskId,userId |  | https://github.com/bitrix24/b24restdocs/blob/main/api-reference/tasks/tasks-task-delegate.md |
| `task.checklistitem.add` | write | task | TASKID,FIELDS |  | https://github.com/bitrix24/b24restdocs/blob/main/api-reference/tasks/checklist-item/task-checklist-item-add.md |
| `task.checklistitem.complete` | write | task | TASKID,ITEMID |  | https://github.com/bitrix24/b24restdocs/blob/main/api-reference/tasks/checklist-item/task-checklist-item-complete.md |
| `tasks.task.chat.message.send` | write | tasks | fields |  | https://github.com/bitrix24/b24restdocs/blob/main/api-reference/rest-v3/tasks/tasks-task-chat-message-send.md |
| `user.search` | read | user,user_brief,user_basic |  |  | https://github.com/bitrix24/b24restdocs/blob/main/api-reference/user/user-search.md |
| `user.fields` | read | user,user_brief,user_basic |  |  | https://github.com/bitrix24/b24restdocs/blob/main/api-reference/user/user-fields.md |
| `crm.deal.contact.add` | write | crm | id,fields |  | https://github.com/bitrix24/b24restdocs/blob/main/api-reference/crm/deals/contacts/crm-deal-contact-add.md |
| `crm.deal.contact.delete` | destructive | crm | id,fields |  | https://github.com/bitrix24/b24restdocs/blob/main/api-reference/crm/deals/contacts/crm-deal-contact-delete.md |
| `crm.deal.contact.items.get` | read | crm | id |  | https://github.com/bitrix24/b24restdocs/blob/main/api-reference/crm/deals/contacts/crm-deal-contact-items-get.md |
| `crm.company.contact.add` | write | crm | id,fields |  | https://github.com/bitrix24/b24restdocs/blob/main/api-reference/crm/companies/contacts/crm-company-contact-add.md |
| `crm.company.contact.items.get` | read | crm | id |  | https://github.com/bitrix24/b24restdocs/blob/main/api-reference/crm/companies/contacts/crm-company-contact-items-get.md |
| `crm.contact.company.add` | write | crm | id,fields |  | https://github.com/bitrix24/b24restdocs/blob/main/api-reference/crm/contacts/company/crm-contact-company-add.md |
| `crm.contact.company.items.get` | read | crm | id |  | https://github.com/bitrix24/b24restdocs/blob/main/api-reference/crm/contacts/company/crm-contact-company-items-get.md |
| `crm.documentgenerator.document.add` | write | crm |  |  | https://github.com/bitrix24/b24restdocs/blob/main/api-reference/crm/document-generator/documents/crm-document-generator-document-add.md |
| `crm.documentgenerator.document.get` | read | crm |  |  | https://github.com/bitrix24/b24restdocs/blob/main/api-reference/crm/document-generator/documents/crm-document-generator-document-get.md |
| `crm.documentgenerator.document.list` | read | crm |  |  | https://github.com/bitrix24/b24restdocs/blob/main/api-reference/crm/document-generator/documents/crm-document-generator-document-list.md |
| `crm.documentgenerator.template.list` | read | crm |  |  | https://github.com/bitrix24/b24restdocs/blob/main/api-reference/crm/document-generator/templates/crm-document-generator-template-list.md |
| `crm.currency.list` | read | crm |  |  | https://github.com/bitrix24/b24restdocs/blob/main/api-reference/crm/currency/crm-currency-list.md |
| `crm.currency.base.get` | read | crm |  |  | https://github.com/bitrix24/b24restdocs/blob/main/api-reference/crm/currency/crm-currency-base-get.md |
| `tasks.task.start` | write | task | taskId |  | https://github.com/bitrix24/b24restdocs/blob/main/api-reference/tasks/tasks-task-start.md |
| `tasks.task.pause` | write | task | taskId |  | https://github.com/bitrix24/b24restdocs/blob/main/api-reference/tasks/tasks-task-pause.md |
| `tasks.task.defer` | write | task | taskId |  | https://github.com/bitrix24/b24restdocs/blob/main/api-reference/tasks/tasks-task-defer.md |
| `tasks.task.files.attach` | write | task | taskId,fileId |  | https://github.com/bitrix24/b24restdocs/blob/main/api-reference/tasks/tasks-task-files-attach.md |
| `tasks.task.counters.get` | read | task |  |  | https://github.com/bitrix24/b24restdocs/blob/main/api-reference/tasks/tasks-task-counters-get.md |
| `tasks.task.history.list` | read | task | taskId |  | https://github.com/bitrix24/b24restdocs/blob/main/api-reference/tasks/tasks-task-history-list.md |
| `crm.duplicate.findbycomm` | read | crm | type,values |  | https://github.com/bitrix24/b24restdocs/blob/main/api-reference/crm/duplicates/crm-duplicate-find-by-comm.md |
| `crm.enum.ownertype` | read | crm |  |  | https://github.com/bitrix24/b24restdocs/blob/main/api-reference/crm/auxiliary/enum/crm-enum-owner-type.md |
| `crm.tracking.trace.add` | write | crm |  |  | https://github.com/bitrix24/b24restdocs/blob/main/api-reference/crm/tracking/crm-tracking-trace-add.md |

Prefer the universal `crm.item.*` API (`entityTypeId`: 1=lead, 2=deal, 3=contact, 4=company). The entity-specific `crm.lead.*` and `crm.deal.*` methods are deprecated and kept only for compatibility.
