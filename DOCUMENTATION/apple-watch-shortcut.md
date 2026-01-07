# Apple Watch Siri Shortcut Setup Guide

This guide walks you through setting up a Siri Shortcut to quickly add todo items to your Claude Assistant bot from your Apple Watch.

## Overview

**Goal:** Say "Hey Siri, add to my todo list" and dictate a task that gets sent to your Telegram bot with an `[APPLE-WATCH]` prefix for quick processing.

**Flow:**
```
Apple Watch → Siri → Shortcut → TG Watch → Telegram Bot → Backend
```

## Prerequisites

- Apple Watch Series 4 or later (watchOS 9+)
- iPhone with iOS 16+ paired to the watch
- [TG Watch app](https://apps.apple.com/us/app/tg-watch-telegram-watch-app/id6469582116) installed
- Your Telegram bot already set up and accessible

## Step 1: Install TG Watch

1. On your **iPhone**, open the **App Store**
2. Search for **"TG Watch"**
3. Install the app (free tier available)
4. Open TG Watch and log into your Telegram account
5. Navigate to your bot chat to ensure it's accessible

## Step 2: Enable Shortcut Syncing

On your **iPhone**:

1. Open **Settings**
2. Scroll down to **Shortcuts**
3. Toggle on **iCloud Sync**

This ensures shortcuts sync between your iPhone and Apple Watch.

## Step 3: Create the Shortcut (iPhone)

Open the **Shortcuts** app on your iPhone:

### 3.1 Create New Shortcut
- Tap **+** (top right corner)

### 3.2 Add "Dictate Text" Action
- Tap **"Add Action"**
- Search for: `Dictate`
- Select **"Dictate Text"**

### 3.3 Add "Text" Action
This builds the prefixed message.

- Tap **+** or **"Add Action"**
- Search for: `Text`
- Select **"Text"** (the plain one, not "Get Text from Input")
- In the text field, type exactly:
  ```
  [APPLE-WATCH]
  ```
  *(include the space after the closing bracket)*

- Tap **after** that space
- Above the keyboard, you'll see variables - tap **"Dictated Text"**
- Your text field should now show: `[APPLE-WATCH] Dictated Text`

### 3.4 Add "TG Watch - Send Message to" Action
- Tap **+** or **"Add Action"**
- Search for: `TG Watch`
- Select **"Send Message to"**
- For **Content**: tap it, then select the **"Text"** variable from step 3.3
- Leave **Contact** blank for now (you'll set this on the watch)

### 3.5 Add Confirmation (Optional but Recommended)
- Tap **+** or **"Add Action"**
- Search for: `Speak`
- Select **"Speak Text"**
- Type: `Todo sent`

### 3.6 Rename the Shortcut
- Tap the name at the very top (probably says "New Shortcut 1")
- Change it to: **Add to my todo list**

### 3.7 Enable Apple Watch Sync
- Tap the **ⓘ** icon (top right) or tap the dropdown arrow next to the name
- Toggle on **"Show on Apple Watch"**
- Tap **Done**

## Step 4: Configure Contact on Apple Watch

The TG Watch app requires you to select the contact from the watch itself.

1. Wait 30 seconds for the shortcut to sync
2. On your **Apple Watch**, open the **Shortcuts** app
3. Find **"Add to my todo list"**
4. Tap and hold → select **Edit**
5. Tap the **Contact** field
6. Select your Telegram bot from the list
7. Save/confirm the changes

## Step 5: Test the Shortcut

### From Apple Watch:
1. Raise your wrist
2. Say: **"Hey Siri, add to my todo list"**
3. When prompted, dictate your task (e.g., "Buy groceries")
4. The shortcut should:
   - Capture your dictation
   - Send `[APPLE-WATCH] Buy groceries` to your bot
   - Speak "Todo sent" as confirmation

### From iPhone:
The same shortcut works from your iPhone too - just say the trigger phrase.

## Shortcut Summary

| Step | Action | Output |
|------|--------|--------|
| 1 | Dictate Text | Captures spoken input |
| 2 | Text | Creates `[APPLE-WATCH] {input}` |
| 3 | TG Watch Send | Sends to bot via Telegram |
| 4 | Speak Text | Confirms "Todo sent" |

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Shortcut not on watch | Settings → Shortcuts → iCloud Sync (toggle off/on) |
| Contact picker empty | Open TG Watch on watch, navigate to bot chat first |
| "Need Apple Watch" message | Contact must be selected on watch, not iPhone |
| Shortcut not syncing | Restart both iPhone and Apple Watch |
| TG Watch actions not found | Open TG Watch app once to register its Shortcuts actions |

## Backend Handling

Messages from this shortcut arrive with the `[APPLE-WATCH]` prefix. Your backend should:

1. Detect the prefix
2. Parse the todo item
3. Create the todo
4. Send a brief confirmation (e.g., "Todo received!")

Example message your bot receives:
```
[APPLE-WATCH] Buy groceries
```

See the backend message handler for implementation details.

## Alternative Apps

If TG Watch doesn't work for your setup, consider:

- **[Pigeon for Telegram](https://apps.apple.com/us/app/pigeon-for-telegram/id1671939892)** - Paid app with native Siri integration, may allow contact selection from iPhone

## Notes

- The official Telegram app does **not** have an Apple Watch app
- TG Watch is a third-party standalone Telegram client for watchOS
- Voice messages are also supported if you prefer audio over dictation
- The shortcut works on cellular Apple Watches without iPhone nearby
