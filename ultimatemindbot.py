import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler
from telegram.error import TelegramError

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Replace with your bot token from @BotFather
BOT_TOKEN = "8593966746:AAHIwSNPsm3sfFQytv-zRqI_7semHpW5q9I"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send a message when the command /start is issued."""
    await update.message.reply_text(
        "👋 Hello! I'm the Mention All Bot.\n\n"
        "Add me to your group/channel and give me admin rights to read messages.\n\n"
        "Commands:\n"
        "/start - Show this message\n"
        "/help - Show help information\n\n"
        "Just type @everyone in any message to mention all members!"
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send a message when the command /help is issued."""
    await update.message.reply_text(
        "📖 *How to use:*\n\n"
        "1. Add me to your group or channel\n"
        "2. Make me an admin (needed to read members)\n"
        "3. Type @everyone anywhere in your message\n"
        "4. I'll mention all registered members!\n\n"
        "*Commands:*\n"
        "/scan - Scan and add group admins\n"
        "/add @user1 @user2 - Add members by username\n"
        "/remove @user1 @user2 - Remove members by username\n"
        "/list - Show all registered members with usernames\n"
        "/help - Show this help message\n\n"
        "*Examples:*\n"
        "/add @yoonmi071775 @yu55200 @Mayyym31\n"
        "/remove @henry_casper @yoonmi071775\n\n"
        "*Note:* I can mention up to 50 users per message.",
        parse_mode='Markdown'
    )

