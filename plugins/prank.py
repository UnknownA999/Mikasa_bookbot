import asyncio
from pyrogram import Client, filters
from info import ADMINS, LOG_CHANNEL, AUTH_CHANNELS

# 🚨 FAKE CRASH LOG
FAKE_CRASH_LOG = """
<b>🚨 CRITICAL SYSTEM FAILURE - FATAL EXCEPTION 🚨</b>

<code>Traceback (most recent call last):
  File "/DreamxBotz/bot.py", line 84, in <module>
    loop.run_until_complete(dreamxbotz_start())
  File "/usr/local/lib/python3.10/asyncio/base_events.py", line 649, in run_until_complete
    return future.result()
  File "/DreamxBotz/bot.py", line 42, in dreamxbotz_start
    await db.ensure_indexes()
  File "/DreamxBotz/database/users_chats_db.py", line 112, in ensure_indexes
    await self.col.create_index("id", unique=True)
  File "/usr/local/lib/python3.10/site-packages/motor/core.py", line 1253, in create_index
    return await self.collection.create_index(keys, **kwargs)
pymongo.errors.ServerSelectionTimeoutError: cluster0-shard-00-00.mongodb.net:27017: [SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed: certificate has expired (_ssl.c:997), Timeout: 30.0s, Topology Description: <TopologyDescription id: 651e4a...>

[SYSTEM_HALT] Memory Limit Exceeded (512MB/512MB). 
FATAL ERROR: Bot forced shutdown to prevent database corruption. Initiating core dump...</code>
"""

# ✅ FAKE RECOVERY LOG
FAKE_RECOVERY_LOG = """
<b>✅ SYSTEM RECOVERY SUCCESSFUL ✅</b>

<code>[INIT] Rebooting core services... OK
[NETWORK] Re-establishing MongoDB connection... OK
[SSL] Injecting emergency certificate bypass... Handshake Successful
[DATABASE] Verifying index integrity... 100% Validated
[MEMORY] Core dump cleared. RAM usage stabilized at 45MB.

System diagnostic complete. All services are fully operational. Bot is back online! 🚀</code>
"""

@Client.on_message(filters.command("fakecrash") & filters.user(ADMINS))
async def send_fake_crash(client, message):
    if len(message.command) > 1:
        arg = message.command[1].lower()
        
        # Agar user ne 'all' likha hai
        if arg == "all":
            target_channels = set([LOG_CHANNEL])
            if AUTH_CHANNELS:
                target_channels.update(AUTH_CHANNELS)
                
            msg = await message.reply_text("⏳ <i>Broadcasting FATAL ERROR to ALL channels... Tabaahi incoming! 💥</i>")
            await asyncio.sleep(2)
            
            success = 0
            for ch in target_channels:
                try:
                    await client.send_message(ch, FAKE_CRASH_LOG)
                    success += 1
                    await asyncio.sleep(0.3)
                except Exception:
                    pass
            await msg.edit_text(f"😈 <b>Global Crash Deployed!</b> Successfully sent to {success} channels.")
            return
            
        # Agar user ne koi specific ID daali hai
        else:
            try:
                target_chat = int(arg)
            except ValueError:
                return await message.reply_text("⚠️ Bhai, ek valid integer Chat ID ya 'all' daal!")
    
    # Agar kuch nahi likha toh default LOG_CHANNEL
    else:
        target_chat = LOG_CHANNEL

    msg = await message.reply_text(f"⏳ <i>Injecting fake kernel panic into {target_chat}...</i>")
    await asyncio.sleep(2)
    try:
        await client.send_message(target_chat, FAKE_CRASH_LOG)
        await msg.edit_text(f"✅ <b>Fake crash deployed to <code>{target_chat}</code>!</b>")
    except Exception as e:
        await msg.edit_text(f"❌ Error: {e}\n(Make sure bot is admin in this chat!)")


@Client.on_message(filters.command("fakefix") & filters.user(ADMINS))
async def send_fake_recovery(client, message):
    if len(message.command) > 1:
        arg = message.command[1].lower()
        
        if arg == "all":
            target_channels = set([LOG_CHANNEL])
            if AUTH_CHANNELS:
                target_channels.update(AUTH_CHANNELS)
                
            msg = await message.reply_text("⏳ <i>Broadcasting RECOVERY to ALL channels...</i>")
            await asyncio.sleep(2)
            
            success = 0
            for ch in target_channels:
                try:
                    await client.send_message(ch, FAKE_RECOVERY_LOG)
                    success += 1
                    await asyncio.sleep(0.3)
                except Exception:
                    pass
            await msg.edit_text(f"😎 <b>Global Recovery Deployed!</b> Fixed in {success} channels. Hacker mode deactivated. 💻")
            return
            
        else:
            try:
                target_chat = int(arg)
            except ValueError:
                return await message.reply_text("⚠️ Bhai, ek valid integer Chat ID ya 'all' daal!")
    else:
        target_chat = LOG_CHANNEL

    msg = await message.reply_text(f"⏳ <i>Running diagnostic repair sequence on {target_chat}...</i>")
    await asyncio.sleep(2)
    try:
        await client.send_message(target_chat, FAKE_RECOVERY_LOG)
        await msg.edit_text(f"✅ <b>Fake recovery deployed to <code>{target_chat}</code>!</b>")
    except Exception as e:
        await msg.edit_text(f"❌ Error: {e}")
