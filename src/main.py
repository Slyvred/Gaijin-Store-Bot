import logging
import os

import dotenv

from gaijin_store_bot import Bot

dotenv.load_dotenv()
api_token = str(os.getenv("API_TOKEN"))


logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)


if __name__ == "__main__":
    bot = Bot(api_token)
    bot.application.run_polling()
