#This is a simple script to export trainings from Endomondo to Strava

## Requirements
1. Python 3.7+
2. aiohttp 
    ```
    pip install -r requirements.txt
    ```
3. Strava api token with activity:write scope
    1. create application: https://developers.strava.com/docs/getting-started/
    2. create token with activity:write scope. Run in your browser with open network console
    ```
   https://www.strava.com/oauth/authorize?
    client_id=<client_id>&
    redirect_uri=http://localhost&
    response_type=code&
    scope=activity:write
   ```
   Click authorize. Browser will do some requests. Find one that look like this
   ```
   http://localhost/?state=&code=<code>&scope=read,activity:write
   ```
   and get the code. Then run
   ```
        curl -X POST https://www.strava.com/api/v3/oauth/token \
          -d client_id=<client_id> \
          -d client_secret=<client_secret> \
          -d code=<code you got> \
          -d grant_type=authorization_code
    ```
   in response you should get access token you can use in this script
   
## Usage
```
python main.py <endomondo email> <endomondo password> <strava access token>
```

## Limitations
By default Strava API allows for 100 requests per 15 minutes. 
When the script reaches the limit it waits 15 min to be able to perform more requests. Due to that execution can be long. There is also a daily limit 1000 requests that resets at midnight UTC.  
If you have more than 1000 workouts you can run the script over midnight or customize this script.
Read more https://developers.strava.com/docs/rate-limits/

You don't have to be worried about workout duplications caused by running this script many times because Strava refuses to add the same workout many times.