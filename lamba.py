import requests
from datetime import date, datetime, timedelta
import time

id = "ed9995430133c14a4c1af8051e75a8be8491f9f7db6f285bffd3f8210176a1da"
secret = "7845086c94f3fab5cce81df66f458ba44f2d29481274111cce2654507ca6141a"
genuis_token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCIsInZlciI6IjEuMC4wIn0.eyJleHAiOjE2ODc4NzU3MjAsImlhdCI6MTY1NjMzOTc5NywianRpIjoiZHlmYV9hYTFPWmJnbGpEc1ZkQ0dSZ0EiLCJzdWIiOiIxODpDQzoyMzowMDo0OTozMiIsInVzZXJuYW1lIjoiYXBhcnRyb29tcyJ9.hePbsxgXB1H74mEdCiL6ZVUrb2mQR1zz3qunvcQtYwQ"

location_mapping = [
    {
        "remote_lock_location_id": "2f48b646-2b96-408b-b279-b03f7ff6fd29",
        "genius_hub_zone_id": 1 
    }
]

client = requests.post('https://connect.remotelock.com/oauth/token', data={'client_id': id, 'client_secret': secret, 'grant_type': 'client_credentials'})

token = client.json()['access_token']

def getGeniusHubZoneId(remote_lock_location_id):
    return [location for location in location_mapping if location['remote_lock_location_id'] == remote_lock_location_id][0]["genius_hub_zone_id"]


def prepareTodaysBookings():
    print('Preparing weeks bookings')
    bookings = []
    access_guests = requests.get('https://api.remotelock.com/access_persons?type=access_guest&attributes[status][]=current&amp;attributes[status][]=upcoming&sort=starts_at&per_page=50', headers = {'Authorization': 'Bearer ' + token}).json()
    for guest in access_guests['data']:
        accesses = requests.get('https://api.remotelock.com/access_persons/' + guest['id'] + '/accesses', headers = {'Authorization': 'Bearer ' + token}).json()   

        for access in accesses['data']:
            lock = requests.get(access['links']['accessible'], headers = {'Authorization': 'Bearer ' + token}).json()
            lock_name = lock['data']['attributes']['name']
            if 'Apartrooms ' in lock_name:
                room_identifier = lock_name.split(" ", 1)[1]

                next_week = date.today() + timedelta(weeks=1)
                if datetime.fromisoformat(guest['attributes']['starts_at']).date() < next_week: 
                    current =  True if guest['attributes']['status'] == 'current' else False
                    past_end_of_week = True if datetime.fromisoformat(guest['attributes']['ends_at']).date() >= next_week else False
                    bookings.append({"apartment": room_identifier, "start": guest['attributes']['starts_at'], "end": guest['attributes']['ends_at'], "current":current, "past_end_of_week": past_end_of_week })

    print(bookings)

    working_apartment = 1
    while working_apartment <= 10:
        week_day = 0
        request_body = {"objTimer": []}
        print("Apartment: " + str(working_apartment))
        while week_day < 7:
            working_date = date.today() + timedelta(days=week_day)
            status_for_day = {"move_in": False, "move_out": False, "occupied": False}
            for booking in bookings:
                if booking['apartment'] == str(working_apartment):
                    if datetime.fromisoformat(booking['start']).date() == working_date:
                        status_for_day['move_in'] = True
                    elif datetime.fromisoformat(booking['end']).date() == working_date:
                        status_for_day['move_out'] = True
                    elif datetime.fromisoformat(booking['start']).date() < working_date and datetime.fromisoformat(booking['end']).date() > working_date:
                        status_for_day['occupied'] = True

            print(str(week_day))
            print(status_for_day)
            number_of_days_past_sunday = datetime.today().weekday() + 1
            request_body['objTimer'].extend(getScheduleForDay(week_day + number_of_days_past_sunday, status_for_day))
            week_day = week_day + 1

        print(request_body)
        req = requests.patch('https://hub-server-1.heatgenius.co.uk/v3/zone/' + str(working_apartment), json = request_body, headers = {'Authorization': 'Bearer ' + genuis_token})
        time.sleep(1)
        print(req.status_code)
        if(req.status_code == 308):
            req = requests.patch('https://hub-server-2.heatgenius.co.uk/v3/zone/' + str(working_apartment), json = request_body, headers = {'Authorization': 'Bearer ' + genuis_token})
            print(req.status_code)
            time.sleep(1)

        working_apartment = working_apartment + 1

