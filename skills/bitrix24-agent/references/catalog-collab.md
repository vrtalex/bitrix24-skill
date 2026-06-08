# Catalog: collab

Scope: workgroups and collaboration streams.

| Method | Risk | Scope | Required | Deprecated | Docs |
|---|---|---|---|---|---|
| `socialnetwork.api.workgroup.list` | read | socialnetwork |  |  | https://github.com/bitrix24/b24restdocs/blob/main/api-reference/sonet-group/socialnetwork-api-workgroup-list.md |
| `sonet_group.get` | read | sonet |  |  | https://github.com/bitrix24/b24restdocs/blob/main/api-reference/sonet-group/sonet-group-get.md |
| `sonet_group.create` | write | sonet | NAME |  | https://github.com/bitrix24/b24restdocs/blob/main/api-reference/sonet-group/sonet-group-create.md |
| `sonet_group.update` | write | sonet | GROUP_ID |  | https://github.com/bitrix24/b24restdocs/blob/main/api-reference/sonet-group/sonet-group-update.md |
| `sonet_group.delete` | destructive | sonet | GROUP_ID |  | https://github.com/bitrix24/b24restdocs/blob/main/api-reference/sonet-group/sonet-group-delete.md |
| `log.blogpost.add` | write | log | POST_MESSAGE |  | https://github.com/bitrix24/b24restdocs/blob/main/api-reference/log/log-blogpost-add.md |
| `log.blogpost.update` | write | log | POST_ID |  | https://github.com/bitrix24/b24restdocs/blob/main/api-reference/log/log-blogpost-update.md |
| `log.blogpost.delete` | destructive | log | POST_ID |  | https://github.com/bitrix24/b24restdocs/blob/main/api-reference/log/log-blogpost-delete.md |
| `log.blogcomment.add` | write | log | POST_ID,TEXT |  | https://github.com/bitrix24/b24restdocs/blob/main/api-reference/log/blogcomment/log-blogcomment-add.md |
| `log.blogcomment.delete` | destructive | log | COMMENT_ID |  | https://github.com/bitrix24/b24restdocs/blob/main/api-reference/log/blogcomment/log-blogcomment-delete.md |
