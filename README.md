# TempMail Bot

![TempMail Bot](https://your-image-url.com/banner.jpg)  

TempMail Bot is a Telegram bot that generates temporary email addresses and notifies users of new emails.

## Features

- 📧 Generate temporary email addresses
- 🔔 Receive email notifications in Telegram
- 🗑️ Manage temporary emails

## Getting Started

### Prerequisites

- ![Python](https://img.shields.io/badge/Python-3.6%2B-blue)
- ![MongoDB](https://img.shields.io/badge/MongoDB-Atlas-green)
- ![Telegram](https://img.shields.io/badge/Telegram-Bot_Token-blue)

### Installation

1. **Clone the repository:**

   ```sh
   git clone https://github.com/utkarshdubey2008/Tempmail.git
   cd Tempmail
   ```

2. **Install the required Python packages:**

   ```sh
   pip install -r requirements.txt
   ```

3. **Create a `.env` file and add your environment variables:**

   ```env
   BOT_TOKEN=your_telegram_bot_token
   OWNER_ID=your_telegram_id
   MONGO_URI=your_mongo_uri
   BASE_URL=https://tempmail.bjcoderx.workers.dev
   ```

### Running the Bot Locally

```sh
python bot.py
```

### Deploying to Heroku

1. **Create a new Heroku app:**

   ```sh
   heroku create your-app-name
   ```

2. **Add the necessary environment variables to Heroku:**

   ```sh
   heroku config:set BOT_TOKEN=your_telegram_bot_token
   heroku config:set OWNER_ID=your_telegram_id
   heroku config:set MONGO_URI=your_mongo_uri
   heroku config:set BASE_URL=https://tempmail.bjcoderx.workers.dev
   ```

3. **Deploy the code to Heroku:**

   ```sh
   git push heroku main
   ```

4. **Scale the worker to run the bot:**

   ```sh
   heroku ps:scale worker=1
   ```

Alternatively, you can use the Heroku button to deploy:



## Deploy to Heroku 🚀  
Click the button below to deploy your TempMail Bot instantly!  

[![Deploy](https://www.herokucdn.com/deploy/button.svg)](https://heroku.com/deploy?template=https://github.com/utkarshdubey2008/Tempmail)

### Usage

- `/start` - Start the bot and get a welcome message
- `/new` - Generate a new temporary email
- Click "Delete Email" to delete the current temporary email

### Screenshots

![Welcome Message](https://your-image-url.com/welcome.png)
*Welcome message from the bot.*

![New Email](https://your-image-url.com/new-email.png)
*Notification of a new email.*

### About the Owner

👤 **Utkarsh Dubey**

![GitHub Profile](https://avatars.githubusercontent.com/utkarshdubey2008)

- 🏷️ **GitHub:** [utkarshdubey2008](https://github.com/utkarshdubey2008)
- 📝 **LinkedIn:** [Utkarsh Dubey](https://www.linkedin.com/in/utkarshdubey2008)
- 📧 **Email:** [utkarsh.dubey@example.com](mailto:utkarsh.dubey@example.com)

### Contributing

1. Fork the repository
2. Create a new branch (`git checkout -b feature-branch`)
3. Commit your changes (`git commit -m 'Add some feature'`)
4. Push to the branch (`git push origin feature-branch`)
5. Open a Pull Request

### License

This project is licensed under the MIT License.

![MIT License](https://your-image-url.com/license.png)
