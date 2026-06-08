# Catalog: comms

Scope: chats, chat-bots, messaging, telephony.

| Method | Risk | Scope | Required | Deprecated | Docs |
|---|---|---|---|---|---|
| `im.message.add` | write | im | DIALOG_ID,MESSAGE |  | https://github.com/bitrix24/b24restdocs/blob/main/api-reference/chats/messages/im-message-add.md |
| `im.message.update` | write | im | MESSAGE_ID |  | https://github.com/bitrix24/b24restdocs/blob/main/api-reference/chats/messages/im-message-update.md |
| `im.message.delete` | destructive | im | MESSAGE_ID |  | https://github.com/bitrix24/b24restdocs/blob/main/api-reference/chats/messages/im-message-delete.md |
| `im.dialog.messages.get` | read | im | DIALOG_ID |  | https://github.com/bitrix24/b24restdocs/blob/main/api-reference/chats/messages/im-dialog-messages-get.md |
| `imbot.v2.Bot.register` | write | imbot | fields |  | https://github.com/bitrix24/b24restdocs/blob/main/api-reference/chat-bots/chat-bots-v2/imbot.v2/bots/bot-register.md |
| `imbot.v2.Command.register` | write | imbot | botId,fields |  | https://github.com/bitrix24/b24restdocs/blob/main/api-reference/chat-bots/chat-bots-v2/imbot.v2/commands/command-register.md |
| `imbot.v2.Command.answer` | write | imbot | botId,commandId,messageId,dialogId |  | https://github.com/bitrix24/b24restdocs/blob/main/api-reference/chat-bots/chat-bots-v2/imbot.v2/commands/command-answer.md |
| `imbot.register` | write | imbot | CODE,EVENT_MESSAGE_ADD,EVENT_WELCOME_MESSAGE,EVENT_BOT_DELETE,PROPERTIES | → imbot.v2.Bot.register | https://github.com/bitrix24/b24restdocs/blob/main/api-reference/chat-bots/outdated/bots/imbot-register.md |
| `imbot.command.register` | write | imbot | BOT_ID,COMMAND,EVENT_COMMAND_ADD,LANG | → imbot.v2.Command.register | https://github.com/bitrix24/b24restdocs/blob/main/api-reference/chat-bots/outdated/commands/imbot-command-register.md |
| `imbot.command.answer` | write | imbot | COMMAND_ID,COMMAND,MESSAGE_ID,MESSAGE | → imbot.v2.Command.answer | https://github.com/bitrix24/b24restdocs/blob/main/api-reference/chat-bots/outdated/commands/imbot-command-answer.md |
| `telephony.externalCall.register` | write | telephony | USER_ID,USER_PHONE_INNER,PHONE_NUMBER,TYPE |  | https://github.com/bitrix24/b24restdocs/blob/main/api-reference/telephony/telephony-external-call-register.md |
| `telephony.externalCall.finish` | write | telephony | CALL_ID,USER_ID,USER_PHONE_INNER |  | https://github.com/bitrix24/b24restdocs/blob/main/api-reference/telephony/telephony-external-call-finish.md |
| `messageservice.sender.list` | read | messageservice |  |  | https://github.com/bitrix24/b24restdocs/blob/main/api-reference/messageservice/messageservice-sender-list.md |
| `imconnector.list` | read | imopenlines |  |  | https://github.com/bitrix24/b24restdocs/blob/main/api-reference/imopenlines/imconnector/imconnector-list.md |
| `imopenlines.config.list.get` | read | imopenlines |  |  | https://github.com/bitrix24/b24restdocs/blob/main/api-reference/imopenlines/openlines/imopenlines-config-list-get.md |
| `imopenlines.config.get` | read | imopenlines | CONFIG_ID |  | https://github.com/bitrix24/b24restdocs/blob/main/api-reference/imopenlines/openlines/imopenlines-config-get.md |
| `imopenlines.crm.message.add` | write | imopenlines | CRM_ENTITY_TYPE,CRM_ENTITY,USER_ID,CHAT_ID,MESSAGE |  | https://github.com/bitrix24/b24restdocs/blob/main/api-reference/imopenlines/openlines/messages/imopenlines-crm-message-add.md |
| `imopenlines.bot.session.transfer` | write | imopenlines,imbot | CHAT_ID |  | https://github.com/bitrix24/b24restdocs/blob/main/api-reference/imopenlines/openlines/chat-bots/imopenlines-bot-session-transfer.md |
| `mailservice.list` | read | mailservice |  |  | https://github.com/bitrix24/b24restdocs/blob/main/api-reference/mailservice/mailservice-list.md |
| `im.notify.system.add` | write | im | USER_ID,MESSAGE |  | https://github.com/bitrix24/b24restdocs/blob/main/api-reference/chats/notifications/im-notify-system-add.md |
| `im.notify.personal.add` | write | im | USER_ID,MESSAGE |  | https://github.com/bitrix24/b24restdocs/blob/main/api-reference/chats/notifications/im-notify-personal-add.md |
| `im.chat.add` | write | im |  |  | https://github.com/bitrix24/b24restdocs/blob/main/api-reference/chats/im-chat-add.md |
| `im.notify.delete` | destructive | im | ID,TAG,SUB_TAG |  | https://github.com/bitrix24/b24restdocs/blob/main/api-reference/chats/notifications/im-notify-delete.md |
| `im.chat.get` | read | im | ENTITY_TYPE,ENTITY_ID |  | https://github.com/bitrix24/b24restdocs/blob/main/api-reference/chats/im-chat-get.md |
| `im.chat.leave` | write | im | CHAT_ID |  | https://github.com/bitrix24/b24restdocs/blob/main/api-reference/chats/chat-users/im-chat-leave.md |
| `im.chat.setOwner` | write | im | CHAT_ID,USER_ID |  | https://github.com/bitrix24/b24restdocs/blob/main/api-reference/chats/chat-update/im-chat-set-owner.md |

Event docs:
- https://github.com/bitrix24/b24restdocs/blob/main/api-reference/chat-bots/messages/events/on-imbot-message-add.md
- https://github.com/bitrix24/b24restdocs/blob/main/api-reference/chat-bots/commands/events/on-im-command-add.md
