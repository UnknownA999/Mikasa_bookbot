import datetime
import time
import os
import asyncio
import logging
from pyrogram import Client, filters
from pyrogram.errors.exceptions.bad_request_400 import MessageTooLong
from pyrogram.errors import FloodWait
from database.users_chats_db import db
from info import ADMINS
from utils import users_broadcast, groups_broadcast, temp, get_readable_time, clear_junk, junk_group
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup

lock = asyncio.Lock()

@Client.on_callback_query(filters.regex(r'^broadcast_cancel'))
async def broadcast_cancel(bot, query):
    _, target = query.data.split("#", 1)
    if target == 'users':
        temp.B_USERS_CANCEL = True
        await query.message.edit("🛑 ᴛʀʏɪɴɢ ᴛᴏ ᴄᴀɴᴄᴇʟ ᴜꜱᴇʀꜱ ʙʀᴏᴀᴅᴄᴀꜱᴛɪɴɢ...")
    elif target == 'groups':
        temp.B_GROUPS_CANCEL = True
        await query.message.edit("🛑 ᴛʀʏɪɴɢ ᴛᴏ ᴄᴀɴᴄᴇʟ ɢʀᴏᴜᴘꜱ ʙʀᴏᴀᴅᴄᴀꜱᴛɪɴɢ...")

@Client.on_message(filters.command("broadcast") & filters.user(ADMINS) & filters.reply)
async def broadcast_users(bot, message):
    if lock.locked():
        return await message.reply("⚠️ Another broadcast is in progress. Please wait...")
    ask = await message.reply(
        "<b>Do you want to pin this message in users?</b>",
        reply_markup=ReplyKeyboardMarkup([["Yes", "No"]], one_time_keyboard=True, resize_keyboard=True)
    )
    try:
        dreamxbotz_user_response = await bot.listen(chat_id=message.chat.id, user_id=message.from_user.id, timeout=60)
    except asyncio.TimeoutError:
        await ask.delete()
        return await message.reply("❌ Timed out. Broadcast cancelled.")
    await ask.delete()
    if dreamxbotz_user_response.text not in ("Yes", "No"):
        return await message.reply("❌ Invalid input. Broadcast cancelled.")

    is_pin = dreamxbotz_user_response.text == "Yes"
    b_msg = message.reply_to_message
    users = [user async for user in await db.get_all_users()]
    total_users = len(users)
    dreamxbotz_status_msg = await message.reply_text("📤 <b>Broadcasting your message...</b>")
    success = blocked = deleted = failed = 0
    start_time = time.time()
    cancelled = False

    async def send(user):
        try:
            _, result = await users_broadcast(int(user["id"]), b_msg, is_pin)
            return result
        except Exception as e:
            logging.exception(f"Error sending broadcast to {user['id']}")
            return "Error"

    async with lock:
        for i in range(0, total_users, 100):
            if temp.B_USERS_CANCEL:
                temp.B_USERS_CANCEL = False
                cancelled = True
                break
            batch = users[i:i + 100]
            results = await asyncio.gather(*[send(user) for user in batch])

            for res in results:
                if res == "Success":
                    success += 1
                elif res == "Blocked":
                    blocked += 1
                elif res == "Deleted":
                    deleted += 1
                elif res == "Error":
                    failed += 1

            done = i + len(batch)
            elapsed = get_readable_time(time.time() - start_time)
            await dreamxbotz_status_msg.edit(
                f"📣 <b>Broadcast Progress....:</b>\n\n"
                f"👥 Total: <code>{total_users}</code>\n"
                f"✅ Done: <code>{done}</code>\n"
                f"📬 Success: <code>{success}</code>\n"
                f"⛔ Blocked: <code>{blocked}</code>\n"
                f"🗑️ Deleted: <code>{deleted}</code>\n"
                f"⏱️ Time: {elapsed}",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("❌ CANCEL", callback_data="broadcast_cancel#users")]
                ])
            )
            await asyncio.sleep(0.1)
    elapsed = get_readable_time(time.time() - start_time)
    final_status = (
        f"{'❌ <b>Broadcast Cancelled.</b>' if cancelled else '✅ <b>Broadcast Completed.</b>'}\n\n"
        f"🕒 Time: {elapsed}\n"
        f"👥 Total: <code>{total_users}</code>\n"
        f"📬 Success: <code>{success}</code>\n"
        f"⛔ Blocked: <code>{blocked}</code>\n"
        f"🗑️ Deleted: <code>{deleted}</code>\n"
        f"❌ Failed: <code>{failed}</code>"
    )
    await dreamxbotz_status_msg.edit(final_status)


