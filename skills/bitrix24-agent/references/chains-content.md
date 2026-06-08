# Chains: content

## 1) Upload file to process folder

1. `disk.storage.getlist`
2. `disk.folder.getchildren`
3. `disk.folder.uploadfile`
4. Store resulting file ID in CRM/task entity

## 2) Versioned replacement flow

1. `disk.file.get`
2. `disk.file.uploadversion`
3. Keep previous version reference for rollback

## 3) Move-and-archive pattern

1. `disk.file.moveto`
2. `disk.file.copyto` for backup
3. `disk.file.delete` only with explicit destructive confirmation

## 4) Create a task with a Disk file attached

Requires the `core` pack for the tasks.* methods.

1. `disk.folder.uploadfile` — upload and capture the Disk object id
2. On a NEW task: `tasks.task.add` with `fields.UF_TASK_WEBDAV_FILES = ['n<diskId>']` (note the literal `n` prefix)
3. On an EXISTING task: `tasks.task.files.attach` with `fileId=<diskId>` (NO `n` prefix here)
4. `tasks.task.get` selecting `UF_TASK_WEBDAV_FILES`, then `disk.attachedObject.get` to resolve the attachment

Guardrail: the `n`-prefix applies only to the `UF_TASK_WEBDAV_FILES` field on add; the attach method takes the bare id — this mismatch is the #1 source of file-attach bugs.
