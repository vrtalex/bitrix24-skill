# Catalog: content

Scope: file and document operations.

| Method | Risk | Scope | Required | Deprecated | Docs |
|---|---|---|---|---|---|
| `disk.storage.getlist` | read | disk |  |  | https://github.com/bitrix24/b24restdocs/blob/main/api-reference/disk/storage/disk-storage-get-list.md |
| `disk.storage.getchildren` | read | disk | id |  | https://github.com/bitrix24/b24restdocs/blob/main/api-reference/disk/storage/disk-storage-get-children.md |
| `disk.folder.getchildren` | read | disk | id |  | https://github.com/bitrix24/b24restdocs/blob/main/api-reference/disk/folder/disk-folder-get-children.md |
| `disk.folder.addsubfolder` | write | disk | id,data |  | https://github.com/bitrix24/b24restdocs/blob/main/api-reference/disk/folder/disk-folder-add-subfolder.md |
| `disk.folder.uploadfile` | write | disk | id,data |  | https://github.com/bitrix24/b24restdocs/blob/main/api-reference/disk/folder/disk-folder-upload-file.md |
| `disk.file.get` | read | disk | id |  | https://github.com/bitrix24/b24restdocs/blob/main/api-reference/disk/file/disk-file-get.md |
| `disk.file.copyto` | write | disk | id,targetFolderId |  | https://github.com/bitrix24/b24restdocs/blob/main/api-reference/disk/file/disk-file-copy-to.md |
| `disk.file.moveto` | write | disk | id,targetFolderId |  | https://github.com/bitrix24/b24restdocs/blob/main/api-reference/disk/file/disk-file-move-to.md |
| `disk.file.uploadversion` | write | disk | id,fileContent |  | https://github.com/bitrix24/b24restdocs/blob/main/api-reference/disk/file/disk-file-upload-version.md |
| `disk.file.delete` | destructive | disk | id |  | https://github.com/bitrix24/b24restdocs/blob/main/api-reference/disk/file/disk-file-delete.md |
| `documentgenerator.document.add` | write | documentgenerator | templateId,value |  | https://github.com/bitrix24/b24restdocs/blob/main/api-reference/document-generator/document-generator-document-add.md |
| `disk.folder.get` | read | disk | id |  | https://github.com/bitrix24/b24restdocs/blob/main/api-reference/disk/folder/disk-folder-get.md |
| `disk.file.getfields` | read | disk |  |  | https://github.com/bitrix24/b24restdocs/blob/main/api-reference/disk/file/disk-file-get-fields.md |
| `disk.attachedObject.get` | read | disk | id |  | https://github.com/bitrix24/b24restdocs/blob/main/api-reference/disk/attached-object/disk-attached-object-get.md |
