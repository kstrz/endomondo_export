import sys
import aiohttp
import asyncio

FILE_FORMAT = 'TCX'
DOWNLOAD_TRAININGS_TASKS = 10
UPLOAD_TRAININGS_TASKS = 10

ENDOMONDO_BASE_URL = 'https://www.endomondo.com/rest/'
ENDOMONDO_LOGIN_URL = 'session'
ENDOMONDO_LIST_TRAININGS_URL = 'v1/users/{}/workouts/history?offset={}&limit={}'
ENDOMONDO_DOWNLOAD_TRAINING_URL = 'v1/users/{}/workouts/{}/export?format={}'

STRAVA_API_BASE_URL = "https://www.strava.com/api/v3/"


async def endomondo_login(session: aiohttp.ClientSession, login: str, password: str):
    async with session.post(ENDOMONDO_BASE_URL + ENDOMONDO_LOGIN_URL, json={
        'email': login,
        'password': password
    }) as response:
        user_data = await response.json()
        return user_data['id']


async def get_trainings_ids(session: aiohttp.ClientSession, user_id: str, training_ids_queue: asyncio.Queue):
    limit = 25
    offset = 0
    while True:
        async with session.get(
                ENDOMONDO_BASE_URL + ENDOMONDO_LIST_TRAININGS_URL.format(user_id, offset, limit)) as response:

            trainings_data = await response.json()
            trainings_data = trainings_data.get('data')

            if not trainings_data:
                print('get_trainings_ids finished')
                return
            for training_id in trainings_data:
                await training_ids_queue.put(training_id['id'])
            offset += limit


async def download_training(session: aiohttp.ClientSession, user_id: str, training_ids_queue: asyncio.Queue,
                            training_data_queue: asyncio.Queue):
    while True:
        training_id = await training_ids_queue.get()
        async with session.get(
                ENDOMONDO_BASE_URL + ENDOMONDO_DOWNLOAD_TRAINING_URL.format(user_id, training_id,
                                                                            FILE_FORMAT)) as response:
            await training_data_queue.put(await response.read())
            training_ids_queue.task_done()
            print(f'downloaded training: {training_id}')


async def upload_training(session: aiohttp.ClientSession, training_data_queue: asyncio.Queue, strava_access_token: str):
    while True:
        training_data = await training_data_queue.get()

        data = {
            'file': training_data,
            'data_type': 'tcx'
        }

        for i in range(3):
            response = await post_training(session, data, strava_access_token)
            print('upload status:', response.status)
            print('upload resp:', await response.read())
            if response.status != 429:
                print("uploaded training")
                training_data_queue.task_done()
                break
            print(f"sleeping for 15 minutes")
            await asyncio.sleep(60 * 15 + 10)
        else:
            print('ERROR: not uploaded due to rate limits')


async def post_training(session: aiohttp.ClientSession, data: dict, strava_access_token: str):
    return await session.post(
        STRAVA_API_BASE_URL + 'uploads', data=data,
        headers={'Authorization': f'Bearer {strava_access_token}'})


async def main(endomondo_email: str, endomondo_password: str, strava_access_token: str):
    training_ids_queue = asyncio.Queue()
    training_data_queue = asyncio.Queue()
    endomondo_session = aiohttp.ClientSession()
    strava_session = aiohttp.ClientSession()
    user_id: str = await endomondo_login(endomondo_session, endomondo_email, endomondo_password)

    tasks_get_ids = [asyncio.create_task(get_trainings_ids(endomondo_session, user_id, training_ids_queue))]

    tasks_download_data = []
    for _ in range(DOWNLOAD_TRAININGS_TASKS):
        tasks_download_data.append(
            asyncio.create_task(download_training(endomondo_session, user_id, training_ids_queue, training_data_queue)))

    upload_tasks = []
    for _ in range(UPLOAD_TRAININGS_TASKS):
        upload_tasks.append(
            asyncio.create_task(upload_training(strava_session, training_data_queue, strava_access_token)))

    await asyncio.gather(*tasks_get_ids)
    await training_ids_queue.join()
    for task in tasks_download_data:
        task.cancel()
    await training_data_queue.join()
    for task in upload_tasks:
        task.cancel()

    await endomondo_session.close()
    await strava_session.close()


if __name__ == '__main__':
    login_end = sys.argv[1]
    password_end = sys.argv[2]
    strava_access_token = sys.argv[3]
    asyncio.run(main(login_end, password_end, strava_access_token))