def getScheduleForDay(week_day, status_for_day):

    if(week_day > 6):
        week_day = week_day - 7

    if(status_for_day['move_in'] and status_for_day['move_out']):
        return [{"iDay": week_day, "iTm": 0, "fSP": 19},{"iDay": week_day, "iTm": 21600, "fSP": 21},{"iDay": week_day, "iTm": 34200, "fSP": 19}, {"iDay": week_day, "iTm": 39600, "fSP": 15},{"iDay": week_day, "iTm": 43200, "fSP": 21},{"iDay": week_day, "iTm": 79200, "fSP": 19}]
    elif(status_for_day['move_in']):
        return [{"iDay": week_day, "iTm": 0, "fSP": 15},{"iDay": week_day, "iTm": 43200, "fSP": 21},{"iDay": week_day, "iTm": 79200, "fSP": 19}]
    elif(status_for_day['move_out']):
        return [{"iDay": week_day, "iTm": 0, "fSP": 19},{"iDay": week_day, "iTm": 21600, "fSP": 21},{"iDay": week_day, "iTm": 34200, "fSP": 19}, {"iDay": week_day, "iTm": 39600, "fSP": 15}]
    elif(status_for_day['occupied']):
        return [{"iDay": week_day, "iTm": 0, "fSP": 19},{"iDay": week_day, "iTm": 21600, "fSP": 21},{"iDay": week_day, "iTm": 32400, "fSP": 19}, {"iDay": week_day, "iTm": 59400, "fSP": 21},{"iDay": week_day, "iTm": 79200, "fSP": 19}]
    else:
        return [{"iDay": week_day, "iTm": 0, "fSP": 15}]

prepareTodaysBookings()

# def appartmentList():
#     return [{"appartment": 1, "bookings": []},{"appartment": 2, "bookings": []},{"appartment": 1, "bookings": []},{"appartment": 1, "bookings": []},{"appartment": 1, "bookings": []},{"appartment": 1, "bookings": []},{"appartment": 1, "bookings": []},{"appartment": 1, "bookings": []},{"appartment": 1, "bookings": []},{"appartment": 1, "bookings": []},{"appartment": 1, "bookings": []},{"appartment": 1, "bookings": []}]

# def nightTimeCheckForCurrentBooking():

#     # Get upcoming access guests for today
#     access_guests = requests.get('https://api.remotelock.com/access_persons?type=access_guest&attributes[status]=current&sort=starts_at&per_page=50', headers = {'Authorization': 'Bearer ' + token}).json()

#     for guest in access_guests['data']:
#         if datetime.fromisoformat(guest['attributes']['starts_at']).date() <= date.today():
            
#             accesses = requests.get('https://api.remotelock.com/access_persons/' + guest['id'] + '/accesses', headers = {'Authorization': 'Bearer ' + token}).json()

#             for access in accesses['data']:
#                 lock = requests.get(access['links']['accessible'], headers = {'Authorization': 'Bearer ' + token}).json()
#                 lock_name = lock['data']['attributes']['name']
#                 if 'Apartrooms ' in lock_name:
#                     room_identifier = lock_name.split(" ", 1)[1]
#                     temp_data = {
#                         "duration": 36000,
#                         "setpoint": 19
#                     }
#                     print('Night time temp for apt' + room_identifier)
#                     requests.post('https://my.geniushub.co.uk/v1/zones/' + room_identifier + '/override', json = temp_data, headers = {'Authorization': 'Bearer ' + genuis_token})
#                     time.sleep(2)

# def occupiedWakeUpChecks():

#     print("Processing wake up checks")

#     # Get upcoming access guests for today
#     access_guests = requests.get('https://api.remotelock.com/access_persons?type=access_guest&attributes[status]=current&sort=starts_at&per_page=50', headers = {'Authorization': 'Bearer ' + token}).json()

#     for guest in access_guests['data']:
#         if datetime.fromisoformat(guest['attributes']['starts_at']).date() < date.today():
            
#             accesses = requests.get('https://api.remotelock.com/access_persons/' + guest['id'] + '/accesses', headers = {'Authorization': 'Bearer ' + token}).json()

#             for access in accesses['data']:
#                 lock = requests.get(access['links']['accessible'], headers = {'Authorization': 'Bearer ' + token}).json()
#                 lock_name = lock['data']['attributes']['name']
#                 if 'Apartrooms ' in lock_name:
#                     room_identifier = lock_name.split(" ", 1)[1]

#                     if datetime.fromisoformat(guest['attributes']['ends_at']).date() == date.today():
#                         temp_data = {
#                             "duration": 12600,
#                             "setpoint": 21
#                         }
#                         print('Checkout day, wake up apt' + room_identifier)
#                     else:
#                         temp_data = {
#                             "duration": 10800,
#                             "setpoint": 21
#                         }
#                         print('Normal today, wake up apt' + room_identifier)
                    
#                     requests.post('https://my.geniushub.co.uk/v1/zones/' + room_identifier + '/override', json = temp_data, headers = {'Authorization': 'Bearer ' + genuis_token})
#                     time.sleep(2)

# def occupiedMorningChecks():

