# Noyabot
Noyabot is a simple modern Discord bot primarily designed to run a few, high-polished utility commands

As of writing, Noyabot can:
- Set reminders with language-driven time durations
- Get random users, with channel and role filters
- Robust dice roll command with math expressions
- Filter trackers from URLs, using self-updating AdGuard lists, entropy calculation, and custom precision

## Bot Invite
Use the live version here! -> [Invite Noyabot](https://discord.com/oauth2/authorize?client_id=1389044729467113594)<br/>
...or join the [discord server](https://discord.gg/Ggrtu5nRfg)!

## How to install:
### Docker (recommended)
1. Clone the repo
2. Create an .env file at the root with the following parameters:

| Param                | Description                                                                                                                                                      | Required? |
|:---------------------|:-----------------------------------------------------------------------------------------------------------------------------------------------------------------|:---------:|
| PROD_TOKEN           | The main discord bot token, this is required to run.                                                                                                             |   True    |
| ERROR_LOG_CHANNEL_ID | Private channel ID where Noyabot posts errors. If you get any errors, please report a new issue.                                                                 |   True    |
| URL_LOG_CHANNEL_ID   | Private channel ID where Noyabot posts unfiltered URLs when trying to sanitize them.                                                                            |   True    |
| DEV_TOKEN            | You can use an additional bot token for development or testing. Won't run even if present unless explicitly set, such as through an IDE's environment variables. |   False   |

3. Create a data folder for Noyabot to store and access<br/>
Edit `docker-compose.yml` to set the volume to your created data directory. The default is ('`/mnt/cache/appdata/noyabot`') which is ideal for an Unraid server, this must be changed to the location of your directory. If set properly, when the bot is first started it should immediately populate with fresh database files

4. Installation<br/>
Run `docker compose up -d --build` at the root and Noyabot will build + run automatically. This also works when updating to a newer release