async def mention_all(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Mention all members when @everyone is typed."""
    message = update.message
    
    # Check if message contains @everyone
    if not message.text or '@everyone' not in message.text.lower():
        return
    
    chat = message.chat
    
    # Only work in groups and channels
    if chat.type not in ['group', 'supergroup', 'channel']:
        return
    
    try:
        # Get chat administrators to check bot permissions
        admins = await context.bot.get_chat_administrators(chat.id)
        bot_admin = None
        
        for admin in admins:
            if admin.user.id == context.bot.id:
                bot_admin = admin
                break
        
        if not bot_admin:
            await message.reply_text("❌ I need to be an admin to mention members!")
            return
        
        # Get all chat members (this works for smaller groups)
        # For large groups, you'll need to maintain a database of members
        members = []
        member_count = await context.bot.get_chat_member_count(chat.id)
        
        if member_count > 200:
            await message.reply_text(
                "⚠️ This group is too large. For groups with 200+ members, "
                "I recommend using @username mentions or maintaining a member database."
            )
            return
        
        # Try to get members (this works better for smaller groups)
        # Note: Telegram API limitations make it difficult to get all members in large groups
        # You might need to track members as they send messages
        
        # Alternative approach: Mention recent active users stored in context
        if 'active_members' not in context.chat_data:
            context.chat_data['active_members'] = set()
        
        # Add current message sender
        if message.from_user and not message.from_user.is_bot:
            context.chat_data['active_members'].add(
                (message.from_user.id, message.from_user.first_name, message.from_user.username)
            )
        
        active_members = list(context.chat_data['active_members'])
        
        if not active_members:
            await message.reply_text("No active members found yet. Members will be tracked as they send messages.")
            return
        
        # Build mention list (max 50 mentions per message to avoid spam)
        mentions = []
        for user_id, first_name, username in active_members[:50]:
            # Escape special characters in names for Markdown
            safe_name = first_name.replace('[', '\\[').replace(']', '\\]').replace('_', '\\_').replace('*', '\\*').replace('`', '\\`')
            
            # Use text mention with user ID if available, otherwise use @username
            if user_id != 0:
                mentions.append(f"[{safe_name}](tg://user?id={user_id})")
            elif username:
                mentions.append(f"@{username}")
        
        if mentions:
            mention_text = "📢 " + " ".join(mentions)
            
            # Send the mention message
            try:
                await message.reply_text(
                    mention_text,
                    parse_mode='Markdown'
                )
            except TelegramError as parse_error:
                # If Markdown parsing fails, send without formatting
                logger.error(f"Markdown parse error: {parse_error}")
                # Try sending as plain text with just @usernames
                plain_mentions = []
                for user_id, first_name, username in active_members[:50]:
                    if username:
                        plain_mentions.append(f"@{username}")
                    else:
                        plain_mentions.append(first_name)
                
                if plain_mentions:
                    await message.reply_text("📢 " + " ".join(plain_mentions))
            
            # Show info about tracked members
            total_tracked = len(active_members)
            mentioned = min(total_tracked, 50)
            
            if total_tracked > 50:
                await message.reply_text(
                    f"ℹ️ Mentioned {mentioned} out of {total_tracked} tracked members "
                    f"(Telegram limit: 50 per message)"
                )
        
    except TelegramError as e:
        logger.error(f"Error mentioning members: {e}")
        await message.reply_text(f"❌ Error: {str(e)}")

async def track_members(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Track active members as they send messages and update stored usernames."""
    if not update.message or not update.message.from_user:
        return
    
    chat = update.message.chat
    user = update.message.from_user
    
    # Only track in groups/channels
    if chat.type not in ['group', 'supergroup', 'channel']:
        return
    
    # Don't track bots
    if user.is_bot:
        return
    
    # Initialize active members set if not exists
    if 'active_members' not in context.chat_data:
        context.chat_data['active_members'] = set()
    
    # Check if user was added by username only (has ID 0)
    # If so, update with real user info
    if user.username:
        # Remove old placeholder entry if exists
        for member in list(context.chat_data['active_members']):
            if member[0] == 0 and member[2] == user.username:
                context.chat_data['active_members'].remove(member)
                break
    
    # Add/update member with full info
    context.chat_data['active_members'].add(
        (user.id, user.first_name, user.username)
    )

async def new_member(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Track new members joining the group."""
    for member in update.message.new_chat_members:
        if member.is_bot:
            continue
        
        if 'active_members' not in context.chat_data:
            context.chat_data['active_members'] = set()
        
        context.chat_data['active_members'].add(
            (member.id, member.first_name, member.username)
        )

async def scan_members(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Manually scan and add all current group members."""
    chat = update.message.chat
    
    if chat.type not in ['group', 'supergroup']:
        await update.message.reply_text("❌ This command only works in groups!")
        return
    
    try:
        await update.message.reply_text("🔍 Scanning all group members... This may take a moment.")
        
        # Initialize members set
        if 'active_members' not in context.chat_data:
            context.chat_data['active_members'] = set()
        
        # Get member count
        member_count = await context.bot.get_chat_member_count(chat.id)
        
        # For small groups, try to get all members
        added_count = 0
        
        # Try to get chat administrators first
        admins = await context.bot.get_chat_administrators(chat.id)
        for admin in admins:
            if not admin.user.is_bot:
                context.chat_data['active_members'].add(
                    (admin.user.id, admin.user.first_name, admin.user.username)
                )
                added_count += 1
        
        await update.message.reply_text(
            f"✅ Scan complete!\n"
            f"📊 Total members in group: {member_count}\n"
            f"👥 Members I can mention: {len(context.chat_data['active_members'])}\n\n"
            f"ℹ️ Due to Telegram privacy restrictions, I can only mention:\n"
            f"- Members who have sent messages\n"
            f"- Group administrators\n"
            f"- Members who joined after I was added\n\n"
            f"💡 To add members manually, reply to their message with /add\n"
            f"💡 Or ask them to send at least one message in the group!"
        )
        
    except TelegramError as e:
        logger.error(f"Error scanning members: {e}")
        await update.message.reply_text(f"❌ Error: {str(e)}")

async def add_member(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Add a member to the mention list by replying to their message OR by username."""
    chat = update.message.chat
    
    if chat.type not in ['group', 'supergroup']:
        await update.message.reply_text("❌ This command only works in groups!")
        return
    
    # Initialize members set
    if 'active_members' not in context.chat_data:
        context.chat_data['active_members'] = set()
    
    # Check if usernames are provided in the command
    if context.args:
        # Adding members by username: /add @user1 @user2 @user3
        added_users = []
        failed_users = []
        
        for username in context.args:
            # Remove @ if present
            clean_username = username.replace('@', '').strip()
            
            if not clean_username:
                continue
            
            try:
                # Try to get user info from Telegram
                # Note: This only works if the bot has seen the user before
                # For new users, we'll store the username and try to match later
                
                # Store username for future matching
                # We use a placeholder ID (0) until we can get the real ID
                context.chat_data['active_members'].add(
                    (0, clean_username, clean_username)  # (id, display_name, username)
                )
                added_users.append(f"@{clean_username}")
                
            except Exception as e:
                failed_users.append(f"@{clean_username}")
        
        # Report results
        result_msg = ""
        if added_users:
            result_msg += f"✅ Added: {', '.join(added_users)}\n"
        if failed_users:
            result_msg += f"⚠️ Could not verify: {', '.join(failed_users)}\n"
        
        result_msg += f"\n👥 Total members in list: {len(context.chat_data['active_members'])}"
        result_msg += f"\n\n💡 Note: Usernames are stored. When these users send a message, their full info will be updated."
        
        await update.message.reply_text(result_msg)
        return
    
    # Original functionality: Reply to a message to add that user
    if not update.message.reply_to_message:
        await update.message.reply_text(
            "❌ Usage:\n\n"
            "Method 1: /add @username1 @username2 @username3\n"
            "Method 2: Reply to a user's message with /add\n\n"
            "Examples:\n"
            "/add @yoonmi071775 @yu55200 @Mayyym31\n"
            "OR reply to someone's message and type /add"
        )
        return
    
    target_user = update.message.reply_to_message.from_user
    
    # Don't add bots
    if target_user.is_bot:
        await update.message.reply_text("❌ I can't add bots to the mention list!")
        return
    
    # Add the member
    context.chat_data['active_members'].add(
        (target_user.id, target_user.first_name, target_user.username)
    )
    
    await update.message.reply_text(
        f"✅ Added {target_user.first_name} to the mention list!\n"
        f"👥 Total members I can mention: {len(context.chat_data['active_members'])}"
    )

async def list_members(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show all members that can be mentioned."""
    chat = update.message.chat
    
    if chat.type not in ['group', 'supergroup']:
        await update.message.reply_text("❌ This command only works in groups!")
        return
    
    if 'active_members' not in context.chat_data or not context.chat_data['active_members']:
        await update.message.reply_text(
            "❌ No members in the mention list yet!\n\n"
            "💡 Add members with: /add @username1 @username2"
        )
        return
    
    members_list = context.chat_data['active_members']
    total = len(members_list)
    
    # Create a formatted list with usernames
    member_lines = []
    for user_id, first_name, username in sorted(members_list, key=lambda x: x[1].lower()):
        if username:
            member_lines.append(f"• {first_name} (@{username})")
        else:
            member_lines.append(f"• {first_name}")
    
    # Split into chunks if too many members (Telegram message limit)
    max_per_message = 50
    
    if total <= max_per_message:
        members_text = "\n".join(member_lines)
        await update.message.reply_text(
            f"👥 *Members in mention list ({total} total):*\n\n{members_text}\n\n"
            f"💡 Use @everyone to mention all members\n"
            f"💡 Use /remove @username to remove members",
            parse_mode='Markdown'
        )
    else:
        # Send in chunks
        for i in range(0, total, max_per_message):
            chunk = member_lines[i:i+max_per_message]
            chunk_text = "\n".join(chunk)
            chunk_num = (i // max_per_message) + 1
            total_chunks = (total + max_per_message - 1) // max_per_message
            
            await update.message.reply_text(
                f"👥 *Members list (Part {chunk_num}/{total_chunks}):*\n\n{chunk_text}",
                parse_mode='Markdown'
            )

async def remove_member(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Remove a member from the mention list by replying to their message OR by username."""
    chat = update.message.chat
    
    if chat.type not in ['group', 'supergroup']:
        await update.message.reply_text("❌ This command only works in groups!")
        return
    
    if 'active_members' not in context.chat_data:
        context.chat_data['active_members'] = set()
    
    # Check if usernames are provided in the command
    if context.args:
        # Removing members by username: /remove @user1 @user2 @user3
        removed_users = []
        not_found_users = []
        
        for username in context.args:
            # Remove @ if present
            clean_username = username.replace('@', '').strip()
            
            if not clean_username:
                continue
            
            # Find and remove the member by username
            removed = False
            for member in list(context.chat_data['active_members']):
                member_username = member[2] if member[2] else ""
                if member_username.lower() == clean_username.lower():
                    context.chat_data['active_members'].remove(member)
                    removed_users.append(f"@{clean_username}")
                    removed = True
                    break
            
            if not removed:
                not_found_users.append(f"@{clean_username}")
        
        # Report results
        result_msg = ""
        if removed_users:
            result_msg += f"✅ Removed: {', '.join(removed_users)}\n"
        if not_found_users:
            result_msg += f"❌ Not found: {', '.join(not_found_users)}\n"
        
        result_msg += f"\n👥 Total members in list: {len(context.chat_data['active_members'])}"
        
        await update.message.reply_text(result_msg)
        return
    
    # Original functionality: Reply to a message to remove that user
    if not update.message.reply_to_message:
        await update.message.reply_text(
            "❌ Usage:\n\n"
            "Method 1: /remove @username1 @username2\n"
            "Method 2: Reply to a user's message with /remove\n\n"
            "Examples:\n"
            "/remove @henry_casper @yoonmi071775\n"
            "OR reply to someone's message and type /remove"
        )
        return
    
    target_user = update.message.reply_to_message.from_user
    
    # Find and remove the member
    removed = False
    for member in list(context.chat_data['active_members']):
        if member[0] == target_user.id:
            context.chat_data['active_members'].remove(member)
            removed = True
            break
    
    if removed:
        await update.message.reply_text(
            f"✅ Removed {target_user.first_name} from the mention list!\n"
            f"👥 Total members I can mention: {len(context.chat_data['active_members'])}"
        )
    else:
        await update.message.reply_text(f"❌ {target_user.first_name} was not in the mention list.")

def main():
    """Start the bot."""
    # Create the Application
    application = Application.builder().token(BOT_TOKEN).build()

    # Add handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("scan", scan_members))
    application.add_handler(CommandHandler("add", add_member))
    application.add_handler(CommandHandler("remove", remove_member))
    application.add_handler(CommandHandler("list", list_members))
    
    # Track all messages to build member list
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, track_members), group=0)
    
    # Handle @everyone mentions
    application.add_handler(MessageHandler(filters.TEXT & filters.Regex(r'(?i)@everyone'), mention_all), group=1)
    
    # Track new members
    application.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, new_member))

    # Start the Bot
    print("Bot is running...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()