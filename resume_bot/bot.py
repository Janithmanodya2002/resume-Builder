import logging
from enum import Enum

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, ReplyKeyboardRemove
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
    GETTING_EDUCATION = 10
    ASKING_TAILOR = 11
    GETTING_JOB_DESCRIPTION = 12
    AWAITING_TAILOR_APPROVAL = 13
    GENERATING_PDF = 14


# --- START HANDLER ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Starts the conversation and asks for the template using reply keyboard."""
    reply_keyboard = [["Modern", "Creative"]]

    await update.message.reply_text(
        "Welcome to the Resume Bot! Let's create your resume.\n\n"
        "Please choose a template:",
        reply_markup=ReplyKeyboardMarkup(
            reply_keyboard, one_time_keyboard=True, resize_keyboard=True
        ),
    )
    return States.SELECTING_TEMPLATE


# --- TEMPLATE SELECTION ---
async def select_template(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Stores the selected template and asks for an accent color."""
    template_name = update.message.text.strip().lower()
    if template_name not in ["modern", "creative"]:
        await update.message.reply_text(
            "Invalid choice. Please type 'Modern' or 'Creative'."
        )
        return States.SELECTING_TEMPLATE

    context.user_data["template"] = template_name
    reply_keyboard = [["Blue", "Green"], ["Red", "Purple"]]

    await update.message.reply_text(
        f"You selected the '{template_name}' template. Now, pick an accent color:",
        reply_markup=ReplyKeyboardMarkup(
            reply_keyboard, one_time_keyboard=True, resize_keyboard=True
        ),
    )
    return States.SELECTING_COLOR


# --- COLOR SELECTION ---
async def select_color(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Stores the selected color and asks for a photo."""
    color_map = {
        "Blue": "#3498db",
        "Green": "#2ecc71",
        "Red": "#e74c3c",
        "Purple": "#8e44ad",
    }

    color_choice = update.message.text.strip().capitalize()
    if color_choice not in color_map:
        await update.message.reply_text(
            "Invalid choice. Please select from Blue, Green, Red, or Purple."
        )
        return States.SELECTING_COLOR

    context.user_data["accent_color"] = color_map[color_choice]

    await update.message.reply_text(
        f"Great! You've chosen the {context.user_data['template']} template "
        f"with {color_choice} as the accent color.\n\n"
        "Now, please upload a profile photo for your resume.",
        reply_markup=ReplyKeyboardRemove(),  # Remove the keyboard so user can upload photo
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
    """Stores an experience entry and asks for the next one."""
    experience_text = update.message.text
    context.user_data["experience"].append(experience_text)
    await update.message.reply_text(f"Experience added. Enter another one, or click 'Done'.")
    return States.GETTING_EXPERIENCE


async def experience_done(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Ends the experience section, runs batch enhancement, and asks for education."""
    await update.message.reply_text(
        "Experience section complete! I will now enhance the descriptions with AI...",
        reply_markup=ReplyKeyboardRemove(),
    )

    original_experiences = context.user_data.get("experience", [])
    if original_experiences:
        enhanced_experiences = gemini_client.enhance_multiple_experiences(original_experiences)
        if enhanced_experiences:
            context.user_data["experience"] = enhanced_experiences
            await update.message.reply_text("Descriptions enhanced successfully!")
        else:
            await update.message.reply_text("AI enhancement failed, using your original descriptions.")

    # Proceed to the next step
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
    """Ends data collection and asks about tailoring."""
    await update.message.reply_text(
        "All information collected!",
        reply_markup=ReplyKeyboardRemove(),
    )
    
    keyboard = [
        [
            InlineKeyboardButton("✅ Yes, please!", callback_data="tailor_yes"),
            InlineKeyboardButton("❌ No, thanks", callback_data="tailor_no"),
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        "Would you like me to tailor your resume for a specific job description?",
        reply_markup=reply_markup,
    )
    return States.ASKING_TAILOR


async def handle_tailor_choice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handles the user's choice about tailoring."""
    query = update.callback_query
    await query.answer()

    if query.data == "tailor_yes":
        await query.edit_message_text("Great! Please paste the job description below.")
        return States.GETTING_JOB_DESCRIPTION
    else:
        await query.edit_message_text("Okay, I'll generate your resume with the information I have.")
        return await generate_and_send_pdf(update, context)


async def get_job_description(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Gets the job description and calls the tailoring AI."""
    job_description = update.message.text
    await update.message.reply_text("Analyzing the job description and tailoring your resume...")

    tailoring_suggestions = gemini_client.tailor_resume_for_job(context.user_data, job_description)

    if tailoring_suggestions:
        context.user_data["tailored_summary"] = tailoring_suggestions["tailored_summary"]
        
        keyboard = [
            [InlineKeyboardButton("✅ Apply Changes", callback_data="apply_tailoring")],
            [InlineKeyboardButton("❌ Keep Original", callback_data="reject_tailoring")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        skills_text = "\n- ".join(tailoring_suggestions["suggested_skills"])
        await update.message.reply_text(
            "Here are my suggestions:\n\n"
            "**Tailored Summary:**\n"
            f"_{tailoring_suggestions['tailored_summary']}_\n\n"
            "**Suggested Skills to Add:**\n"
            f"- {skills_text}\n\n"
            "Would you like to apply the new summary to your resume?",
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )
        return States.AWAITING_TAILOR_APPROVAL
    else:
        await update.message.reply_text("Sorry, the AI tailoring failed. I'll generate the resume with your original data.")
        return await generate_and_send_pdf(update, context)


async def handle_tailor_approval(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handles the user's choice for the tailoring and generates the PDF."""
    query = update.callback_query
    await query.answer()

    if query.data == "apply_tailoring":
        context.user_data["summary"] = context.user_data["tailored_summary"]
        await query.edit_message_text("Okay, I've updated your summary.")
    else:
        await query.edit_message_text("No problem. I'll use your original summary.")
    
    return await generate_and_send_pdf(update, context)


async def generate_and_send_pdf(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Helper function to generate, send, and clean up the PDF."""
    message_sender = update.callback_query.message if update.callback_query else update.message
    await message_sender.reply_text("I'm now generating your resume...")

    logger.info(f"Final user data: {context.user_data}")
    pdf_path = generator.generate_pdf(context.user_data)

    if pdf_path and os.path.exists(pdf_path):
        await message_sender.reply_document(
            document=open(pdf_path, 'rb'),
            filename=f"{context.user_data.get('name', 'resume')}.pdf",
            caption="Here is your generated resume!"
        )
        os.remove(pdf_path)
    else:
        await message_sender.reply_text("Sorry, something went wrong while generating your PDF.")
        
    if 'photo_path' in context.user_data:
        local_photo_path = context.user_data['photo_path'].replace('file://', '')
        if os.path.exists(local_photo_path):
            try:
                os.remove(local_photo_path)
                logger.info(f"Cleaned up photo: {local_photo_path}")
            except OSError as e:
                logger.error(f"Error cleaning up photo {local_photo_path}: {e}")

    context.user_data.clear()
    return ConversationHandler.END


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancels and ends the conversation."""
    await update.message.reply_text("Operation cancelled.")
    return ConversationHandler.END


async def invalid_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles any input that is not appropriate for the current state."""
    await update.message.reply_text(
        "Sorry, I was expecting different input. Please follow the instructions or type /cancel to start over."
    )
    # This does not change the state
    return


async def fallback_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Catches any button clicks that don't match a state."""
    query = update.callback_query
    await query.answer()
    logger.warning(f"Fallback callback handler triggered for data: {query.data}")
    await query.edit_message_text(
        "Something went wrong! This button is not active. Please type /start to begin again."
    )
    return ConversationHandler.END


def main() -> None:
    """Run the bot."""
    application = Application.builder().token(config.TELEGRAM_TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            States.SELECTING_TEMPLATE: [
                MessageHandler(filters.Regex("^(?i)(modern|creative)$"), select_template),
            ],
            States.SELECTING_COLOR: [
                MessageHandler(filters.Regex("^(?i)(blue|green|red|purple)$"), select_color),
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
            States.GETTING_EDUCATION: [
                MessageHandler(filters.Regex("^Done$"), education_done),
                MessageHandler(filters.TEXT & ~filters.COMMAND, get_education),
            ],
            States.ASKING_TAILOR: [
                CallbackQueryHandler(handle_tailor_choice)
            ],
            States.GETTING_JOB_DESCRIPTION: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, get_job_description)
            ],
            States.AWAITING_TAILOR_APPROVAL: [
                CallbackQueryHandler(handle_tailor_approval)
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
