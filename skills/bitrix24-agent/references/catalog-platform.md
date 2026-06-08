# Catalog: platform

Scope: AI engines, entity storage, and biconnector layer.

| Method | Risk | Scope | Required | Deprecated | Docs |
|---|---|---|---|---|---|
| `ai.engine.list` | read | ai_admin |  |  | https://github.com/bitrix24/b24restdocs/blob/main/api-reference/ai/ai-engine-list.md |
| `ai.engine.register` | write | ai_admin | name,code,category,completions_url |  | https://github.com/bitrix24/b24restdocs/blob/main/api-reference/ai/ai-engine-register.md |
| `ai.engine.unregister` | destructive | ai_admin |  |  | https://github.com/bitrix24/b24restdocs/blob/main/api-reference/ai/ai-engine-unregister.md |
| `entity.get` | read | entity |  |  | https://github.com/bitrix24/b24restdocs/blob/main/api-reference/entity/entities/entity-get.md |
| `entity.add` | write | entity |  |  | https://github.com/bitrix24/b24restdocs/blob/main/api-reference/entity/entities/entity-add.md |
| `entity.update` | write | entity |  |  | https://github.com/bitrix24/b24restdocs/blob/main/api-reference/entity/entities/entity-update.md |
| `entity.item.get` | read | entity |  |  | https://github.com/bitrix24/b24restdocs/blob/main/api-reference/entity/items/entity-item-get.md |
| `entity.item.add` | write | entity |  |  | https://github.com/bitrix24/b24restdocs/blob/main/api-reference/entity/items/entity-item-add.md |
| `biconnector.source.list` | read | biconnector |  |  | https://github.com/bitrix24/b24restdocs/blob/main/api-reference/biconnector/source/biconnector-source-list.md |
| `biconnector.source.add` | write | biconnector | fields |  | https://github.com/bitrix24/b24restdocs/blob/main/api-reference/biconnector/source/biconnector-source-add.md |
| `biconnector.connector.list` | read | biconnector |  |  | https://github.com/bitrix24/b24restdocs/blob/main/api-reference/biconnector/connector/biconnector-connector-list.md |