@Client.on_message(filters.command("grp_broadcast") & filters.user(ADMINS) & filters.reply)
async def broadcast_group(bot, message):
    ask = await message.reply(
        "<b>Do you want to pin this message in groups?</b>",
        reply_markup=ReplyKeyboardMarkup([["Yes", "No"]], one_time_keyboard=True, resize_keyboard=True)
    )
    try:
        dreamxbotz_user_response = await bot.listen(chat_id=message.chat.id, user_id=message.from_user.id, timeout=60)
    except asyncio.TimeoutError:
        await ask.delete()
        return await message.reply("❌ Timed out. Broadcast cancelled.")
    await ask.delete()
    if dreamxbotz_user_response.text not in ("Yes", "No"):
        return await message.reply("❌ Invalid input. Broadcast cancelled.")

    is_pin = dreamxbotz_user_response.text == "Yes"
    b_msg = message.reply_to_message
    chats = await db.get_all_chats()
    total_chats = await db.total_chat_count()
    dreamxbotz_status_msg = await message.reply_text("📤 <b>Broadcasting your message to groups...</b>")
    start_time = time.time()
    done = success = failed = 0
    cancelled = False

    async with lock:
        async for chat in chats:
            time_taken = get_readable_time(time.time() - start_time)
            if temp.B_GROUPS_CANCEL:
                temp.B_GROUPS_CANCEL = False
                cancelled = True
                break
            try:
                sts = await groups_broadcast(int(chat['id']), b_msg, is_pin)
            except Exception as e:
                logging.exception(f"Error broadcasting to group {chat['id']}")
                sts = 'Error'
            if sts == "Success":
                success += 1
            else:
                failed += 1
            done += 1
            if done % 10 == 0:
                btn = [[InlineKeyboardButton("❌ CANCEL", callback_data="broadcast_cancel#groups")]]
                await dreamxbotz_status_msg.edit(
                    f"📣 <b>Group broadcast progress:</b>\n\n"
                    f"👥 Total Groups: <code>{total_chats}</code>\n"
                    f"✅ Completed: <code>{done} / {total_chats}</code>\n"
                    f"📬 Success: <code>{success}</code>\n"
                    f"❌ Failed: <code>{failed}</code>",
                    reply_markup=InlineKeyboardMarkup(btn)
                )
    time_taken = get_readable_time(time.time() - start_time)
    dreamxbotz_text = (
        f"{'❌ <b>Groups broadcast cancelled!</b>' if cancelled else '✅ <b>Group broadcast completed.</b>'}\n"
        f"⏱️ Completed in {time_taken}\n\n"
        f"👥 Total Groups: <code>{total_chats}</code>\n"
        f"✅ Completed: <code>{done} / {total_chats}</code>\n"
        f"📬 Success: <code>{success}</code>\n"
        f"❌ Failed: <code>{failed}</code>"
    )
    try:
        await dreamxbotz_status_msg.edit(dreamxbotz_text)
    except MessageTooLong:
        with open("reason.txt", "w+") as outfile:
            outfile.write(str(failed))
        await message.reply_document(
            "reason.txt", caption=dreamxbotz_text
        )
        os.remove("reason.txt")

