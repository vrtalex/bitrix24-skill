# Chains: bots

## 1) Stand up a chat-bot
1. `imbot.v2.Bot.register`
2. `imbot.v2.Command.register`
3. handle the command event, then `imbot.v2.Command.answer`
4. `imbot.v2.Chat.Message.send` to post into a dialog

## 2) Manage existing bots
1. `imbot.v2.Bot.list`
2. `imbot.v2.Bot.update`
3. `imbot.v2.Bot.unregister` (only with explicit destructive confirmation)