#     # Get upcoming access guests for today
#     access_guests = requests.get('https://api.remotelock.com/access_persons?type=access_guest&attributes[status]=upcoming&sort=starts_at&per_page=50', headers = {'Authorization': 'Bearer ' + token}).json()
#     print(access_guests)
#     for guest in access_guests['data']:
#         if datetime.fromisoformat(guest['attributes']['starts_at']).date() < date.today() and datetime.fromisoformat(guest['attributes']['ends_at']).date() != date.today():
#             print(guest)
#             accesses = requests.get('https://api.remotelock.com/access_persons/' + guest['id'] + '/accesses', headers = {'Authorization': 'Bearer ' + token}).json()

#             for access in accesses['data']:
#                 lock = requests.get(access['links']['accessible'], headers = {'Authorization': 'Bearer ' + token}).json()
#                 lock_name = lock['data']['attributes']['name']
#                 if 'Apartrooms ' in lock_name:
#                     room_identifier = lock_name.split(" ", 1)[1]

#                     temp_data = {
#                         "duration": 19800,
#                         "setpoint": 19
#                     }

#                     print('Occupied morning apt' + room_identifier)
#                     # response = requests.post('https://my.geniushub.co.uk/v1/zones/' + room_identifier + '/override', json = temp_data, headers = {'Authorization': 'Bearer ' + genuis_token})

#                     # print(response)
#                     time.sleep(2)

# def occupiedAfternoonChecks():

#     # Get upcoming access guests for today
#     access_guests = requests.get('https://api.remotelock.com/access_persons?type=access_guest&attributes[status]=current&sort=starts_at&per_page=50', headers = {'Authorization': 'Bearer ' + token}).json()
#     print(access_guests)
#     for guest in access_guests['data']:
#         if datetime.fromisoformat(guest['attributes']['starts_at']).date() < date.today() and datetime.fromisoformat(guest['attributes']['ends_at']).date() != date.today():
            
#             accesses = requests.get('https://api.remotelock.com/access_persons/' + guest['id'] + '/accesses', headers = {'Authorization': 'Bearer ' + token}).json()

#             for access in accesses['data']:
#                 lock = requests.get(access['links']['accessible'], headers = {'Authorization': 'Bearer ' + token}).json()
#                 lock_name = lock['data']['attributes']['name']
#                 if 'Apartrooms ' in lock_name:
#                     room_identifier = lock_name.split(" ", 1)[1]

#                     temp_data = {
#                         "duration": 19800,
#                         "setpoint": 21
#                     }

#                     print('Occupied Afternoon apt' + room_identifier)
#                     requests.post('https://my.geniushub.co.uk/v1/zones/' + room_identifier + '/override', json = temp_data, headers = {'Authorization': 'Bearer ' + genuis_token})
#                     time.sleep(2)

# def getCheckOuts():
#         # Get upcoming access guests for today
#     access_guests = requests.get('https://api.remotelock.com/access_persons?type=access_guest&attributes[attributes[status]=current&sort=starts_at&per_page=50', headers = {'Authorization': 'Bearer ' + token}).json()

#     for guest in access_guests['data']:
#         if datetime.fromisoformat(guest['attributes']['ends_at']).date() == date.today():
            
#             accesses = requests.get('https://api.remotelock.com/access_persons/' + guest['id'] + '/accesses', headers = {'Authorization': 'Bearer ' + token}).json()

#             for access in accesses['data']:
#                 lock = requests.get(access['links']['accessible'], headers = {'Authorization': 'Bearer ' + token}).json()
#                 lock_name = lock['data']['attributes']['name']
#                 if 'Apartrooms ' in lock_name:
#                     room_identifier = lock_name.split(" ", 1)[1]
#                     temp_data = {
#                         "duration": 5400,
#                         "setpoint": 19
#                     }
#                     print('Checkouts for apt' + room_identifier)
#                     requests.post('https://my.geniushub.co.uk/v1/zones/' + room_identifier + '/override', json = temp_data, headers = {'Authorization': 'Bearer ' + genuis_token})
#                     time.sleep(2)

# # def processTime():
# #     match datetime.now().strftime("%H:%M"):
# #         case "06:00":
# #             return occupiedWakeUpChecks()
# #         case "18:44":
# #             return nightTimeCheckForCurrentBooking()
# #         case "09:00":
# #             return occupiedMorningChecks()
# #         case "09:30":
# #             return getCheckOuts()
# #         case "10:00":
# #             return nightTimeCheckForCurrentBooking()
# #         case "12:00":
# #             return prepareTodaysBookings()
# #         case "16:30":
# #             return occupiedAfternoonChecks()
# #         case "22:00":
# #             return nightTimeCheckForCurrentBooking()
# #         case _:
# #             return

# # def processTime():
# #     time = datetime.now().strftime("%H:%M")

# #     if time == "06:00":
# #         return occupiedWakeUpChecks()
# #     elif time == "09:00":
# #         return occupiedMorningChecks()
# #     elif time == "09:30":
# #         return getCheckOuts()
# #     elif time == "12:00":
# #         return prepareTodaysBookings()
# #     elif time == "16:30":
# #         return occupiedAfternoonChecks()
# #     elif time == "22:00":
# #         return nightTimeCheckForCurrentBooking()

# # processTime()




