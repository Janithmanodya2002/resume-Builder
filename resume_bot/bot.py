import logging
from enum import Enum

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters,
)

import config

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)


import os

# Define conversation states using an Enum for clarity
class States(Enum):
    START = 0
    SELECTING_TEMPLATE = 1
    SELECTING_COLOR = 2
    UPLOADING_PHOTO = 3
    GETTING_NAME = 4
    GETTING_CONTACTS = 5
    GETTING_SUMMARY = 6
    AWAITING_SUMMARY_APPROVAL = 7
    GETTING_SKILLS = 8
    GETTING_EXPERIENCE = 9
    AWAITING_EXPERIENCE_APPROVAL = 10
    GETTING_EDUCATION = 11
    GENERATING_PDF = 12


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Starts the conversation and asks for the template."""
    keyboard = [
        [
            InlineKeyboardButton("Modern", callback_data="modern"),
            InlineKeyboardButton("Creative", callback_data="creative"),
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "Welcome to the Resume Bot! Let's create your resume.\n\n"
        "First, choose a template:",
        reply_markup=reply_markup,
    )
    return States.SELECTING_TEMPLATE


async def select_template(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Stores the selected template and asks for an accent color."""
    query = update.callback_query
    await query.answer()
    context.user_data["template"] = query.data

    keyboard = [
        [
            InlineKeyboardButton("Blue", callback_data="#3498db"),
            InlineKeyboardButton("Green", callback_data="#2ecc71"),
        ],
        [
            InlineKeyboardButton("Red", callback_data="#e74c3c"),
            InlineKeyboardButton("Purple", callback_data="#8e44ad"),
        ],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(
        text=f"You selected the {query.data} template. Now, pick an accent color:",
        reply_markup=reply_markup,
    )
    return States.SELECTING_COLOR


async def select_color(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Stores the selected color and asks for a photo."""
    query = update.callback_query
    await query.answer()
    context.user_data["accent_color"] = query.data

    await query.edit_message_text(
        text=f"Great! You've chosen the {context.user_data['template']} template with your chosen accent color.\n\n"
             "Now, please upload a profile photo for your resume."
    )
    return States.UPLOADING_PHOTO


async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Stores the photo and asks for the name."""
    photo_file = await update.message.photo[-1].get_file()

    # Create a temporary directory for the user's session
    user_id = update.message.from_user.id
    temp_dir = f"/tmp/resume_bot/{user_id}"
    os.makedirs(temp_dir, exist_ok=True)

    file_path = os.path.join(temp_dir, "profile_photo.jpg")
    await photo_file.download_to_drive(file_path)

    context.user_data["photo_path"] = file_path

    await update.message.reply_text(
        "Photo received! Now, what is your full name?"
    )
    return States.GETTING_NAME


async def get_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Stores the name and asks for contact info."""
    context.user_data["name"] = update.message.text
    await update.message.reply_text(
        f"Thanks, {update.message.text}. Now, please provide your email and phone number.\n\n"
        "**Example:**\n"
        "john.doe@email.com, 123-456-7890",
        parse_mode="Markdown"
    )
    return States.GETTING_CONTACTS


from telegram import ReplyKeyboardMarkup, ReplyKeyboardRemove

async def get_contacts(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Stores contact info and asks for a summary."""
    # Simple parsing, can be improved with regex later
    contacts = [item.strip() for item in update.message.text.split(',')]
    context.user_data["email"] = contacts[0] if len(contacts) > 0 else ""
    context.user_data["phone"] = contacts[1] if len(contacts) > 1 else ""

    await update.message.reply_text(
        "Contact info saved. Now, please write a professional summary about yourself."
    )
    return States.GETTING_SUMMARY


import gemini_client

async def get_summary(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Stores the summary, gets AI enhancement, and asks for approval."""
    original_summary = update.message.text
    context.user_data["original_summary"] = original_summary

    await update.message.reply_text("Thanks. I'm now using AI to enhance your summary...")

    template_style = context.user_data.get("template", "modern")
    enhanced_summary = gemini_client.enhance_summary(original_summary, template_style=template_style)

    if enhanced_summary:
        context.user_data["enhanced_summary"] = enhanced_summary

        keyboard = [
            [InlineKeyboardButton("✅ Use AI Version", callback_data="use_ai_summary")],
            [InlineKeyboardButton("✍️ Keep My Version", callback_data="use_original_summary")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_text(
            "Here is the AI-enhanced version of your summary:\n\n"
            f"**AI Version:**\n_{enhanced_summary}_\n\n"
            f"**Your Version:**\n_{original_summary}_\n\n"
            "Which version would you like to use?",
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )
        return States.AWAITING_SUMMARY_APPROVAL
    else:
        # If AI enhancement fails, just use the original and move on
        context.user_data["summary"] = original_summary
        await update.message.reply_text(
            "AI enhancement failed. Using your original summary. Let's move on to skills."
        )
        # Fall through to the next step
        return await start_getting_skills(update, context)


async def handle_summary_approval(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handles the user's choice for the summary and asks for skills."""
    query = update.callback_query
    await query.answer()

    if query.data == "use_ai_summary":
        context.user_data["summary"] = context.user_data["enhanced_summary"]
        await query.edit_message_text("Great, I've saved the AI-enhanced summary.")
    else:
        context.user_data["summary"] = context.user_data["original_summary"]
        await query.edit_message_text("Okay, I've saved your original summary.")

    return await start_getting_skills(update, context)


async def start_getting_skills(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Shared function to start the skill collection process."""
    reply_keyboard = [["Done"]]
    message_sender = update.callback_query.message if update.callback_query else update.message
    await message_sender.reply_text(
        "Now, list your skills and rate your proficiency from 1 to 5.\n\n"
        "**Format:** `Skill Name, Rating`\n"
        "**Example:** `Python, 5`\n\n"
        "Enter one skill at a time. Click 'Done' when you are finished.",
        reply_markup=ReplyKeyboardMarkup(
            reply_keyboard, one_time_keyboard=True, input_field_placeholder="e.g., Python, 5"
        ),
        parse_mode="Markdown"
    )
    context.user_data["skills"] = []
    return States.GETTING_SKILLS


async def get_skill(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Stores a skill and its rating, then asks for the next one."""
    parts = [p.strip() for p in update.message.text.split(',')]
    if len(parts) == 2 and parts[1].isdigit() and 1 <= int(parts[1]) <= 5:
        skill_name = parts[0]
        skill_rating = int(parts[1])
        context.user_data["skills"].append({"name": skill_name, "rating": skill_rating})
        await update.message.reply_text(f"'{skill_name}' with rating {skill_rating} added. Enter another skill, or click 'Done'.")
    else:
        await update.message.reply_text(
            "Invalid format. Please use the format: `Skill Name, Rating` (e.g., Python, 5). The rating must be a number between 1 and 5."
        )
    return States.GETTING_SKILLS


async def skills_done(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Ends the skill section and asks for experience."""
    await update.message.reply_text(
        "Skills section complete! Now, let's add your work experience.",
        reply_markup=ReplyKeyboardRemove(),
    )

    reply_keyboard = [["Done"]]
    await update.message.reply_text(
        "Please enter one job at a time using this format:\n"
        "`Job Title, Company, Start Date - End Date, Key responsibilities or achievements`\n\n"
        "**Example:**\n"
        "Software Engineer, Google, 2020 - Present, Developed a scalable web application that increased user engagement by 15%.\n\n"
        "Click 'Done' when you are finished.",
        reply_markup=ReplyKeyboardMarkup(
            reply_keyboard, one_time_keyboard=True, input_field_placeholder="Enter a job"
        ),
        parse_mode="Markdown"
    )
    context.user_data["experience"] = []
    return States.GETTING_EXPERIENCE


async def get_experience(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Stores an experience, gets AI enhancement, and asks for approval."""
    original_experience = update.message.text
    context.user_data["experience"].append(original_experience) # Add original for now

    await update.message.reply_text("Using AI to enhance this entry...")

    # For simplicity, we assume the description is the last part after a comma
    parts = [p.strip() for p in original_experience.split(',')]
    description = parts[-1] if len(parts) > 1 else original_experience

    enhanced_description_list = gemini_client.enhance_experience([description])

    if enhanced_description_list:
        enhanced_description = enhanced_description_list[0]
        # Store for approval
        context.user_data["pending_experience"] = original_experience
        context.user_data["enhanced_experience_desc"] = enhanced_description

        keyboard = [
            [InlineKeyboardButton("✅ Use AI Version", callback_data="use_ai_exp")],
            [InlineKeyboardButton("✍️ Keep My Version", callback_data="use_original_exp")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_text(
            "Here is an AI-enhanced description for this role:\n\n"
            f"**AI Version:**\n_{enhanced_description}_\n\n"
            "Would you like to use the AI version for the description?",
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )
        return States.AWAITING_EXPERIENCE_APPROVAL
    else:
        # AI enhancement failed, just use the original and ask for the next one
        await update.message.reply_text("AI enhancement failed. Sticking with your version. Enter another one, or click 'Done'.")
        return States.GETTING_EXPERIENCE


async def handle_experience_approval(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handles the user's choice for the experience description."""
    query = update.callback_query
    await query.answer()

    original_experience = context.user_data.pop("pending_experience")
    parts = [p.strip() for p in original_experience.split(',')]

    if query.data == "use_ai_exp":
        enhanced_desc = context.user_data.pop("enhanced_experience_desc")
        # Replace the old description with the new one
        if len(parts) > 1:
            parts[-1] = enhanced_desc
            final_experience = ", ".join(parts)
        else:
            final_experience = enhanced_desc
        # Replace the last-added original experience with the approved one
        context.user_data["experience"][-1] = final_experience
        await query.edit_message_text("Great, I've saved the AI-enhanced version.")
    else:
        # The original is already in the list, so we just need to clean up
        context.user_data.pop("enhanced_experience_desc", None)
        await query.edit_message_text("Okay, I've saved your original version.")

    await query.message.reply_text("Enter another job experience, or click 'Done'.")
    return States.GETTING_EXPERIENCE


async def experience_done(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Ends the experience section and asks for education."""
    await update.message.reply_text(
        "Experience section complete! Now, let's add your education.",
        reply_markup=ReplyKeyboardRemove(),
    )

    reply_keyboard = [["Done"]]
    await update.message.reply_text(
        "Please enter one education entry at a time using this format:\n"
        "`Degree, University, Graduation Year`\n\n"
        "**Example:**\n"
        "B.S. in Computer Science, MIT, 2020\n\n"
        "Click 'Done' when you are finished.",
        reply_markup=ReplyKeyboardMarkup(
            reply_keyboard, one_time_keyboard=True, input_field_placeholder="Enter education"
        ),
        parse_mode="Markdown"
    )
    context.user_data["education"] = []
    return States.GETTING_EDUCATION


async def get_education(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Stores an education entry and asks for the next one."""
    education_text = update.message.text
    context.user_data["education"].append(education_text)
    await update.message.reply_text(f"Education entry added. Enter another one, or click 'Done'.")
    return States.GETTING_EDUCATION


import generator

async def education_done(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Ends data collection, generates PDF, and sends it."""
    await update.message.reply_text(
        "All information collected! I'm now generating your resume...",
        reply_markup=ReplyKeyboardRemove(),
    )

    # For debugging
    logger.info(f"Final user data: {context.user_data}")

    pdf_path = generator.generate_pdf(context.user_data)

    if pdf_path and os.path.exists(pdf_path):
        await update.message.reply_document(
            document=open(pdf_path, 'rb'),
            filename=f"{context.user_data.get('name', 'resume')}.pdf",
            caption="Here is your generated resume!"
        )
        # Clean up the generated PDF
        os.remove(pdf_path)
    else:
        await update.message.reply_text(
            "Sorry, something went wrong while generating your PDF. Please try again later."
        )

    # Clean up the user's photo if it exists
    if 'photo_path' in context.user_data:
        # The photo path is a file URI, need to convert it back to a normal path
        local_photo_path = context.user_data['photo_path'].replace('file://', '')
        if os.path.exists(local_photo_path):
            try:
                os.remove(local_photo_path)
                logger.info(f"Cleaned up photo: {local_photo_path}")
            except OSError as e:
                logger.error(f"Error cleaning up photo {local_photo_path}: {e}")

    # Clear user data for the next session
    context.user_data.clear()
    return ConversationHandler.END


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancels and ends the conversation."""
    await update.message.reply_text("Operation cancelled.")
    return ConversationHandler.END


async def invalid_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles any input that is not appropriate for the current state."""
    current_state = context.user_data.get('state') # I need to store the state first
    # A simple fallback message for now. A more advanced version could check the state.
    await update.message.reply_text(
        "Sorry, I was expecting different input. Please follow the instructions or type /cancel to start over."
    )
    # This does not change the state
    return


def main() -> None:
    """Run the bot."""
    application = Application.builder().token(config.TELEGRAM_TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            States.SELECTING_TEMPLATE: [
                CallbackQueryHandler(select_template)
            ],
            States.SELECTING_COLOR: [
                CallbackQueryHandler(select_color)
            ],
            States.UPLOADING_PHOTO: [
                MessageHandler(filters.PHOTO, handle_photo)
            ],
            States.GETTING_NAME: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, get_name)
            ],
            States.GETTING_CONTACTS: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, get_contacts)
            ],
            States.GETTING_SUMMARY: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, get_summary)
            ],
            States.AWAITING_SUMMARY_APPROVAL: [
                CallbackQueryHandler(handle_summary_approval)
            ],
            States.GETTING_SKILLS: [
                MessageHandler(filters.Regex("^Done$"), skills_done),
                MessageHandler(filters.TEXT & ~filters.COMMAND, get_skill),
            ],
            States.GETTING_EXPERIENCE: [
                MessageHandler(filters.Regex("^Done$"), experience_done),
                MessageHandler(filters.TEXT & ~filters.COMMAND, get_experience),
            ],
            States.AWAITING_EXPERIENCE_APPROVAL: [
                CallbackQueryHandler(handle_experience_approval)
            ],
            States.GETTING_EDUCATION: [
                MessageHandler(filters.Regex("^Done$"), education_done),
                MessageHandler(filters.TEXT & ~filters.COMMAND, get_education),
            ],
            # Other states will be added here
        },
        fallbacks=[
            CommandHandler("cancel", cancel),
            MessageHandler(filters.TEXT & ~filters.COMMAND, invalid_input),
        ],
    )

    application.add_handler(conv_handler)

    logger.info("Starting bot...")
    application.run_polling()


if __name__ == "__main__":
    main()
