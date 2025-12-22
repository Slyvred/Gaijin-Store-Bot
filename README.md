# Gaijin-Store-Bot 
This repository contains a Telegram bot that scraps gaijin's premium store and sends an alert if a new pack is added or if prices change

Using the bot's commands your are able to filter by selecting:
- The countries
- The tiers
- The vehicle types (air, groud, sea)

## Installation
To install and run the Gaijin-Store-Bot, follow these steps:

1. Clone the repository to your local machine:
    ```
    git clone https://github.com/Slyvred/Gaijin-Store-Bot.git
    ```

2. Navigate to the project directory:
    ```
    cd Gaijin-Store-Bot
    ```

3. Install the required dependencies:
    ```
    pip install -r requirements.txt
    ```

4. Create a Telegram bot and obtain the API token. You can follow the official Telegram documentation for instructions on how to create a bot.

5. Create a `.env` file in the project directory and add the following content:
    ```
    API_TOKEN=<your_telegram_api_token>
    ```

6. Run the bot:
    ```
    python main.py
    ```

That's it! The Gaijin-Store-Bot should now be up and running. You will receive alerts whenever a new plane is added or if prices change in the Gaijin premium store.

## Usage
Alternatively, if you don't want to go through the hassle of setting up the bot yourself, you can simply use the already hosted version. Just head over to [t.me/gaijinstorecheckerbot](https://t.me/gaijinstorecheckerbot) and start using it right away!