@Client.on_message(filters.command("clear_junk") & filters.user(ADMINS))
async def remove_junkuser__db(bot, message):
    users = await db.get_all_users()
    b_msg = message 
    sts = await message.reply_text('ɪɴ ᴘʀᴏɢʀᴇss.... ᴘʟᴇᴀsᴇ ᴡᴀɪᴛ')   
    start_time = time.time()
    total_users = await db.total_users_count()
    blocked = 0
    deleted = 0
    failed = 0
    done = 0
    async for user in users:
        pti, sh = await clear_junk(int(user['id']), b_msg)
        if pti == False:
            if sh == "Blocked":
                blocked+=1
            elif sh == "Deleted":
                deleted += 1
            elif sh == "Error":
                failed += 1
        done += 1
        if not done % 50:
            await sts.edit(f"In Progress:\n\nTotal Users {total_users}\nCompleted: {done} / {total_users}\nBlocked: {blocked}\nDeleted: {deleted}")    
    time_taken = datetime.timedelta(seconds=int(time.time()-start_time))
    await sts.delete()
    await bot.send_message(message.chat.id, f"Completed:\nCompleted in {time_taken} seconds.\n\nTotal Users {total_users}\nCompleted: {done} / {total_users}\nBlocked: {blocked}\nDeleted: {deleted}")

@Client.on_message(filters.command(["junk_group", "clear_junk_group"]) & filters.user(ADMINS))
async def junk_clear_group(bot, message):
    groups = await db.get_all_chats()
    if not groups:
        grp = await message.reply_text("❌ Nᴏ ɢʀᴏᴜᴘs ғᴏᴜɴᴅ ғᴏʀ ᴄʟᴇᴀʀ Jᴜɴᴋ ɢʀᴏᴜᴘs.")
        await asyncio.sleep(60)
        await grp.delete()
        return
    b_msg = message
    sts = await message.reply_text(text='..............')
    start_time = time.time()
    total_groups = await db.total_chat_count()
    done = 0
    failed = ""
    deleted = 0
    async for group in groups:
        pti, sh, ex = await junk_group(int(group['id']), b_msg)        
        if pti == False:
            if sh == "deleted":
                deleted+=1 
                failed += ex 
                try:
                    await bot.leave_chat(int(group['id']))
                except Exception as e:
                    print(f"{e} > {group['id']}")  
        done += 1
        if not done % 50:
            await sts.edit(f"in progress:\n\nTotal Groups {total_groups}\nCompleted: {done} / {total_groups}\nDeleted: {deleted}")    
    time_taken = datetime.timedelta(seconds=int(time.time()-start_time))
    await sts.delete()
    try:
        await bot.send_message(message.chat.id, f"Completed:\nCompleted in {time_taken} seconds.\n\nTotal Groups {total_groups}\nCompleted: {done} / {total_groups}\nDeleted: {deleted}\n\nFiled Reson:- {failed}")    
    except MessageTooLong:
        with open('junk.txt', 'w+') as outfile:
            outfile.write(failed)
        await message.reply_document('junk.txt', caption=f"Completed:\nCompleted in {time_taken} seconds.\n\nTotal Groups {total_groups}\nCompleted: {done} / {total_groups}\nDeleted: {deleted}")
        os.remove("junk.txt")

# ==========================================
# 🚀 NEW AD MONETIZATION COMMANDS BELOW 🚀
# ==========================================

