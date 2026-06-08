# Chains: mail

## 1) Read the inbox
1. `mail.mailbox.list`
2. `mail.message.list` with a deterministic filter
3. `mail.message.get` for full content

## 2) Act on a message
1. `mail.message.get`
2. `mail.message.createtask` or `mail.message.createcrmactivity`
3. `mail.message.reply`
