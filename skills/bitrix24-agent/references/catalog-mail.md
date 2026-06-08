# Catalog: mail

Scope: mailboxes and email messages.

| Method | Risk | Scope | Required | Deprecated | Docs |
|---|---|---|---|---|---|
| `mail.mailbox.list` | read | mail |  |  | https://github.com/bitrix24/b24restdocs/blob/main/api-reference/rest-v3/mail/mailbox/mail-mailbox-list.md |
| `mail.mailbox.get` | read | mail | id |  | https://github.com/bitrix24/b24restdocs/blob/main/api-reference/rest-v3/mail/mailbox/mail-mailbox-get.md |
| `mail.message.list` | read | mail |  |  | https://github.com/bitrix24/b24restdocs/blob/main/api-reference/rest-v3/mail/message/mail-message-list.md |
| `mail.message.get` | read | mail | id |  | https://github.com/bitrix24/b24restdocs/blob/main/api-reference/rest-v3/mail/message/mail-message-get.md |
| `mail.message.send` | write | mail | from,to,subject,body |  | https://github.com/bitrix24/b24restdocs/blob/main/api-reference/rest-v3/mail/message/mail-message-send.md |
| `mail.message.reply` | write | mail | replyToMessageId,from,to,subject,body |  | https://github.com/bitrix24/b24restdocs/blob/main/api-reference/rest-v3/mail/message/mail-message-reply.md |
| `mail.message.forward` | write | mail | forwardMessageId,from,to,subject,body |  | https://github.com/bitrix24/b24restdocs/blob/main/api-reference/rest-v3/mail/message/mail-message-forward.md |
| `mail.message.createcrmactivity` | write | mail | messageId |  | https://github.com/bitrix24/b24restdocs/blob/main/api-reference/rest-v3/mail/message/mail-message-createcrmactivity.md |
| `mail.message.createtask` | write | mail | messageId |  | https://github.com/bitrix24/b24restdocs/blob/main/api-reference/rest-v3/mail/message/mail-message-createtask.md |
| `mail.recipient.listcontacts` | read | mail |  |  | https://github.com/bitrix24/b24restdocs/blob/main/api-reference/rest-v3/mail/recipient/mail-recipient-listcontacts.md |
