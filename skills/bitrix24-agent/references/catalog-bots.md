# Catalog: bots

Scope: chat-bot construction (imbot.v2).

| Method | Risk | Scope | Required | Deprecated | Docs |
|---|---|---|---|---|---|
| `imbot.v2.Bot.register` | write | imbot | fields |  | https://github.com/bitrix24/b24restdocs/blob/main/api-reference/chat-bots/chat-bots-v2/imbot.v2/bots/bot-register.md |
| `imbot.v2.Bot.get` | read | imbot |  |  | https://github.com/bitrix24/b24restdocs/blob/main/api-reference/chat-bots/chat-bots-v2/imbot.v2/bots/bot-get.md |
| `imbot.v2.Bot.list` | read | imbot |  |  | https://github.com/bitrix24/b24restdocs/blob/main/api-reference/chat-bots/chat-bots-v2/imbot.v2/bots/bot-list.md |
| `imbot.v2.Bot.update` | write | imbot | botId,fields |  | https://github.com/bitrix24/b24restdocs/blob/main/api-reference/chat-bots/chat-bots-v2/imbot.v2/bots/bot-update.md |
| `imbot.v2.Bot.unregister` | destructive | imbot | botId |  | https://github.com/bitrix24/b24restdocs/blob/main/api-reference/chat-bots/chat-bots-v2/imbot.v2/bots/bot-unregister.md |
| `imbot.v2.Command.register` | write | imbot | botId,fields |  | https://github.com/bitrix24/b24restdocs/blob/main/api-reference/chat-bots/chat-bots-v2/imbot.v2/commands/command-register.md |
| `imbot.v2.Command.list` | read | imbot | botId |  | https://github.com/bitrix24/b24restdocs/blob/main/api-reference/chat-bots/chat-bots-v2/imbot.v2/commands/command-list.md |
| `imbot.v2.Command.answer` | write | imbot | botId,commandId,messageId,dialogId |  | https://github.com/bitrix24/b24restdocs/blob/main/api-reference/chat-bots/chat-bots-v2/imbot.v2/commands/command-answer.md |
| `imbot.v2.Command.unregister` | destructive | imbot | botId,commandId |  | https://github.com/bitrix24/b24restdocs/blob/main/api-reference/chat-bots/chat-bots-v2/imbot.v2/commands/command-unregister.md |
| `imbot.v2.Chat.add` | write | imbot | botId |  | https://github.com/bitrix24/b24restdocs/blob/main/api-reference/chat-bots/chat-bots-v2/imbot.v2/chats/chat-add.md |
| `imbot.v2.Chat.get` | read | imbot | botId,dialogId |  | https://github.com/bitrix24/b24restdocs/blob/main/api-reference/chat-bots/chat-bots-v2/imbot.v2/chats/chat-get.md |
| `imbot.v2.Chat.User.add` | write | imbot | botId,dialogId,userIds |  | https://github.com/bitrix24/b24restdocs/blob/main/api-reference/chat-bots/chat-bots-v2/imbot.v2/chats/chat-user-add.md |
| `imbot.v2.Chat.Message.send` | write | imbot | botId,dialogId |  | https://github.com/bitrix24/b24restdocs/blob/main/api-reference/chat-bots/chat-bots-v2/imbot.v2/messages/chat-message-send.md |
| `imbot.v2.Chat.Message.update` | write | imbot | botId,messageId,fields |  | https://github.com/bitrix24/b24restdocs/blob/main/api-reference/chat-bots/chat-bots-v2/imbot.v2/messages/chat-message-update.md |
| `imbot.v2.Chat.Message.delete` | destructive | imbot | botId,messageId |  | https://github.com/bitrix24/b24restdocs/blob/main/api-reference/chat-bots/chat-bots-v2/imbot.v2/messages/chat-message-delete.md |
| `imbot.v2.Event.get` | read | imbot | botId |  | https://github.com/bitrix24/b24restdocs/blob/main/api-reference/chat-bots/chat-bots-v2/imbot.v2/events/event-get.md |