@Client.on_message(filters.command("ad_broadcast") & filters.user(ADMINS) & filters.reply)
async def ad_broadcast(bot, message):
    """
    Sends an ad to all users and captures their message_ids to database 
    so they can be cleanly deleted later. 
    Usage: Reply to an ad with /ad_broadcast [time] (e.g. /ad_broadcast 1_day)
    """
    if lock.locked():
        return await message.reply("⚠️ Another broadcast is in progress. Please wait...")
    
    args = message.text.split()
    duration = args[1] if len(args) > 1 else "lifetime"
    b_msg = message.reply_to_message
    
    users = [user async for user in await db.get_all_users()]
    total_users = len(users)
    
    status_msg = await message.reply_text(f"📤 **Broadcasting Ad...**\nTarget Duration: {duration}")
    
    broadcast_id = f"ad_{int(time.time())}"
    successful_deliveries = []
    success = fail = 0
    
    async with lock:
        for user in users:
            try:
                # Copy message guarantees exact ad replica & returns the new message object
                sent_msg = await b_msg.copy(chat_id=int(user["id"]))
                successful_deliveries.append({
                    "chat_id": int(user["id"]),
                    "message_id": sent_msg.id
                })
                success += 1
                
            except FloodWait as e:
                # Telegram's strict rate limit protection
                await asyncio.sleep(e.value)
                sent_msg = await b_msg.copy(chat_id=int(user["id"]))
                successful_deliveries.append({
                    "chat_id": int(user["id"]),
                    "message_id": sent_msg.id
                })
                success += 1
                
            except Exception:
                fail += 1
            
            # Absolute magic delay to keep bot flawlessly unbanned
            await asyncio.sleep(0.05) 
            
            if (success + fail) % 50 == 0:
                await status_msg.edit(f"📣 **Ad Broadcast Progress:**\n✅ Sent: {success}\n❌ Failed: {fail}\nTotal: {total_users}")

    # Store IDs in MongoDB so /unbroadcast can find them later
    if successful_deliveries:
        await db.db["active_ads"].insert_one({
            "broadcast_id": broadcast_id,
            "duration": duration,
            "timestamp": int(time.time()),
            "messages": successful_deliveries
        })
        
    await status_msg.edit(f"📊 **Ad Broadcast Complete**\nID: `{broadcast_id}`\nDuration: {duration}\n✅ Success: {success}\n❌ Failed: {fail}")


@Client.on_message(filters.command("unbroadcast") & filters.user(ADMINS))
async def unbroadcast_ad(bot, message):
    """
    Cleans up old ads to prevent bot spam.
    Usage: /unbroadcast last (deletes the most recent ad)
           /unbroadcast all (deletes all active ads in DB)
    """
    args = message.text.split()
    if len(args) < 2:
        return await message.reply("⚠️ Please specify a target: `/unbroadcast last` or `/unbroadcast all`")
    
    target = args[1].lower()
    status_msg = await message.reply("🧹 **Gathering old ads to delete...**")
    
    # Fetch target ads from database
    if target == "all":
        target_broadcasts = await db.db["active_ads"].find({}).to_list(length=None)
    elif target == "last":
        target_broadcasts = await db.db["active_ads"].find({}).sort("timestamp", -1).limit(1).to_list(length=None)
    else:
        return await status_msg.edit("❌ Invalid target. Use 'last' or 'all'.")

    if not target_broadcasts:
        return await status_msg.edit("❌ No active ads found in the database.")

    deleted_count = 0
    for ad in target_broadcasts:
        for msg_data in ad['messages']:
            try:
                await bot.delete_messages(chat_id=msg_data['chat_id'], message_ids=msg_data['message_id'])
                deleted_count += 1
            except Exception:
                # User might have manually deleted the chat history, safely ignore
                pass 
                
            await asyncio.sleep(0.05) # Rate limit protection for deletions
            
        # Clear the completed broadcast from the database
        await db.db["active_ads"].delete_one({"_id": ad["_id"]})
        
    await status_msg.edit(f"🧹 **Unbroadcast Complete!**\nSuccessfully deleted `{deleted_count}` promotional messages.")

@Client.on_message(filters.command("export_ids") & filters.user(ADMINS))
async def export_user_ids(bot, message):
    """
    Generates a .txt file of all User IDs for Telega.io verification.
    """
    sts = await message.reply("⏳ **Generating User ID list for Telega.io...**")
    file_name = "mikasa_user_ids.txt"
    
    try:
        # We use the existing get_all_users() from your db object
        users = await db.get_all_users()
        
        with open(file_name, "w") as f:
            async for user in users:
                # Standard Telega.io format: One ID per line
                f.write(f"{user['id']}\n")
        
        await message.reply_document(
            document=file_name,
            caption="✅ **Export Complete!**\nUpload this file to Telega.io for verification."
        )
        
        # Cleanup file from Render server
        if os.path.exists(file_name):
            os.remove(file_name)
        await sts.delete()
        
    except Exception as e:
        logging.exception("Failed to export IDs")
        await sts.edit(f"❌ **Error:** `{e}`")
