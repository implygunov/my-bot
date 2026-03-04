import os
import asyncio
import shutil
import time
from telethon import TelegramClient
from colorama import init, Fore

init(autoreset=True)

sessions = [f.replace('.session', '') for f in os.listdir() if f.endswith('.session')]

os.makedirs('valid', exist_ok=True)
os.makedirs('nevalid', exist_ok=True)
os.makedirs('trash', exist_ok=True)

processed_ids = set()

total_sessions = len(sessions)
valid_sessions = 0
has_duplicates = False


async def process_session(session):
    global valid_sessions, has_duplicates
    print(Fore.WHITE + f'┏Using session: {session}')
    client = None  
    try:
        client = TelegramClient(session, 21256606, "900987996a7ae04b6438d90a9e65ee66", system_version='4.16.30-vxCUSTOM')

        # Таймаут подключения
        try:
            await asyncio.wait_for(client.connect(), timeout=3)
        except asyncio.TimeoutError:
            print(Fore.YELLOW + f"┗Session {session} timed out during connection.")
            raise RuntimeError("Timeout during connection")

        if not await client.is_user_authorized():
            print(Fore.RED + f"┗Session {session} is not valid.")
            target_folder = 'nevalid'
        else:
            user = await client.get_me()
            user_id = user.id

            # Проверка на копию (только по ID)
            if user_id in processed_ids:
                print(Fore.RED + f"┗Session {session} is a duplicate (ID: {user_id}).")
                target_folder = 'trash'
                has_duplicates = True
            else:
                if user.bot:
                    print(Fore.MAGENTA + f"┗Session {session} belongs to a bot.")
                    target_folder = 'trash'
                else:
                    print(Fore.GREEN + f"┗Session {session} is valid and belongs to ID: {user_id}.")
                    target_folder = 'valid'

                    with open(f"{target_folder}/{session}.txt", "w") as f:
                        f.write(f"ID: {user_id}\n")

                    processed_ids.add(user_id)
                    valid_sessions += 1

    except Exception as e:
        error_message = str(e)
        if "used under two different IP addresses" in error_message:
            print(Fore.MAGENTA + f"┗Session {session} has IP conflict error.")
            target_folder = 'trash'
        else:
            print(Fore.RED + f"Error with session {session}: {error_message}")
            target_folder = 'trash'
    finally:
        if client:
            await client.disconnect()
        try:
            shutil.move(f"{session}.session", f"{target_folder}/{session}.session")
        except Exception as move_error:
            print(Fore.RED + f"Failed to move session {session} to {target_folder}: {move_error}")


async def main():
    for session in sessions:
        await process_session(session)

    time.sleep(2)

    print(Fore.CYAN + '\n📊 Итоги проверки:')
    print(Fore.CYAN + f'Всего сессий: {total_sessions}')
    print(Fore.CYAN + f'Валидных сессий: {valid_sessions}')
    print(Fore.CYAN + f'Есть копии: {"Да" if has_duplicates else "Нет"}')
    time.sleep(8888)

asyncio.run(main())
